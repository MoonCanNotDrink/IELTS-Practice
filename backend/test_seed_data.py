import ast
import unittest
from pathlib import Path


def _load_seed_topic_calls():
    seed_data_path = Path(__file__).resolve().parent / "app" / "seed_data.py"
    tree = ast.parse(seed_data_path.read_text(encoding="utf-8"))

    season = None
    topic_calls = None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CURRENT_PART2_SEASON":
                    season = ast.literal_eval(node.value)
                if isinstance(target, ast.Name) and target.id == "SEED_TOPICS":
                    topic_calls = node.value.elts

    if season is None or topic_calls is None:
        raise AssertionError("Could not locate CURRENT_PART2_SEASON or SEED_TOPICS")

    return season, topic_calls


class SeedTopicBankTests(unittest.TestCase):
    def test_part2_seed_topics_match_2026_q1_bank(self):
        season, topic_calls = _load_seed_topic_calls()
        titles = {
            ast.literal_eval(call.args[0])
            for call in topic_calls
            if isinstance(call, ast.Call)
        }
        point_counts = [
            len(call.args[1].elts)
            for call in topic_calls
            if isinstance(call, ast.Call) and isinstance(call.args[1], ast.List)
        ]

        self.assertEqual(season, "2026-Q1")
        self.assertEqual(len(topic_calls), 58)
        self.assertEqual(len(titles), 58)
        self.assertTrue(all(count >= 3 for count in point_counts))

        self.assertIn("Describe a famous person you would like to meet.", titles)
        self.assertIn("Describe a time when you had an unusual meal.", titles)
        self.assertNotIn("Describe a place you visited that was very crowded", titles)
