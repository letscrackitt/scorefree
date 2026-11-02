#!/usr/bin/env python3
"""Regression tests for the original Mains-level Reasoning (+ Computer Aptitude) bank.

Structure checks run on all 20 generated tests. Logic checks re-solve the PRINTED text with separate
code (inequality closure, puzzle clue re-parsing happens inside the builder) and test known classical
syllogism / blood-relation facts against the solver."""
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import random  # noqa: E402
import build_mains_reasoning as mr  # noqa: E402


class StructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tests = {(e, t): mr.build_test_safe(e, t) for e in ("ibps", "sbi") for t in range(1, 11)}

    def test_official_counts(self):
        for (exam, t), qs in self.tests.items():
            self.assertEqual(len(qs), 40 if exam == "ibps" else 50, (exam, t))

    def test_every_question_valid(self):
        for (exam, t), qs in self.tests.items():
            for q in qs:
                with self.subTest(exam=exam, test=t, q=q["q"][:50]):
                    self.assertEqual(len(q["opts"]), 5)
                    self.assertEqual(len(set(q["opts"])), 5)
                    self.assertTrue(0 <= q["ans"] < 5)
                    self.assertTrue(q["exp"].strip())

    def test_puzzle_sets_have_four_or_five_questions_with_clues(self):
        for (exam, t), qs in self.tests.items():
            sets = {}
            for q in qs:
                if q.get("setTitle"):
                    sets.setdefault(q["setTitle"], []).append(q)
                    self.assertIn("<li>", q["setIntro"])
            self.assertIn(len(sets), (2, 3), (exam, t))
            for title, items in sets.items():
                self.assertIn(len(items), (4, 5), title)
                idx = [i for i, q in enumerate(qs) if q.get("setTitle") == title]
                self.assertEqual(idx, list(range(idx[0], idx[0] + len(idx))), "a puzzle set must stay contiguous")

    def test_tests_do_not_share_the_same_pattern(self):
        """Reviewer feedback: every test used the same layout. Each test must now differ in mix, counts and order."""
        for exam in ("ibps", "sbi"):
            seqs, firsts, mixes = set(), set(), set()
            for t in range(1, 11):
                topics = [q["topic"] for q in self.tests[(exam, t)] if q["topic"] != "Computer Aptitude"]
                seqs.add(tuple(topics[:8]))
                firsts.add(topics[0])
                mixes.add(tuple(sorted(Counter(topics).items())))
                self.assertGreaterEqual(len(set(topics)), 9, (exam, t))
            self.assertEqual(len(seqs), 10, exam)
            self.assertEqual(len(mixes), 10, exam)
            self.assertGreaterEqual(len(firsts), 6, exam)
            for topic in ("Syllogism", "Inequality", "Blood Relations", "Coding-Decoding", "Input-Output"):
                counts = {sum(q["topic"] == topic for q in self.tests[(exam, t)]) for t in range(1, 11)}
                self.assertGreaterEqual(len(counts), 3, (exam, topic, counts))

    def test_puzzle_kinds_and_sizes_vary(self):
        for exam in ("ibps", "sbi"):
            titles = {q["setTitle"] for t in range(1, 11) for q in self.tests[(exam, t)] if q.get("setTitle")}
            self.assertGreaterEqual(len(titles), 6, titles)

    def test_sbi_has_fifteen_computer_questions(self):
        for t in range(1, 11):
            qs = self.tests[("sbi", t)]
            self.assertEqual(sum(q["topic"] == "Computer Aptitude" for q in qs), 15, t)
        for t in range(1, 11):
            self.assertFalse(any(q["topic"] == "Computer Aptitude" for q in self.tests[("ibps", t)]))

    def test_no_duplicate_questions_within_a_test(self):
        for key, qs in self.tests.items():
            texts = [(q["q"], q.get("setTitle", "")) for q in qs]
            self.assertEqual(len(texts), len(set(texts)), key)

    def test_answer_positions_not_lopsided(self):
        c = Counter(q["ans"] for qs in self.tests.values() for q in qs)
        total = sum(c.values())
        for pos in range(5):
            self.assertGreater(c[pos] / total, 0.08, c)

    def test_concept_questions_never_repeat_across_sbi_tests(self):
        seen = Counter(q["q"] for t in range(1, 11) for q in self.tests[("sbi", t)] if q["topic"] == "Computer Aptitude"
                       and q["q"] in {c[0] for c in mr.CONCEPTS})
        self.assertTrue(all(v == 1 for v in seen.values()))


def closure_relation(edges, n):
    """Independent transitive-closure solver for statements built from >, <, >=, <=, = between named letters."""
    R = [[None] * n for _ in range(n)]                  # R[i][j]: i >= j ('ge') or i > j ('gt')
    def put(i, j, v):
        if R[i][j] != "gt":
            R[i][j] = v if R[i][j] is None or v == "gt" else R[i][j]
    for a, r, b in edges:
        if r == ">":
            put(a, b, "gt")
        elif r == "<":
            put(b, a, "gt")
        elif r == "≥":
            put(a, b, "ge")
        elif r == "≤":
            put(b, a, "ge")
        else:
            put(a, b, "ge"); put(b, a, "ge")
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if R[i][k] and R[k][j]:
                    put(i, j, "gt" if "gt" in (R[i][k], R[k][j]) else "ge")
    return R


