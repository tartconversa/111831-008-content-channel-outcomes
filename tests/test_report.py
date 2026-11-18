import unittest
from datetime import date

from signal_lab.analysis import compare_periods
from signal_lab.definitions import DefinitionRegistry
from signal_lab.records import MetricDefinition, Observation
from signal_lab.report import SCOPE_CAVEAT, create_report, definition_delta

READS_V1 = MetricDefinition(
    metric_id="reads",
    version="v1",
    behavior="read",
    window_days=7,
    audience_scope="all-users",
)
READS_V2 = MetricDefinition(
    metric_id="reads",
    version="v2",
    behavior="read",
    window_days=28,
    audience_scope="all-users",
)

# 陈述中不允许出现的因果措辞
CAUSAL_WORDS = ("导致", "造成", "带来", "促成", "拉动", "归功于", "证明了", "归因于")


def obs(oid, source, year, month, value, version="v1"):
    return Observation(
        oid,
        source,
        date(year, month, 1),
        "topic",
        value,
        metric_id="reads",
        metric_version=version,
    )


def build_report():
    registry = DefinitionRegistry([READS_V1, READS_V2])
    rows = [
        obs("a", "desk-1", 2026, 10, 100),  # desk-1 口径 v1 → v2
        obs("b", "desk-1", 2026, 11, 150, version="v2"),
        obs("c", "desk-2", 2026, 10, 40),  # desk-2 口径一致，可比
        obs("d", "desk-2", 2026, 11, 55),
    ]
    comparison = compare_periods(rows, (2026, 10), (2026, 11))
    return create_report("r-1", "两期复盘", comparison, registry=registry), registry


class ReportTests(unittest.TestCase):
    def test_statements_are_scoped_observations(self):
        report, _ = build_report()
        self.assertEqual(len(report.statements), 1)
        statement = report.statements[0]
        self.assertIn("desk-2", statement)
        self.assertIn("观察到", statement)
        self.assertIn("受众范围 all-users", statement)
        self.assertIn("观察窗口 7 天", statement)
        self.assertIn("口径 reads v1", statement)
        self.assertIn("阅读", statement)
        self.assertIn("40", statement)
        self.assertIn("55", statement)

    def test_statements_avoid_causal_wording(self):
        report, _ = build_report()
        for statement in report.statements:
            for word in CAUSAL_WORDS:
                self.assertNotIn(word, statement)

    def test_gaps_explain_definition_change_with_field_delta(self):
        report, _ = build_report()
        self.assertEqual(len(report.gaps), 1)
        gap = report.gaps[0]
        self.assertIn("desk-1", gap)
        self.assertIn("v1", gap)
        self.assertIn("v2", gap)
        self.assertIn("观察窗口（天）：7 → 28", gap)
        self.assertIn("不直接可比", gap)

    def test_readings_preserve_raw_values_with_versions(self):
        report, _ = build_report()
        readings = {
            (r.source_id, r.period): (r.value, r.versions) for r in report.readings
        }
        self.assertEqual(readings[("desk-1", (2026, 10))], (100, ("v1",)))
        self.assertEqual(readings[("desk-1", (2026, 11))], (150, ("v2",)))
        self.assertEqual(readings[("desk-2", (2026, 11))], (55, ("v1",)))

    def test_report_snapshots_definitions_at_creation_time(self):
        report, registry = build_report()
        self.assertEqual(
            set(report.definitions), {("reads", "v1"), ("reads", "v2")}
        )
        # 留档后注册表新增版本，不影响已留档报告
        registry.register(
            MetricDefinition(
                metric_id="reads",
                version="v3",
                behavior="read",
                window_days=90,
                audience_scope="all-users",
            )
        )
        self.assertEqual(set(report.definitions), {("reads", "v1"), ("reads", "v2")})
        self.assertEqual(report.definitions[("reads", "v1")].window_days, 7)

    def test_report_carries_scope_caveat(self):
        report, _ = build_report()
        self.assertIn(SCOPE_CAVEAT, report.caveats)
        self.assertIn("不能据此归因于某一内容", SCOPE_CAVEAT)

    def test_definition_delta_lists_changed_fields(self):
        self.assertEqual(
            definition_delta(READS_V1, READS_V2), ("观察窗口（天）：7 → 28",)
        )
        self.assertEqual(definition_delta(READS_V1, READS_V1), ())


if __name__ == "__main__":
    unittest.main()
