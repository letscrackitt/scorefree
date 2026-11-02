#!/usr/bin/env python3
"""Regression tests for the original Mains-level Quants bank (question-bank.mains-quant.js).

Rebuilds all 20 tests in memory (the builder re-solves every question from its printed data and
asserts equality) and checks structure, key validity, sets and absence of duplicates."""
import sys
import unittest
from collections import Counter
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

    def test_di_sets_have_four_or_five_questions_and_a_diagram_or_table(self):
        for (exam, t), qs in self.tests.items():
            sets = {}
            for q in qs:
                if q.get("setTitle"):
                    sets.setdefault(q["setTitle"], []).append(q)
                    self.assertTrue("<table" in q["setIntro"] or "<svg" in q["setIntro"] or "<ul" in q["setIntro"])
            self.assertIn(len(sets), (2, 3) if exam == "ibps" else (3, 4), (exam, t))
            for title, items in sets.items():
                self.assertIn(len(items), (4, 5), title)
                idx = [i for i, q in enumerate(qs) if q.get("setTitle") == title]
                self.assertEqual(idx, list(range(idx[0], idx[0] + len(idx))), "a DI set must stay contiguous")

    def test_tests_do_not_share_the_same_pattern(self):
        """Reviewer feedback: every test used the same layout. Each test must now differ in mix, counts and order."""
        for exam in ("ibps", "sbi"):
            seqs, firsts, mixes = set(), set(), set()
            for t in range(1, 11):
                topics = [q["topic"] for q in self.tests[(exam, t)]]
                seqs.add(tuple(topics[:8]))
                firsts.add(topics[0])
                mixes.add(tuple(sorted(Counter(topics).items())))
                self.assertGreaterEqual(len(set(topics)), 12, (exam, t))
                self.assertLessEqual(Counter(topics).most_common(1)[0][1], 7, (exam, t))
            self.assertEqual(len(seqs), 10, exam)
            self.assertEqual(len(mixes), 10, exam)
            self.assertGreaterEqual(len(firsts), 6, exam)
            for topic in ("Quadratic Equations", "Number Series", "Simplification", "Approximation"):
                counts = {sum(q["topic"] == topic for q in self.tests[(exam, t)]) for t in range(1, 11)}
                self.assertGreaterEqual(len(counts), 3, (exam, topic, counts))

    def test_question_formats_vary_within_a_topic(self):
        for exam in ("ibps", "sbi"):
            for topic, minimum in (("Number Series", 3), ("Quadratic Equations", 2)):
                stems = {q["q"].split("\n")[0][:40] for t in range(1, 11) for q in self.tests[(exam, t)] if q["topic"] == topic}
                self.assertGreaterEqual(len(stems), minimum, (exam, topic, stems))

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