def holds_by_closure(R, i, rel, j):
    ge = lambda a, b: R[a][b] in ("ge", "gt")
    gt = lambda a, b: R[a][b] == "gt"
    return {">": gt(i, j), "<": gt(j, i), "≥": ge(i, j), "≤": ge(j, i), "=": ge(i, j) and ge(j, i)}[rel]


class LogicTests(unittest.TestCase):
    def test_inequality_text_resolves_to_the_same_answer(self):
        phrase = {"is greater than": ">", "is less than": "<", "is greater than or equal to": "≥", "is less than or equal to": "≤", "is equal to": "="}
        for seed in range(200):
            q = mr.inequality(random.Random(seed), seed % 5)
            legend = {m[1]: phrase[m[2]] for m in re.finditer(r"'P (\S) Q' means 'P (.*?) Q'", q["q"])}
            body = re.search(r"Statements?:\n(.*?)\nConclusions:", q["q"], re.S)[1].split("\n")
            names, edges = {}, []
            for line in body:
                tok = line.split()
                for k in range(0, len(tok) - 2, 2):
                    a, sym, b = tok[k], tok[k + 1], tok[k + 2]
                    for L in (a, b):
                        names.setdefault(L, len(names))
                    edges.append((names[a], legend[sym], names[b]))
            con = re.findall(r"^(?:I|II)\. (\S) (\S) (\S)$", q["q"], re.M)
            R = closure_relation(edges, len(names))
            t = [holds_by_closure(R, names[a], legend[s_], names[b]) for a, s_, b in con]
            comp = {">": "≤", "<": "≥", "≥": "<", "≤": ">"}
            rel1, rel2 = legend[con[0][1]], legend[con[1][1]]
            either = (con[0][0], con[0][2]) == (con[1][0], con[1][2]) and comp.get(rel1) == rel2
            want = 4 if all(t) else 0 if t[0] else 1 if t[1] else 2 if either else 3
            self.assertEqual(q["ans"], want, (seed, q["q"]))

    def test_classical_syllogism_results(self):
        # sets: 0=A, 1=B, 2=C, 3=D ; a conclusion follows when it holds in every model of the statements
        def follows(stmts, concl):
            ms = [m for m in mr.ALL_MODELS if all(mr.holds(f, a, b, m) for f, a, b in stmts)]
            return bool(ms) and all(mr.holds(f, a, b, m) for m in ms for f, a, b in [concl])
        self.assertTrue(follows([("all", 0, 1), ("all", 1, 2)], ("all", 0, 2)))
        self.assertTrue(follows([("some", 0, 1), ("all", 1, 2)], ("some", 0, 2)))
        self.assertTrue(follows([("no", 0, 1), ("all", 2, 1)], ("no", 0, 2)))
        self.assertTrue(follows([("all", 0, 1)], ("some", 1, 0)))               # conversion (sets non-empty)
        self.assertFalse(follows([("some", 0, 1), ("some", 1, 2)], ("some", 0, 2)))
        self.assertFalse(follows([("all", 0, 1), ("some", 1, 2)], ("some", 0, 2)))
        self.assertTrue(follows([("few", 0, 1)], ("somenot", 0, 1)))

    def test_known_blood_relations(self):
        def rel(apply, a, b):
            F = mr.Fam()
            for r, x, y in apply:
                F.apply(r, x, y)
            return mr.relation_label(F, a, b)
        self.assertEqual(rel([("father", "F", "X"), ("sister", "S", "F")], "S", "X"), "paternal aunt")
        self.assertEqual(rel([("mother", "M", "X"), ("brother", "B", "M")], "B", "X"), "maternal uncle")
        self.assertEqual(rel([("father", "G", "F"), ("father", "F", "X")], "G", "X"), "paternal grandfather")
        self.assertEqual(rel([("mother", "M", "X"), ("mother", "G", "M")], "G", "X"), "maternal grandmother")
        self.assertIsNone(rel([("father", "F", "X"), ("wife", "W", "F")], "W", "X"))   # could be a step-mother: never labelled
        self.assertEqual(rel([("husband", "H", "W"), ("sister", "W", "S")], "H", "S"), "brother-in-law")

    def test_direction_geometry(self):
        self.assertEqual(mr.compass(3, 4), "North-East")
        self.assertEqual(mr.compass(0, -5), "South")
        self.assertEqual(mr.compass(-2, 2), "North-West")

    def test_generated_file_exists(self):
        out = ROOT / "question-bank.mains-reasoning.js"
        self.assertTrue(out.exists(), "run python tools/build_mains_reasoning.py")
        self.assertIn("SF_BANK[e].reasoning[t]=B[e][t]", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
