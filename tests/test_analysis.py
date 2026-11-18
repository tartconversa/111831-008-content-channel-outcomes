import unittest
from datetime import date

from signal_lab.analysis import (
    COMPARABLE,
    DEFINITION_CHANGED,
    METRIC_UNKNOWN,
    MISSING_IN_END,
    MISSING_IN_START,
    compare_periods,
)
from signal_lab.records import Observation


def obs(oid, source, year, month, topic="t", value=1, metric="reads", version="v1", **kw):
    return Observation(
        oid,
        source,
        date(year, month, 1),
        topic,
        value,
        metric_id=metric,
        metric_version=version,
        **kw,
    )


class ComparePeriodsTests(unittest.TestCase):
    def test_comparable_slice_with_same_definition(self):
        rows = [
            obs("a", "desk-1", 2026, 10, value=2),
            obs("b", "desk-1", 2026, 11, value=3),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        self.assertEqual(result.gaps, ())
        [slice] = result.comparable
        self.assertEqual(slice.status, COMPARABLE)
        self.assertEqual((slice.start_value, slice.end_value), (2, 3))
        self.assertEqual(slice.start_versions, ("v1",))

    def test_definition_change_between_periods_is_a_gap(self):
        rows = [
            obs("a", "desk-1", 2026, 10),
            obs("b", "desk-1", 2026, 11, version="v2"),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        self.assertEqual(result.comparable, ())
        [gap] = result.gaps
        self.assertEqual(gap.status, DEFINITION_CHANGED)
        self.assertEqual(gap.start_versions, ("v1",))
        self.assertEqual(gap.end_versions, ("v2",))

    def test_mixed_versions_within_one_period_is_a_gap(self):
        rows = [
            obs("a", "desk-1", 2026, 10),
            obs("b", "desk-1", 2026, 10, version="v2"),
            obs("c", "desk-1", 2026, 11),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        [gap] = result.gaps
        self.assertEqual(gap.status, DEFINITION_CHANGED)
        self.assertEqual(gap.start_versions, ("v1", "v2"))

    def test_channel_coverage_change_is_a_gap(self):
        rows = [
            obs("a", "desk-1", 2026, 10),
            obs("b", "desk-2", 2026, 11),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        statuses = {gap.source_id: gap.status for gap in result.gaps}
        self.assertEqual(statuses["desk-1"], MISSING_IN_END)
        self.assertEqual(statuses["desk-2"], MISSING_IN_START)
        self.assertEqual(result.comparable, ())

    def test_unscoped_records_are_not_comparable(self):
        rows = [
            Observation("a", "desk-1", date(2026, 10, 1), "t", 2),
            Observation("b", "desk-1", date(2026, 11, 1), "t", 3),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        [gap] = result.gaps
        self.assertEqual(gap.status, METRIC_UNKNOWN)
        self.assertEqual(result.comparable, ())

    def test_ignores_observations_outside_the_selected_periods(self):
        rows = [obs("a", "desk", 2026, 9)]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        self.assertEqual(result.slices, ())

    def test_region_filter(self):
        rows = [
            obs("a", "desk-1", 2026, 10, region="east-asia"),
            obs("b", "desk-2", 2026, 10, region="europe"),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11), region="east-asia")
        self.assertEqual({s.source_id for s in result.slices}, {"desk-1"})

    def test_rollup_sums_only_comparable_slices_per_metric(self):
        rows = [
            obs("a", "desk-1", 2026, 10, value=2),
            obs("b", "desk-1", 2026, 11, value=3),
            obs("c", "desk-2", 2026, 10, value=5),  # desk-2 结束期缺失
            obs("d", "desk-1", 2026, 10, value=7, metric="shares"),
            obs("e", "desk-1", 2026, 11, value=11, metric="shares"),
        ]
        result = compare_periods(rows, (2026, 10), (2026, 11))
        rollup = result.rollup()
        reads = rollup[("t", "reads")]
        self.assertEqual((reads["start_value"], reads["end_value"]), (2, 3))
        self.assertEqual(reads["sources"], ("desk-1",))
        self.assertEqual(reads["excluded"], (("desk-2", MISSING_IN_END),))
        shares = rollup[("t", "shares")]
        self.assertEqual((shares["start_value"], shares["end_value"]), (7, 11))


if __name__ == "__main__":
    unittest.main()
