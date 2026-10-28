#!/usr/bin/env python3
"""Regression tests for ScoreFree's deterministic quantitative question generator."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_question_bank as bank  # noqa: E402


class QuantitativeGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = bank.generate_quant(400)

    def test_generator_produces_full_batch(self):
        self.assertEqual(len(self.questions), 400)

    def test_every_question_has_five_distinct_options_and_valid_key(self):
        for item in self.questions:
            with self.subTest(question=item["q"]):
                self.assertEqual(len(item["opts"]), 5)
                self.assertEqual(len(set(item["opts"])), 5)
                self.assertGreaterEqual(item["ans"], 0)
                self.assertLess(item["ans"], len(item["opts"]))
                self.assertNotEqual(item["exp"], "")

    def test_calculation_matches_the_marked_answer(self):
        patterns = [
            (r"What is (\d+)% of (\d+)\?", lambda m: int(m[1]) * int(m[2]) / 100),
            (r"A value of (\d+) is increased by (\d+)%", lambda m: int(m[1]) * (100 + int(m[2])) / 100),
            (r"Find the simple interest on ₹(\d+) at (\d+)% per annum for (\d+) years", lambda m: int(m[1]) * int(m[2]) * int(m[3]) / 100),
            (r"The average of (\d+) and (\d+) is what\?", lambda m: (int(m[1]) + int(m[2])) / 2),
            (r"An item costs ₹(\d+)\. At a profit of (\d+)%", lambda m: int(m[1]) * (100 + int(m[2])) / 100),
            (r"A vehicle travels at (\d+) km/h for (\d+) hours", lambda m: int(m[1]) * int(m[2])),
            (r"₹(\d+) is divided in the ratio (\d+):(\d+)", lambda m: int(m[1]) * int(m[2]) / (int(m[2]) + int(m[3]))),
            (r"(\d+) workers finish a job in (\d+) days.*how many days will (\d+) workers take", lambda m: int(m[1]) * int(m[2]) / int(m[3])),
        ]
        for item in self.questions:
            with self.subTest(question=item["q"]):
                expected = None
                for pattern, calculate in patterns:
                    match = re.search(pattern, item["q"], flags=re.IGNORECASE)
                    if match:
                        expected = calculate(match)
                        break
                self.assertIsNotNone(expected, "Question does not match a tested calculation template")
                marked = item["opts"][item["ans"]]
                self.assertTrue(float(marked).is_integer(), f"Answer is not an integer: {marked}")
                self.assertEqual(int(marked), int(expected))
                self.assertEqual(expected, int(expected), "Generated answer should be exact, not rounded")


if __name__ == "__main__":
    unittest.main()
