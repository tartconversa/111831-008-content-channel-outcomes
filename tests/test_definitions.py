import unittest
from datetime import date

from signal_lab.definitions import DefinitionRegistry
from signal_lab.records import MetricDefinition

READS_V1 = MetricDefinition(
    metric_id="reads",
    version="v1",
    behavior="read",
    window_days=7,
    audience_scope="all-users",
    valid_to=date(2026, 10, 31),
)
READS_V2 = MetricDefinition(
    metric_id="reads",
    version="v2",
    behavior="read",
    window_days=28,
    audience_scope="all-users",
    valid_from=date(2026, 11, 1),
)


class DefinitionRegistryTests(unittest.TestCase):
    def test_register_and_get(self):
        registry = DefinitionRegistry([READS_V1])
        self.assertIs(registry.get("reads", "v1"), READS_V1)
        self.assertIsNone(registry.get("reads", "v9"))

    def test_identical_re_registration_is_accepted(self):
        registry = DefinitionRegistry([READS_V1])
        registry.register(READS_V1)
        self.assertEqual(registry.versions("reads"), ("v1",))

    def test_conflicting_re_registration_is_rejected(self):
        registry = DefinitionRegistry([READS_V1])
        changed = MetricDefinition(
            metric_id="reads",
            version="v1",
            behavior="read",
            window_days=14,
            audience_scope="all-users",
        )
        with self.assertRaises(ValueError):
            registry.register(changed)
        self.assertEqual(registry.get("reads", "v1").window_days, 7)

    def test_snapshot_is_decoupled_from_later_registrations(self):
        registry = DefinitionRegistry([READS_V1])
        snapshot = registry.snapshot()
        registry.register(READS_V2)
        self.assertEqual(set(snapshot), {("reads", "v1")})
        self.assertEqual(registry.versions("reads"), ("v1", "v2"))

    def test_snapshot_selected_refs(self):
        registry = DefinitionRegistry([READS_V1, READS_V2])
        snapshot = registry.snapshot([("reads", "v1"), ("reads", "missing")])
        self.assertEqual(set(snapshot), {("reads", "v1")})

    def test_current_picks_the_version_valid_on_that_date(self):
        registry = DefinitionRegistry([READS_V1, READS_V2])
        self.assertEqual(
            registry.current("reads", on=date(2026, 10, 15)).version, "v1"
        )
        self.assertEqual(
            registry.current("reads", on=date(2026, 11, 15)).version, "v2"
        )


if __name__ == "__main__":
    unittest.main()
