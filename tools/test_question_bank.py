#!/usr/bin/env python3
"""Regression tests for ScoreFree's original Mains quantitative generator."""
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
                self.assertEqual(int(item["opts"][item["ans"]]), item["answer_value"])

    def test_linked_di_sets_are_shared_and_complete(self):
        sets = {}
        for item in self.questions:
            if item.get("setTitle"):
                sets.setdefault(item["setTitle"], []).append(item)
                self.assertTrue(item.get("setIntro"))
        self.assertGreaterEqual(len(sets), 5)
        for title, items in sets.items():
            self.assertEqual(len(items), 5, title)

    def test_no_duplicate_question_text(self):
        texts = [item["q"].strip().lower() for item in self.questions]
        self.assertEqual(len(texts), len(set(texts)))


if __name__ == "__main__":
    unittest.main()
