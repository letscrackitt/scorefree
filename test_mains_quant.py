#!/usr/bin/env python3
"""Regression tests for the original Mains-level Quants bank (question-bank.mains-quant.js).

Rebuilds all 20 tests in memory (the builder re-solves every question from its printed data and
asserts equality) and checks structure, key validity, sets and absence of duplicates."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_mains_quant as mq  # noqa: E402


class MainsQuantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tests = {(e, t): mq.build_test(e, t) for e in ("ibps", "sbi") for t in range(1, 11)}

    def test_official_question_counts(self):
        for (exam, t), qs in self.tests.items():
            self.assertEqual(len(qs), 35 if exam == "ibps" else 50, (exam, t))

    def test_every_question_is_valid(self):
        for (exam, t), qs in self.tests.items():
            for q in qs:
                with self.subTest(exam=exam, test=t, q=q["q"][:50]):
                    self.assertEqual(len(q["opts"]), 5)
                    self.assertEqual(len(set(q["opts"])), 5)
                    self.assertTrue(0 <= q["ans"] < 5)
                    self.assertTrue(q["exp"].strip())

    def test_di_sets_have_five_questions_and_a_diagram_or_table(self):
        for (exam, t), qs in self.tests.items():
            sets = {}
            for q in qs:
                if q.get("setTitle"):
                    sets.setdefault(q["setTitle"], []).append(q)
                    self.assertTrue("<table" in q["setIntro"] or "<svg" in q["setIntro"])
            self.assertEqual(len(sets), 3 if exam == "ibps" else 4, (exam, t))
            for title, items in sets.items():
                self.assertEqual(len(items), 5, title)

    def test_no_duplicate_questions_within_a_test(self):
        for key, qs in self.tests.items():
            texts = [(q["q"], q.get("setTitle", "")) for q in qs]
            self.assertEqual(len(texts), len(set(texts)), key)

    def test_answer_positions_are_not_lopsided(self):
        from collections import Counter
        c = Counter(q["ans"] for qs in self.tests.values() for q in qs)
        total = sum(c.values())
        for pos in range(5):
            self.assertGreater(c[pos] / total, 0.08, c)

    def test_generated_file_is_up_to_date(self):
        out = (ROOT / "question-bank.mains-quant.js")
        self.assertTrue(out.exists(), "run python tools/build_mains_quant.py")
        self.assertIn("SF_BANK[e].quant[t]=B[e][t]", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
