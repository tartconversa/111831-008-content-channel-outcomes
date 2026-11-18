import unittest
from pathlib import Path

from signal_lab.definitions import DefinitionRegistry
from signal_lab.loading import load_definitions, load_observations, load_sources
from signal_lab.propagation import build_paths

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources(FIXTURES / "sources.json")
        cls.definitions = load_definitions(FIXTURES / "definitions.json")
        cls.observations = load_observations(FIXTURES / "observations.json")

    def test_fixtures_load(self):
        self.assertEqual(len(self.sources), 3)
        self.assertEqual(len(self.definitions), 5)
        self.assertEqual(len(self.observations), 9)

    def test_every_observation_source_is_known(self):
        known = {source.source_id for source in self.sources}
        for obs in self.observations:
            self.assertIn(obs.source_id, known)

    def test_every_metric_ref_is_registered(self):
        registry = DefinitionRegistry(self.definitions)
        for obs in self.observations:
            ref = obs.metric_ref
            self.assertIsNotNone(ref, f"{obs.observation_id} 未标注口径")
            self.assertIsNotNone(
                registry.get(*ref), f"{obs.observation_id} 引用了未登记口径 {ref}"
            )

    def test_every_reshare_root_resolves(self):
        _, dangling = build_paths(self.observations)
        self.assertEqual(dangling, ())


if __name__ == "__main__":
    unittest.main()
