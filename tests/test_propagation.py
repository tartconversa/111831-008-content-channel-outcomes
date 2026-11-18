import unittest
from datetime import date

from signal_lab.propagation import build_paths, summarize_propagation
from signal_lab.records import Observation


def obs(oid, source, day, relation="origin", path_root=None, content="c-1", value=1):
    return Observation(
        oid,
        source,
        date(2026, 11, day),
        "topic",
        value,
        metric_id="reads",
        metric_version="v1",
        content_id=content,
        relation=relation,
        path_root=path_root,
    )


class BuildPathsTests(unittest.TestCase):
    def test_reshares_group_with_their_origin(self):
        rows = [
            obs("o-1", "desk-a", 1),
            obs("o-2", "desk-b", 2, relation="reshare", path_root="o-1"),
            obs("o-3", "desk-c", 3, relation="reshare", path_root="o-1"),
        ]
        paths, dangling = build_paths(rows)
        self.assertEqual(dangling, ())
        [path] = paths
        self.assertEqual(path.root_id, "o-1")
        self.assertEqual(path.observation_ids, ("o-1", "o-2", "o-3"))
        self.assertEqual(path.source_ids, ("desk-a", "desk-b", "desk-c"))
        self.assertFalse(path.is_response)

    def test_transitive_reshare_resolves_to_the_ultimate_root(self):
        rows = [
            obs("o-1", "desk-a", 1),
            obs("o-2", "desk-b", 2, relation="reshare", path_root="o-1"),
            obs("o-3", "desk-c", 3, relation="reshare", path_root="o-2"),
        ]
        paths, dangling = build_paths(rows)
        self.assertEqual(dangling, ())
        [path] = paths
        self.assertEqual(path.observation_ids, ("o-1", "o-2", "o-3"))

    def test_independent_responses_form_their_own_paths(self):
        rows = [
            obs("o-1", "desk-a", 1),
            obs("o-2", "desk-b", 2, relation="response"),
        ]
        paths, _ = build_paths(rows)
        by_root = {path.root_id: path for path in paths}
        self.assertFalse(by_root["o-1"].is_response)
        self.assertTrue(by_root["o-2"].is_response)
        self.assertEqual(by_root["o-2"].observation_ids, ("o-2",))

    def test_reshare_with_missing_root_is_dangling(self):
        rows = [
            obs("o-1", "desk-a", 1),
            obs("o-9", "desk-b", 2, relation="reshare", path_root="gone"),
        ]
        paths, dangling = build_paths(rows)
        self.assertEqual([obs.observation_id for obs in dangling], ["o-9"])
        self.assertEqual([path.root_id for path in paths], ["o-1"])

    def test_reshare_without_path_root_is_dangling(self):
        rows = [obs("o-1", "desk-a", 1, relation="reshare")]
        paths, dangling = build_paths(rows)
        self.assertEqual(paths, ())
        self.assertEqual(len(dangling), 1)

    def test_unknown_relation_is_rejected(self):
        with self.assertRaises(ValueError):
            Observation(
                "o-x", "desk", date(2026, 11, 1), "topic", 1, relation="viral"
            )


class SummarizePropagationTests(unittest.TestCase):
    def test_summary_separates_paths_and_responses_per_content(self):
        rows = [
            obs("o-1", "desk-a", 1, content="c-1"),
            obs("o-2", "desk-b", 2, relation="reshare", path_root="o-1", content="c-1"),
            obs("o-3", "desk-c", 3, relation="response", content="c-1"),
            obs("o-4", "desk-a", 4, content="c-2"),
        ]
        summaries = {s.content_id: s for s in summarize_propagation(rows)}
        c1 = summaries["c-1"]
        self.assertEqual(c1.path_count, 1)
        self.assertEqual(c1.response_count, 1)
        self.assertEqual(c1.involved_sources, ("desk-a", "desk-b", "desk-c"))
        c2 = summaries["c-2"]
        self.assertEqual(c2.path_count, 1)
        self.assertEqual(c2.response_count, 0)


if __name__ == "__main__":
    unittest.main()
