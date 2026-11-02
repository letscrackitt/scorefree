#!/usr/bin/env python3
"""ScoreFree original Mains-level Reasoning Ability (+ Computer Aptitude) generator.

Writes ``question-bank.mains-reasoning.js`` filling
  IBPS Clerk Mains Reasoning Ability      40 Q (60 marks, 35 min)  tests 1-10
  SBI  Clerk Mains Reasoning + Computer   50 Q (60 marks, 45 min)  tests 1-10  (35 reasoning + 15 computer)

Every puzzle is solved by exhaustive search and only kept when it has exactly ONE solution;
syllogisms and inequalities are decided by enumerating every possible model; the rest
(directions, coding, input-output, alphanumeric, data sufficiency, computer aptitude) are
computed by code. Run:  python tools/build_mains_reasoning.py
"""
import itertools
import json
import math
import random
import string
from fractions import Fraction as Fr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "question-bank.mains-reasoning.js"
IBPS_Q, SBI_Q, SBI_COMPUTER = 40, 50, 15
TOPIC_PUZ = "Puzzles and Seating Arrangement"
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"          # no I / O to avoid confusion with 1 / 0
ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]


def Q(topic, q, opts, ans, exp, **extra):
    d = {"topic": topic, "q": q, "opts": opts, "ans": ans, "exp": exp}
    d.update(extra)
    return d


def pick_opts(rng, correct, pool, k=5, key=None):
    """Correct answer + (k-1) distinct others from pool, ordered by key (or shuffled)."""
    others = [x for x in dict.fromkeys(pool) if x != correct]
    rng.shuffle(others)
    items = [correct] + others[:k - 1]
    assert len(items) == k, (correct, pool)
    if key:
        items.sort(key=key)
    else:
        rng.shuffle(items)
    return items, items.index(correct)


COUNT_OPTS = ["None", "One", "Two", "Three", "More than three"]


def count_answer(n):
    return min(n, 4)


# ============================================================ puzzle engine
class Clue:
    def __init__(self, kind, ents, k, text, fn):
        self.kind, self.ents, self.k, self.text, self.fn = kind, ents, k, text, fn


def is_val(e):
    return e not in LETTERS


def desc(e, story):
    return e if not is_val(e) else f"the {story['role']} who {story['phrase'].format(v=e)}"


NUMW = {5: "Five", 6: "Six", 7: "Seven", 8: "Eight"}
ATTR_THEMES = {
    "colour": dict(values=["Red", "Blue", "Green", "Yellow", "White", "Black", "Pink"], phrase="likes {v}", noun="colour",
                   ask="Which colour does {x} like?", intro="likes a different colour among"),
    "pet": dict(values=["Dog", "Cat", "Parrot", "Rabbit", "Fish", "Hamster", "Tortoise"], phrase="keeps a {v}", noun="pet",
                ask="Which pet does {x} keep?", intro="keeps a different pet among"),
    "city": dict(values=["Delhi", "Mumbai", "Pune", "Jaipur", "Lucknow", "Patna", "Indore"], phrase="is from {v}", noun="city",
                 ask="Which city is {x} from?", intro="is from a different city among"),
    "fruit": dict(values=["Apple", "Mango", "Banana", "Grapes", "Orange", "Papaya", "Guava"], phrase="likes {v}", noun="fruit",
                  ask="Which fruit does {x} like?", intro="likes a different fruit among"),
    "subject": dict(values=["Physics", "Maths", "Biology", "History", "Economics", "Geography", "Chemistry"], phrase="teaches {v}", noun="subject",
                    ask="Which subject does {x} teach?", intro="teaches a different subject among"),
}


def make_story(rng, kind):
    """Pick the size and (for two-attribute puzzles) the attribute theme of a puzzle set."""
    n = {"linear": rng.choice([7, 8]), "circular": rng.choice([6, 8]), "floors": rng.choice([5, 6]), "days": rng.choice([5, 6])}[kind]
    st = dict(n=n, kind=kind)
    if kind == "floors":
        th = ATTR_THEMES[rng.choice(["colour", "pet", "city", "fruit"])]
    elif kind == "days":
        th = ATTR_THEMES["subject"]
    else:
        th = None
    if th:
        st.update(role="lecturer" if kind == "days" else "person", phrase=th["phrase"], noun=th["noun"], ask=th["ask"], intro_attr=th["intro"],
                  attr=rng.sample(th["values"], n))
    else:
        st.update(role="person", phrase="likes {v}", attr=[])
    return st


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def make_clue(rng, kind, n, ents_pool, story, hidden_pos, want=True):
    """Return a Clue that is TRUE under hidden_pos (entity -> position), or None."""
    st = story
    d = lambda e: desc(e, st)
    ks = rng.choice(["imm_left", "imm_right", "kth_left", "kth_right", "between", "adj", "not_adj", "gap", "end", "not_end",
                     "left_of", "right_of", "count_right", "count_left"])
    a, b, c = rng.sample(ents_pool, 3)
    k = rng.randint(2, 4)
    g = rng.randint(1, 3)
    p = hidden_pos
    if kind == "linear":
        F = {
            "imm_left": (f"{d(a)} sits immediately to the left of {d(b)}", lambda q: q(a) == q(b) - 1),
            "imm_right": (f"{d(a)} sits immediately to the right of {d(b)}", lambda q: q(a) == q(b) + 1),
            "kth_left": (f"{d(a)} sits {ORD[k - 1]} to the left of {d(b)}", lambda q: q(a) == q(b) - k),
            "kth_right": (f"{d(a)} sits {ORD[k - 1]} to the right of {d(b)}", lambda q: q(a) == q(b) + k),
            "between": (f"{d(a)} sits somewhere between {d(b)} and {d(c)}", lambda q: min(q(b), q(c)) < q(a) < max(q(b), q(c))),
            "adj": (f"{d(a)} sits next to {d(b)}", lambda q: abs(q(a) - q(b)) == 1),
            "not_adj": (f"{d(a)} does not sit next to {d(b)}", lambda q: abs(q(a) - q(b)) > 1),
            "gap": (f"Exactly {['', 'one person', 'two persons', 'three persons'][g]} sit{'s' if g == 1 else ''} between {d(a)} and {d(b)}", lambda q: abs(q(a) - q(b)) == g + 1),
            "end": (f"{d(a)} sits at one of the extreme ends of the row", lambda q: q(a) in (0, n - 1)),
            "not_end": (f"{d(a)} does not sit at either extreme end", lambda q: q(a) not in (0, n - 1)),
            "left_of": (f"{d(a)} sits somewhere to the left of {d(b)}", lambda q: q(a) < q(b)),
            "right_of": (f"{d(a)} sits somewhere to the right of {d(b)}", lambda q: q(a) > q(b)),
            "count_right": (f"Exactly {g + 1} persons sit to the right of {d(a)}", lambda q: q(a) == n - 2 - g),
            "count_left": (f"Exactly {g + 1} persons sit to the left of {d(a)}", lambda q: q(a) == g + 1),
        }
    elif kind == "circular":
        F = {
            "imm_left": (f"{d(a)} sits immediately to the left of {d(b)}", lambda q: (q(a) - q(b)) % n == 1),
            "imm_right": (f"{d(a)} sits immediately to the right of {d(b)}", lambda q: (q(b) - q(a)) % n == 1),
            "kth_left": (f"{d(a)} sits {ORD[k - 1]} to the left of {d(b)}", lambda q: (q(a) - q(b)) % n == k),
            "kth_right": (f"{d(a)} sits {ORD[k - 1]} to the right of {d(b)}", lambda q: (q(b) - q(a)) % n == k),
            "between": (f"{d(a)} sits between {d(b)} and {d(c)}", lambda q: {q(b) % n, q(c) % n} == {(q(a) - 1) % n, (q(a) + 1) % n}),
            "adj": (f"{d(a)} is an immediate neighbour of {d(b)}", lambda q: (q(a) - q(b)) % n in (1, n - 1)),
            "not_adj": (f"{d(a)} is not an immediate neighbour of {d(b)}", lambda q: (q(a) - q(b)) % n not in (0, 1, n - 1)),
            "gap": (f"{d(a)} sits opposite {d(b)}", lambda q: (q(a) - q(b)) % n == n // 2),
            "end": (f"{d(a)} sits second to the left of {d(b)}", lambda q: (q(a) - q(b)) % n == 2),
            "not_end": (f"{d(a)} does not sit opposite {d(b)}", lambda q: (q(a) - q(b)) % n != n // 2),
            "left_of": (f"{d(a)} sits third to the right of {d(b)}", lambda q: (q(b) - q(a)) % n == 3),
            "right_of": (f"{d(a)} sits third to the left of {d(b)}", lambda q: (q(a) - q(b)) % n == 3),
            "count_right": (f"{d(a)} sits opposite {d(b)}", lambda q: (q(a) - q(b)) % n == n // 2),
            "count_left": (f"Exactly two persons sit between {d(a)} and {d(b)} when counted from the left of {d(a)}", lambda q: (q(b) - q(a)) % n == 3),
        }
    else:                                                        # ordinal: floors or days
        fl = kind == "floors"
        w = (lambda e: f"{d(e)}")
        lbl = (lambda x: f"floor {x + 1}") if fl else (lambda x: DAYS[x])
        live = "lives" if fl else "lectures"
        F = {
            "imm_left": (f"{w(a)} {live} immediately {'below' if fl else 'before'} {w(b)}", lambda q: q(a) == q(b) - 1),
            "imm_right": (f"{w(a)} {live} immediately {'above' if fl else 'after'} {w(b)}", lambda q: q(a) == q(b) + 1),
            "kth_left": (f"{w(a)} {live} {k} {'floors' if fl else 'days'} {'below' if fl else 'before'} {w(b)}", lambda q: q(a) == q(b) - k),
            "kth_right": (f"{w(a)} {live} {k} {'floors' if fl else 'days'} {'above' if fl else 'after'} {w(b)}", lambda q: q(a) == q(b) + k),
            "between": (f"{w(a)} {live} somewhere between {w(b)} and {w(c)}", lambda q: min(q(b), q(c)) < q(a) < max(q(b), q(c))),
            "adj": (f"{w(a)} and {w(b)} {'live' if fl else 'lecture'} on consecutive {'floors' if fl else 'days'}", lambda q: abs(q(a) - q(b)) == 1),
            "not_adj": (f"{w(a)} and {w(b)} do not {'live' if fl else 'lecture'} on consecutive {'floors' if fl else 'days'}", lambda q: abs(q(a) - q(b)) > 1),
            "gap": (f"Exactly {g} {'floor' if fl else 'day'}{'s' if g > 1 else ''} separate{'' if g > 1 else 's'} {w(a)} and {w(b)}", lambda q: abs(q(a) - q(b)) == g + 1),
            "end": (f"{w(a)} {live} on {'the topmost or the lowest floor' if fl else 'the first or the last day of the week'}", lambda q: q(a) in (0, n - 1)),
            "not_end": (f"{w(a)} {'does not live' if fl else 'does not lecture'} on {'the topmost or the lowest floor' if fl else 'the first or the last day'}", lambda q: q(a) not in (0, n - 1)),
            "left_of": (f"{w(a)} {live} {'below' if fl else 'before'} {w(b)} (not necessarily immediately)", lambda q: q(a) < q(b)),
            "right_of": (f"{w(a)} {live} {'above' if fl else 'after'} {w(b)} (not necessarily immediately)", lambda q: q(a) > q(b)),
            "count_right": (f"{w(a)} {live} on an {'odd-numbered floor' if fl else 'odd-numbered day of the week (Monday = day 1)'}", lambda q: q(a) % 2 == 0),
            "count_left": (f"{w(a)} {live} on an {'even-numbered floor' if fl else 'even-numbered day of the week (Monday = day 1)'}", lambda q: q(a) % 2 == 1),
        }
        if rng.random() < 0.10:
            x = rng.choice(ents_pool)
            F["on"] = (f"{w(x)} {live} on {lbl(p[x])}", lambda q, x=x, v=p[x]: q(x) == v)
            ks, a = "on", x
    text, fn = F[ks]
    if bool(fn(lambda e: p[e])) != want:
        return None
    if kind == "circular":
        used = [a, b, c] if ks == "between" else [a, b]
    elif ks in ("end", "not_end", "count_right", "count_left", "on"):
        used = [a]
    elif ks == "between":
        used = [a, b, c]
    else:
        used = [a, b]
    return Clue(ks, used, k, text[0].upper() + text[1:] + ".", fn)


def perms_positions(n, kind):
    """All position assignments (tuples index->position). For circular, fix item 0 at seat 0 (rotation)."""
    if kind == "circular":
        return [(0,) + p for p in itertools.permutations(range(1, n))]
    return list(itertools.permutations(range(n)))


def solve_unique(rng, kind, people, attrs, story, tries=60):
    """Return (clues, solution) where solution is a dict entity -> position, unique."""
    n = len(people)
    for _ in range(tries):
        base = list(range(n))
        rng.shuffle(base)
        hp = {p_: base[i] for i, p_ in enumerate(people)}
        if kind == "circular":
            shift = hp[people[0]]
            hp = {k_: (v - shift) % n for k_, v in hp.items()}
        if attrs:
            ab = list(range(n))
            rng.shuffle(ab)
            hv = {v: ab[i] for i, v in enumerate(attrs)}
        else:
            hv = {}
        hidden = {**hp, **hv}
        circ = kind == "circular"
        clues = []
        if not attrs:
            surv = perms_positions(n, kind)
            idx = {p_: i for i, p_ in enumerate(people)}
            ok_runs = 0
            while len(surv) > 1 and len(clues) < 14:
                best = None
                for _c in range(9):
                    c = make_clue(rng, kind, n, people, story, hidden)
                    if not c:
                        continue
                    cnt = sum(1 for s in surv if c.fn(lambda e, s=s: s[idx[e]]))
                    if cnt >= 1 and (best is None or cnt < best[0]) and cnt < len(surv):
                        best = (cnt, c)
                if not best:
                    break
                clues.append(best[1])
                surv = [s for s in surv if best[1].fn(lambda e, s=s: s[idx[e]])]
            if len(surv) == 1 and 5 <= len(clues) <= 10:
                return clues, hidden
            continue
        # two attributes: persons-only, values-only, then cross clues
        pidx = {p_: i for i, p_ in enumerate(people)}
        vidx = {v: i for i, v in enumerate(attrs)}
        P = perms_positions(n, kind)
        V = perms_positions(n, kind) if not circ else perms_positions(n, kind)
        pc, vc, xc = [], [], []
        for pool, S, cl, idx in ((people, P, pc, pidx), (attrs, V, vc, vidx)):
            guard = 0
            while len(S) > 20 and guard < 40:
                guard += 1
                best = None
                for _c in range(7):
                    c = make_clue(rng, kind, n, pool, story, hidden)
                    if not c or (c.kind == "on" and any(x.kind == "on" for x in pc + vc)):
                        continue
                    cnt = sum(1 for s in S if c.fn(lambda e, s=s: s[idx[e]]))
                    if cnt >= 2 and (best is None or cnt < best[0]) and cnt < len(S):
                        best = (cnt, c)
                if best:
                    cl.append(best[1])
                    S[:] = [s for s in S if best[1].fn(lambda e, s=s: s[idx[e]])]
        pairs = [(a_, b_) for a_ in P for b_ in V]
        if len(pairs) > 900 or not pairs:
            continue
        both = people + attrs
        guard = 0
        while len(pairs) > 1 and guard < 40:
            guard += 1
            best = None
            for _c in range(10):
                c = make_clue(rng, kind, n, both, story, hidden)
                if not c or (c.kind == "on" and any(x.kind == "on" for x in pc + vc + xc)):
                    continue
                if not (any(not is_val(e) for e in c.ents) and any(is_val(e) for e in c.ents)) and c.kind != "on":
                    if rng.random() < 0.7:
                        continue
                cnt = sum(1 for (a_, b_) in pairs if c.fn(lambda e, a_=a_, b_=b_: a_[pidx[e]] if not is_val(e) else b_[vidx[e]]))
                if cnt >= 1 and (best is None or cnt < best[0]) and cnt < len(pairs):
                    best = (cnt, c)
            if not best:
                break
            xc.append(best[1])
            pairs = [(a_, b_) for (a_, b_) in pairs if best[1].fn(lambda e, a_=a_, b_=b_: a_[pidx[e]] if not is_val(e) else b_[vidx[e]])]
        if len(pairs) == 1 and len(xc) >= 2 and len(pc) + len(vc) + len(xc) <= 11:
            allc = pc + vc + xc
            rng.shuffle(allc)
            return allc, hidden
    raise RuntimeError("no unique puzzle for " + kind)


# -------------------------------------------------------------- puzzle sets
def clue_list_html(clues):
    return ('<ol style="margin:10px 0 0 20px;padding:0;line-height:1.75">'
            + "".join(f"<li>{c.text}</li>" for c in clues) + "</ol>")


def arrangement_text(kind, sol, people, attrs):
    n = len(people)
    by = lambda pos: [p_ for p_ in people if sol[p_] == pos][0]
    if kind == "linear":
        return "Final arrangement (left → right): " + " – ".join(by(i) for i in range(n))
    if kind == "circular":
        return ("Final arrangement (clockwise, everyone facing the centre; the 'left' of a person is the next person clockwise): "
                + " → ".join(by(i) for i in range(n)) + f" → back to {by(0)}")
    vby = lambda pos: [v for v in attrs if sol[v] == pos][0]
    if kind == "floors":
        return "Final arrangement (top to bottom): " + "; ".join(f"Floor {i + 1}: {by(i)} ({vby(i)})" for i in range(n - 1, -1, -1))
    return "Final arrangement (Monday to Saturday): " + "; ".join(f"{DAYS[i]}: {by(i)} ({vby(i)})" for i in range(n))


def facts_question(rng, kind, sol, pool, story, topic, header, stem, exclude=()):
    """One true + four false statements, all generated from the same clue templates and checked on the solution."""
    true = None
    for _ in range(400):
        true = make_clue(rng, kind, len(set(p for p in sol.values())), pool, story, sol, want=True)
        if true and true.text not in exclude:
            break
    falses, seen = [], {true.text}
    for _ in range(2000):
        c = make_clue(rng, kind, len(set(sol.values())), pool, story, sol, want=False)
        if c and c.text not in seen:
            seen.add(c.text)
            falses.append(c)
        if len(falses) == 4:
            break
    assert true and len(falses) == 4
    items = [true] + falses
    rng.shuffle(items)
    opts = [c.text.rstrip(".") for c in items]
    ans = items.index(true)
    return opts, ans, true.text


def prop_pairs(kind, n):
    def dist(a, b):
        d = abs(a - b)
        return min(d, n - d) if kind == "circular" else d
    props = {f"are {k} seat{'s' if k > 1 else ''} apart" if k > 1 else "are immediate neighbours": (lambda a, b, k=k: dist(a, b) == k) for k in range(1, 5)}
    props["are an even number of seats apart"] = lambda a, b: dist(a, b) % 2 == 0
    props["are an odd number of seats apart"] = lambda a, b: dist(a, b) % 2 == 1
    if kind == "linear":
        props["both sit in the left half of the row"] = lambda a, b: a < n // 2 and b < n // 2
        props["both sit in the right half of the row"] = lambda a, b: a >= n // 2 and b >= n // 2
    return props, dist


def odd_one_question(rng, kind, sol, people):
    n = len(people)
    props, dist = prop_pairs(kind, n)
    names = list(props)
    rng.shuffle(names)
    pairs = [(a, b) for a, b in itertools.combinations(people, 2)]
    for nm in names[:6]:
        f = props[nm]
        yes = [pr for pr in pairs if f(sol[pr[0]], sol[pr[1]])]
        no = [pr for pr in pairs if not f(sol[pr[0]], sol[pr[1]])]
        if len(yes) < 4 or not no:
            continue
        for _ in range(60):
            grp = rng.sample(yes, 4)
            odd = rng.choice(no)
            five = grp + [odd]
            clash = False
            for nm2, f2 in props.items():
                if nm2 == nm:
                    continue
                sat = [f2(sol[a], sol[b]) for a, b in five]
                if sat.count(True) == 4 and sat.index(False) != 4:
                    clash = True
                    break
                if sat.count(False) == 4 and sat.index(True) != 4:
                    clash = True
                    break
            if clash:
                continue
            rng.shuffle(five)
            opts = [f"{a} – {b}" for a, b in five]
            return opts, five.index(odd), nm
    return None


def stated(clue_texts, *ents):
    """True when one clue already mentions all the given persons (so the answer would be handed over directly)."""
    return any(all(re.search(rf"\b{e}\b", t) for e in ents) for t in clue_texts)


def puzzle_questions(rng, kind, sol, people, attrs, story, clue_texts=()):
    arr = arrangement_text(kind, sol, people, attrs)
    n = len(people)
    by = lambda pos: [p_ for p_ in people if sol[p_] == pos][0]
    T = TOPIC_PUZ
    out = []
    P = lambda p_: sol[p_]

    def between_q():
        x, y = rng.sample(people, 2)
        if kind == "circular":
            cnt = (P(y) - P(x)) % n - 1
            q = f"How many persons sit between {x} and {y} when counted from the left of {x}?"
            note = f"Counting clockwise from {x} up to {y}, the persons in between number {cnt}."
        elif kind == "linear":
            cnt = abs(P(x) - P(y)) - 1
            q = f"How many persons sit between {x} and {y}?"
            note = f"{x} and {y} are {abs(P(x) - P(y))} places apart, so {cnt} person(s) sit between them."
        else:
            cnt = abs(P(x) - P(y)) - 1
            unit = "floors" if kind == "floors" else "days"
            q = f"How many {'persons live' if kind == 'floors' else 'lectures take place'} between {x} and {y}{' (floors)' if False else ''}?" if False else f"How many {unit} separate {x} and {y}?"
            note = f"{x} and {y} are {abs(P(x) - P(y))} {unit} apart, so {cnt} {unit[:-1]}(s) lie between them."
        return Q(T, q, COUNT_OPTS, count_answer(cnt), f"{arr}<br>{note} <b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")

    def facts_q():
        pool = people if not attrs else people + attrs
        opts, ans, t = facts_question(rng, kind, sol, pool, story, T, "", "", exclude=set(clue_texts))
        return Q(T, "Which of the following statements is true?", opts, ans, f"{arr}<br>Checking each option against this arrangement, only this one holds: <b>{t}</b>")

    def odd_q():
        r = odd_one_question(rng, kind, sol, people)
        if not r:
            return None
        opts, ans, nm = r
        return Q(T, "Four of the following five pairs are alike in a certain way based on the final arrangement and so form a group. Which pair does not belong to the group?",
                 opts, ans, f"{arr}<br>In four pairs the two persons {nm}; the pair <b>{opts[ans]}</b> does not.")

    if kind == "linear":
        def who_at():
            r, side = rng.randint(0, n - 1), rng.choice(["left", "right"])
            tgt = by(r) if side == "left" else by(n - 1 - r)
            where = f"at the extreme {side} end" if r == 0 else f"{ORD[r]} from the {side} end"
            o, a = pick_opts(rng, tgt, people, key=str)
            return Q(T, f"Who sits {where} of the row?", o, a, f"{arr}<br>The person {where} is <b>{tgt}</b>.")

        def neighbour():
            side = rng.choice(["left", "right"])
            cands = [x for x in people if (P(x) > 0 if side == "left" else P(x) < n - 1)]
            for _t in range(40):
                x = rng.choice(cands)
                tgt = by(P(x) - 1) if side == "left" else by(P(x) + 1)
                if not stated(clue_texts, x, tgt):
                    break
            o, a = pick_opts(rng, tgt, [p_ for p_ in people if p_ != x], key=str)
            return Q(T, f"Who sits immediately to the {side} of {x}?", o, a, f"{arr}<br>The person immediately to the {side} of {x} is <b>{tgt}</b>.")

        def second():
            side = rng.choice(["left", "right"])
            cands = [x for x in people if (P(x) > 1 if side == "left" else P(x) < n - 2)]
            for _t in range(40):
                x = rng.choice(cands)
                tgt = by(P(x) - 2) if side == "left" else by(P(x) + 2)
                if not stated(clue_texts, x, tgt):
                    break
            o, a = pick_opts(rng, tgt, [p_ for p_ in people if p_ != x], key=str)
            return Q(T, f"Who sits second to the {side} of {x}?", o, a, f"{arr}<br>Second to the {side} of {x} is <b>{tgt}</b>.")

        def position():
            x = rng.choice(people)
            side = rng.choice(["left", "right"])
            r = P(x) if side == "left" else n - 1 - P(x)
            words = [ORD[i].capitalize() for i in range(n)]
            o, a = pick_opts(rng, words[r], words, key=words.index)
            return Q(T, f"What is the position of {x} from the {side} end of the row?", o, a, f"{arr}<br>{x} is <b>{words[r].lower()}</b> from the {side} end.")
        fns = [who_at, between_q, rng.choice([neighbour, second]), facts_q, odd_q, position]
        order = [who_at, between_q, facts_q, odd_q, rng.choice([neighbour, second, position])]
    elif kind == "circular":
        def opposite():
            for _t in range(40):
                x = rng.choice(people)
                tgt = by((P(x) + n // 2) % n)
                if not stated(clue_texts, x, tgt):
                    break
            o, a = pick_opts(rng, tgt, [p_ for p_ in people if p_ != x], key=str)
            return Q(T, f"Who sits opposite {x}?", o, a, f"{arr}<br>The person directly opposite {x} is <b>{tgt}</b>.")

        def second_left():
            side = rng.choice(["left", "right"])
            for _t in range(40):
                x = rng.choice(people)
                tgt = by((P(x) + 2) % n) if side == "left" else by((P(x) - 2) % n)
                if not stated(clue_texts, x, tgt):
                    break
            o, a = pick_opts(rng, tgt, [p_ for p_ in people if p_ != x], key=str)
            return Q(T, f"Who sits second to the {side} of {x}?", o, a, f"{arr}<br>Second to the {side} of {x} is <b>{tgt}</b>.")

        def who_between():
            for _t in range(40):
                z = rng.choice(people)
                l, r_ = by((P(z) + 1) % n), by((P(z) - 1) % n)
                if not stated(clue_texts, z, l, r_):
                    break
            pool = [p_ for p_ in people if p_ not in (l, r_, z)]
            if len(pool) < 4:
                pool = [p_ for p_ in people if p_ != z]
            o, a = pick_opts(rng, z, pool, key=str)
            return Q(T, f"Who sits exactly between {l} and {r_}?", o, a, f"{arr}<br>{l} and {r_} are the two neighbours of <b>{z}</b>.")
        order = [opposite, second_left, between_q, facts_q, odd_q]
        rng.shuffle(order)
        if rng.random() < 0.5:
            order[0] = who_between
    else:
        def who_on():
            pos = rng.randrange(n)
            tgt = by(pos)
            lab = f"floor {pos + 1}" if kind == "floors" else DAYS[pos]
            o, a = pick_opts(rng, tgt, people, key=str)
            q = f"Who lives on {lab}?" if kind == "floors" else f"Who lectures on {DAYS[pos]}?"
            return Q(T, q, o, a, f"{arr}<br>On {lab} it is <b>{tgt}</b>.")

        def attr_of():
            x = rng.choice(people)
            val = [v for v in attrs if sol[v] == P(x)][0]
            o, a = pick_opts(rng, val, attrs, key=str)
            q = story["ask"].format(x=x)
            return Q(T, q, o, a, f"{arr}<br>{x}: <b>{val}</b>.")

        def where_attr():
            v = rng.choice(attrs)
            pos = sol[v]
            lab = lambda i: f"Floor {i + 1}" if kind == "floors" else DAYS[i]
            o, a = pick_opts(rng, lab(pos), [lab(i) for i in range(n)], key=lambda t: [lab(i) for i in range(n)].index(t))
            who = desc(v, story)
            q = (f"On which floor does {who} live?" if kind == "floors" else f"On which day does {who} lecture?")
            return Q(T, q, o, a, f"{arr}<br>{v} belongs to <b>{lab(pos)}</b>.")

        def combo():
            lab = lambda i: f"floor {i + 1}" if kind == "floors" else DAYS[i]
            x = rng.choice(people)
            true = (x, [v for v in attrs if sol[v] == P(x)][0], lab(P(x)))
            wrong = []
            for _ in range(200):
                y = rng.choice(people)
                v = rng.choice(attrs)
                l = lab(rng.randrange(n))
                cand = (y, v, l)
                if not (sol[v] == P(y) and lab(P(y)) == l) and cand not in wrong and cand != true:
                    wrong.append(cand)
                if len(wrong) == 4:
                    break
            items = [true] + wrong
            rng.shuffle(items)
            opts = [f"{a} – {b} – {c}" for a, b, c in items]
            return Q(T, "Which of the following combinations (person – " + story["noun"] + " – " + ("floor" if kind == "floors" else "day") + ") is correct?",
                     opts, items.index(true), f"{arr}<br>The only correct combination is <b>{true[0]} – {true[1]} – {true[2]}</b>.")

        def attr_neighbour():
            v = rng.choice(attrs)
            if kind == "floors":
                cands = [(v_, "above") for v_ in [v] if sol[v_] < n - 1] + [(v, "below") for _ in [0] if sol[v] > 0]
            else:
                cands = [(v, "after")] if sol[v] < n - 1 else []
                cands += [(v, "before")] if sol[v] > 0 else []
            v_, side = rng.choice(cands)
            step = 1 if side in ("above", "after") else -1
            tgt = by(sol[v_] + step)
            o, a = pick_opts(rng, tgt, people, key=str)
            q = (f"Who lives immediately {side} {desc(v_, story)}?" if kind == "floors" else f"Who lectures immediately {side} {desc(v_, story)}?")
            return Q(T, q, o, a, f"{arr}<br>The person immediately {side} {v_}'s person is <b>{tgt}</b>.")
        pool_fns = [who_on, attr_of, between_q, combo, where_attr, attr_neighbour, odd_q]
        order = [who_on, attr_of, between_q, combo, rng.choice([where_attr, attr_neighbour])]
        rng.shuffle(order)
    for fn in order:
        q = fn()
        if q is None:
            return None
        out.append(q)
    keys = {q["q"] for q in out}
    if len(keys) < 5:
        return None
    return out


def puzzle_set(rng, kind):
    for _ in range(40):
        story = make_story(rng, kind)
        n = story["n"]
        if kind in ("linear", "circular"):
            people = list(LETTERS[:n]) if rng.random() < 0.5 else sorted(rng.sample(list("ABCDEFGHJKLMNPQRSTUVWXYZ"), n))
        else:
            people = sorted(rng.sample(list("ABCDEFGHJKLMNPQRST"), n))
        attrs = story["attr"]
        try:
            clues, sol = solve_unique(rng, kind, people, attrs, story, tries=25)
        except RuntimeError:
            continue
        verify_puzzle(kind, people, attrs, [c.text for c in clues], sol)
        qs = puzzle_questions(rng, kind, sol, people, attrs, story, [c.text for c in clues])
        if qs:
            break
    else:
        raise RuntimeError("puzzle set " + kind)
    plist = ", ".join(people)
    N = NUMW[n]
    if kind == "linear":
        title, lead = f"Puzzle · {N} persons in a row", (f"<p>{N} persons {plist} sit in a straight row facing north, each at a different position. "
                                                          "'Left' and 'right' are as seen by the seated persons themselves.</p>")
    elif kind == "circular":
        title, lead = f"Puzzle · Circular seating of {n}", (f"<p>{N} persons {plist} sit around a circular table, all facing the centre, each at a different place. "
                                                            "'Left' and 'right' are as seen by the seated persons themselves.</p>")
    elif kind == "floors":
        title, lead = "Puzzle · Floors and " + (story["noun"][:-1] + "ies" if story["noun"].endswith("y") else story["noun"] + "s"), (f"<p>{N} persons {plist} live on different floors of a {n}-storey building (floor 1 is the lowest and floor {n} the topmost). "
                                                              f"Each of them {story['intro_attr']} {', '.join(attrs)}.</p>")
    else:
        title, lead = "Puzzle · Lecture schedule", (f"<p>{N} lecturers {plist} each take exactly one lecture, on different days from Monday to {DAYS[n - 1]} (one lecture per day). "
                                                    f"Each {story['intro_attr']} {', '.join(attrs)}.</p>")
    return title, lead + clue_list_html(clues), qs


# ------------------------------------------------ independent re-check of a puzzle
# The clue TEXT is parsed again with separate English-semantics code and the puzzle is re-solved
# by brute force; the result must be exactly one solution equal to the intended one.
import re

_ORDN = {"second": 2, "third": 3, "fourth": 4, "fifth": 5}
_ENT = r"(the (?:person|lecturer) who (?:likes|teaches|keeps a|is from) [A-Za-z]+|\b[A-Z]\b)"
_NUM = {"one": 1, "two": 2, "three": 3, "four": 4}


def _ent_key(t):
    t = t.strip()
    return t.split()[-1] if t.startswith("the ") else t


def parse_clue(text, kind, n):
    """-> (entities, predicate(pos)) where pos maps entity -> position."""
    t = text.rstrip(".")
    t = "the " + t[4:] if t.startswith("The ") else t
    E = _ENT
    def m(rx):
        return re.fullmatch(re.sub(r"(?<![A-Za-z])E(?![a-z])", lambda _m: E, rx), t)
    circ, floors = kind == "circular", kind == "floors"
    chk = []
    if kind in ("linear", "circular"):
        a = m(r"E sits immediately to the (left|right) of E")
        if a:
            x, side, y = _ent_key(a[1]), a[2], _ent_key(a[3])
            if circ:
                return [x, y], (lambda q: (q[x] - q[y]) % n == 1) if side == "left" else (lambda q: (q[y] - q[x]) % n == 1)
            return [x, y], (lambda q: q[x] == q[y] - 1) if side == "left" else (lambda q: q[x] == q[y] + 1)
        a = m(r"E sits (second|third|fourth|fifth) to the (left|right) of E")
        if a:
            x, k, side, y = _ent_key(a[1]), _ORDN[a[2]], a[3], _ent_key(a[4])
            if circ:
                return [x, y], (lambda q: (q[x] - q[y]) % n == k) if side == "left" else (lambda q: (q[y] - q[x]) % n == k)
            return [x, y], (lambda q: q[x] == q[y] - k) if side == "left" else (lambda q: q[x] == q[y] + k)
        a = m(r"E sits somewhere between E and E")
        if a:
            x, y, z = _ent_key(a[1]), _ent_key(a[2]), _ent_key(a[3])
            return [x, y, z], lambda q: min(q[y], q[z]) < q[x] < max(q[y], q[z])
        a = m(r"E sits between E and E")
        if a:
            x, y, z = _ent_key(a[1]), _ent_key(a[2]), _ent_key(a[3])
            return [x, y, z], lambda q: {q[y], q[z]} == {(q[x] - 1) % n, (q[x] + 1) % n}
        a = m(r"E (?:sits next to|is an immediate neighbour of) E")
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2])
            return [x, y], (lambda q: (q[x] - q[y]) % n in (1, n - 1)) if circ else (lambda q: abs(q[x] - q[y]) == 1)
        a = m(r"E (?:does not sit next to|is not an immediate neighbour of) E")
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2])
            return [x, y], (lambda q: (q[x] - q[y]) % n not in (0, 1, n - 1)) if circ else (lambda q: abs(q[x] - q[y]) > 1)
        a = m(r"Exactly (one person|two persons|three persons) sits? between E and E")
        if a:
            k = _NUM[a[1].split()[0]]
            x, y = _ent_key(a[2]), _ent_key(a[3])
            return [x, y], lambda q: abs(q[x] - q[y]) == k + 1
        a = m(r"E sits at one of the extreme ends of the row")
        if a:
            x = _ent_key(a[1]); return [x], lambda q: q[x] in (0, n - 1)
        a = m(r"E does not sit at either extreme end")
        if a:
            x = _ent_key(a[1]); return [x], lambda q: q[x] not in (0, n - 1)
        a = m(r"E sits somewhere to the (left|right) of E")
        if a:
            x, side, y = _ent_key(a[1]), a[2], _ent_key(a[3])
            return [x, y], (lambda q: q[x] < q[y]) if side == "left" else (lambda q: q[x] > q[y])
        a = m(r"Exactly (\d) persons sit to the (right|left) of E")
        if a:
            k, side, x = int(a[1]), a[2], _ent_key(a[3])
            return [x], (lambda q: n - 1 - q[x] == k) if side == "right" else (lambda q: q[x] == k)
        a = m(r"E sits opposite E")
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2]); return [x, y], lambda q: (q[x] - q[y]) % n == n // 2
        a = m(r"E does not sit opposite E")
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2]); return [x, y], lambda q: (q[x] - q[y]) % n != n // 2
        a = m(r"Exactly two persons sit between E and E when counted from the left of E")
        if a:
            x, y, z = _ent_key(a[1]), _ent_key(a[2]), _ent_key(a[3])
            assert x == z
            return [x, y], lambda q: (q[y] - q[x]) % n == 3
    else:
        U = "floors" if floors else "days"
        up, dn = ("above", "below") if floors else ("after", "before")
        verb = "lives" if floors else "lectures"
        a = m(r"E %s immediately (%s|%s) E" % (verb, up, dn))
        if a:
            x, w, y = _ent_key(a[1]), a[2], _ent_key(a[3])
            return [x, y], (lambda q: q[x] == q[y] + 1) if w == up else (lambda q: q[x] == q[y] - 1)
        a = m(r"E %s (\d) %s (%s|%s) E" % (verb, U, up, dn))
        if a:
            x, k, w, y = _ent_key(a[1]), int(a[2]), a[3], _ent_key(a[4])
            return [x, y], (lambda q: q[x] == q[y] + k) if w == up else (lambda q: q[x] == q[y] - k)
        a = m(r"E %s somewhere between E and E" % verb)
        if a:
            x, y, z = _ent_key(a[1]), _ent_key(a[2]), _ent_key(a[3])
            return [x, y, z], lambda q: min(q[y], q[z]) < q[x] < max(q[y], q[z])
        a = m(r"E and E %s on consecutive %s" % ("live" if floors else "lecture", U))
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2]); return [x, y], lambda q: abs(q[x] - q[y]) == 1
        a = m(r"E and E do not %s on consecutive %s" % ("live" if floors else "lecture", U))
        if a:
            x, y = _ent_key(a[1]), _ent_key(a[2]); return [x, y], lambda q: abs(q[x] - q[y]) > 1
        a = m(r"Exactly (\d) %s separates? E and E" % ("floors?" if floors else "days?"))
        if a:
            g = int(a[1]); x, y = _ent_key(a[2]), _ent_key(a[3]); return [x, y], lambda q: abs(q[x] - q[y]) == g + 1
        a = m(r"E %s on the (?:topmost or the lowest floor|first or the last day of the week)" % verb)
        if a:
            x = _ent_key(a[1]); return [x], lambda q: q[x] in (0, n - 1)
        a = m(r"E does not %s on the (?:topmost or the lowest floor|first or the last day)" % ("live" if floors else "lecture"))
        if a:
            x = _ent_key(a[1]); return [x], lambda q: q[x] not in (0, n - 1)
        a = m(r"E %s (%s|%s) E \(not necessarily immediately\)" % (verb, up, dn))
        if a:
            x, w, y = _ent_key(a[1]), a[2], _ent_key(a[3])
            return [x, y], (lambda q: q[x] > q[y]) if w == up else (lambda q: q[x] < q[y])
        a = m(r"E %s on an (odd|even)-numbered (?:floor|day of the week \(Monday = day 1\))" % verb)
        if a:
            x = _ent_key(a[1]); par = 1 if a[2] == "odd" else 0
            return [x], lambda q: (q[x] + 1) % 2 == par
        a = m(r"E %s on (floor \d|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)" % verb)
        if a:
            x = _ent_key(a[1]); w = a[2]
            v = int(w.split()[1]) - 1 if w.startswith("floor") else DAYS.index(w)
            return [x], lambda q: q[x] == v
    raise ValueError("unparsed clue: " + text)


def verify_puzzle(kind, people, attrs, clue_texts, sol):
    n = len(people)
    parsed = [parse_clue(t, kind, n) for t in clue_texts]
    is_p = lambda e: e in people
    P = perms_positions(n, kind)
    if not attrs:
        hits = []
        for perm in P:
            q = {p_: perm[i] for i, p_ in enumerate(people)}
            if all(fn(q) for _, fn in parsed):
                hits.append(q)
        assert len(hits) == 1 and hits[0] == {p_: sol[p_] for p_ in people}, (kind, len(hits))
        return True
    V = perms_positions(n, kind)
    pc = [c for c in parsed if all(is_p(e) for e in c[0])]
    vc = [c for c in parsed if all(not is_p(e) for e in c[0])]
    xc = [c for c in parsed if c not in pc and c not in vc]
    Pf = [perm for perm in P if all(fn({p_: perm[i] for i, p_ in enumerate(people)}) for _, fn in pc)]
    Vf = [perm for perm in V if all(fn({v: perm[i] for i, v in enumerate(attrs)}) for _, fn in vc)]
    hits = []
    for pp in Pf:
        for vv in Vf:
            q = {**{p_: pp[i] for i, p_ in enumerate(people)}, **{v: vv[i] for i, v in enumerate(attrs)}}
            if all(fn(q) for _, fn in xc):
                hits.append(q)
    assert len(hits) == 1 and hits[0] == {k: sol[k] for k in people + attrs}, (kind, len(hits))
    return True


# ================================================================ syllogism
WORDS = ["Loan", "Deposit", "Cheque", "Branch", "Card", "Account", "Vault", "Ledger", "Teller", "Cash", "Bond", "Share", "Policy", "Wallet"]
CONC_OPTS = ["Only conclusion I follows", "Only conclusion II follows", "Either conclusion I or II follows",
             "Neither conclusion I nor II follows", "Both conclusions I and II follow"]
FORMS = ["all", "some", "no", "somenot", "few"]
NREG = 4
M_IN = [sum(1 << (r - 1) for r in range(1, 1 << NREG) if r >> i & 1) for i in range(NREG)]
M_AND = [[M_IN[i] & M_IN[j] for j in range(NREG)] for i in range(NREG)]
M_DIFF = [[M_IN[i] & ~M_IN[j] & ((1 << ((1 << NREG) - 1)) - 1) for j in range(NREG)] for i in range(NREG)]
ALL_MODELS = [m for m in range(1, 1 << ((1 << NREG) - 1)) if all(m & M_IN[i] for i in range(NREG))]


def holds(form, i, j, m):
    if form == "all":
        return not (m & M_DIFF[i][j])
    if form == "some":
        return bool(m & M_AND[i][j])
    if form == "no":
        return not (m & M_AND[i][j])
    if form == "somenot":
        return bool(m & M_DIFF[i][j])
    if form == "few":
        return bool(m & M_AND[i][j]) and bool(m & M_DIFF[i][j])
    if form == "poss_some":
        raise ValueError
    raise ValueError(form)


def plural(w):
    if w.endswith(("s", "sh", "ch", "x")):
        return w + "es"
    if w.endswith("y") and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    return w + "s"


def art(w):
    return ("an " if w[0] in "AEIOU" else "a ") + w


def sent(form, a, b):
    return {"all": f"All {plural(a)} are {plural(b)}", "some": f"Some {plural(a)} are {plural(b)}", "no": f"No {a} is {art(b)}",
            "somenot": f"Some {plural(a)} are not {plural(b)}", "few": f"Only a few {plural(a)} are {plural(b)}"}[form]


CONTRA = {("some", "no"), ("no", "some"), ("all", "somenot"), ("somenot", "all")}


def region_text(m, names):
    parts = []
    for r in range(1, 1 << NREG):
        if m >> (r - 1) & 1:
            ins = [names[i] for i in range(NREG) if r >> i & 1]
            parts.append(("only " + ins[0]) if len(ins) == 1 else " & ".join(ins))
    return "; ".join(parts)


def syllogism(rng, want):
    topic = "Syllogism"
    for _ in range(6000):
        names = rng.sample(WORDS, NREG)
        nstm = rng.choice([2, 3, 3])
        nterms = nstm + 1
        chain = [(rng.choice(FORMS), i, i + 1) for i in range(nstm)]
        if rng.random() < 0.5:
            chain = [(f, a, b) if rng.random() < 0.7 else (f, b, a) for f, a, b in chain]
        models = [m for m in ALL_MODELS if all(holds(f, a, b, m) for f, a, b in chain)]
        if not models:
            continue

        def mk():
            poss = rng.random() < 0.25
            f = rng.choice(["some", "all", "somenot"]) if poss else rng.choice(FORMS)
            i_, j_ = rng.sample(range(nterms), 2)
            return (f, i_, j_, poss)

        if want == 2:
            i_, j_ = rng.sample(range(nterms), 2)
            f1, f2 = rng.choice(sorted(CONTRA))
            c1, c2 = (f1, i_, j_, False), (f2, i_, j_, False)
        else:
            c1, c2 = mk(), mk()
            if c1 == c2:
                continue

        def truth(c):
            if c[3]:
                const = any(holds(c[0], c[1], c[2], m) for m in models)
                return [const] * len(models)
            return [holds(c[0], c[1], c[2], m) for m in models]
        t1, t2 = truth(c1), truth(c2)
        d1, d2 = all(t1), all(t2)
        either = all(a or b for a, b in zip(t1, t2))
        if d1 and d2:
            code = 4
        elif d1:
            code = 0
        elif d2:
            code = 1
        elif either:
            code = 2
        else:
            code = 3
        if code != want:
            continue
        stm = [sent(f, names[a], names[b]) for f, a, b in chain]
        ctext = lambda c: ("Possibility: " if c[3] else "") + sent(c[0], names[c[1]], names[c[2]])
        q = ("Directions: Take the statements to be true even if they contradict known facts and decide which conclusion(s) follow. "
             "('Only a few A are B' means some A are B and some A are not B.)\n"
             "Statements: " + ". ".join(stm) + ".\nConclusions:\nI. " + ctext(c1) + "\nII. " + ctext(c2))
        lines = []
        for lab, c, t, d in (("I", c1, t1, d1), ("II", c2, t2, d2)):
            if c[3]:
                lines.append(f"{lab}. \"{sent(c[0], names[c[1]], names[c[2]])}\" " + ("can be true in at least one case consistent with the statements → the possibility holds." if d
                                                                                       else "is false in every case consistent with the statements → the possibility does not hold."))
            elif d:
                lines.append(f"{lab}. \"{ctext(c)}\" holds in every case consistent with the statements → follows.")
            else:
                cm = next(m for m, ok in zip(models, t) if not ok)
                lines.append(f"{lab}. \"{ctext(c)}\" fails in at least one valid case (e.g. when the only existing kinds of items are: {region_text(cm, names)}) → does not definitely follow.")
        extra = "I and II are complementary (exactly one of them is always true) → either follows. " if code == 2 else ""
        exp = "<br>".join(lines) + f"<br>{extra}<b>Answer: {CONC_OPTS[code]}</b>"
        return Q(topic, q, CONC_OPTS, code, exp)
    raise RuntimeError("syllogism")


# ================================================================ inequality
REL = {">": "is greater than", "<": "is less than", "≥": "is greater than or equal to", "≤": "is less than or equal to", "=": "is equal to"}
COMP = {">": "≤", "<": "≥", "≥": "<", "≤": ">"}
SYMS = ["@", "#", "$", "%", "©", "*", "δ", "&", "★"]


def rel_ok(r, x, y):
    return {">": x > y, "<": x < y, "≥": x >= y, "≤": x <= y, "=": x == y}[r]


def inequality(rng, want):
    RELS = [">", "<", "≥", "≤", "="]
    for _ in range(6000):
        layout = rng.choice(["chain5", "chain4", "two"])
        nL = 4 if layout == "chain4" else 5
        letters = rng.sample(list("ABCDEFGHJKLMNPQRSTUVWXYZ"), nL)
        syms = rng.sample(SYMS, 5)
        code = dict(zip(RELS, syms))
        rr = lambda: rng.choice([">", "<", "≥", "≤", "=", ">", "<", "≥", "≤"])
        if layout == "chain5":
            lines = [[(0, rr(), 1), (1, rr(), 2), (2, rr(), 3), (3, rr(), 4)]]
        elif layout == "chain4":
            lines = [[(0, rr(), 1), (1, rr(), 2), (2, rr(), 3)]]
        else:
            lines = [[(0, rr(), 1), (1, rr(), 2)], [(3, rr(), 1), (1, rr(), 4)]]
        cons = [c for ln in lines for c in ln]
        models = [v for v in itertools.product(range(5), repeat=nL) if all(rel_ok(r_, v[a], v[b]) for a, r_, b in cons)]
        if not models:
            continue
        if want == 2:
            x, y = rng.sample(range(nL), 2)
            r1 = rng.choice(["<", ">", "≥", "≤"])
            c1, c2 = (x, r1, y), (x, COMP[r1], y)
        else:
            x, y = rng.sample(range(nL), 2)
            c1 = (x, rng.choice(RELS), y)
            x2, y2 = rng.sample(range(nL), 2)
            c2 = (x2, rng.choice(RELS), y2)
            if c1 == c2:
                continue
        t1 = [rel_ok(c1[1], v[c1[0]], v[c1[2]]) for v in models]
        t2 = [rel_ok(c2[1], v[c2[0]], v[c2[2]]) for v in models]
        d1, d2 = all(t1), all(t2)
        either = all(a or b for a, b in zip(t1, t2))
        res = 4 if d1 and d2 else 0 if d1 else 1 if d2 else 2 if either else 3
        if res != want:
            continue

        def det(x, y):
            seen = {("=" if v[x] == v[y] else ">" if v[x] > v[y] else "<") for v in models}
            return {frozenset([">"]): f"{letters[x]} > {letters[y]}", frozenset(["<"]): f"{letters[x]} < {letters[y]}", frozenset(["="]): f"{letters[x]} = {letters[y]}",
                    frozenset([">", "="]): f"{letters[x]} ≥ {letters[y]}", frozenset(["<", "="]): f"{letters[x]} ≤ {letters[y]}"}.get(frozenset(seen), "no definite relation")

        def line_text(ln, coded):
            out = letters[ln[0][0]]
            for a, r_, b in ln:
                out += f" {code[r_] if coded else r_} {letters[b]}"
            return out
        s_coded = "\n".join(line_text(ln, True) for ln in lines)
        s_plain = "; ".join(line_text(ln, False) for ln in lines)
        legend = "; ".join(f"'P {code[r_]} Q' means 'P {REL[r_]} Q'" for r_ in RELS)
        cc = lambda c: f"{letters[c[0]]} {code[c[1]]} {letters[c[2]]}"
        cp = lambda c: f"{letters[c[0]]} {c[1]} {letters[c[2]]}"
        head = "Statements:" if len(lines) > 1 else "Statement:"
        q = (f"Directions: In the question below, the symbols {', '.join(syms)} are used as follows: {legend}.\n"
             "Assuming the statement(s) to be true, decide which of the conclusions I and II is/are definitely true.\n"
             f"{head}\n{s_coded}\nConclusions:\nI. {cc(c1)}\nII. {cc(c2)}")
        out_lines = [f"Decoding: {s_plain}.",
                     f"I. {cp(c1)}: from the statement(s), {det(c1[0], c1[2])} → {'true' if d1 else 'not definitely true'}.",
                     f"II. {cp(c2)}: from the statement(s), {det(c2[0], c2[2])} → {'true' if d2 else 'not definitely true'}."]
        if res == 2:
            out_lines.append("I and II are opposite cases of each other (one of them must be true) → either follows.")
        return Q("Inequality", q, CONC_OPTS, res, "<br>".join(out_lines) + f"<br><b>Answer: {CONC_OPTS[res]}</b>")
    raise RuntimeError("inequality")


# ================================================================ blood relations
class Fam:
    def __init__(self):
        self.g, self.father, self.mother, self.spouse = {}, {}, {}, {}
        self.virt = 0

    def node(self, x):
        self.g.setdefault(x, None)

    def setg(self, x, g):
        self.node(x)
        if self.g[x] not in (None, g):
            raise ValueError("gender clash")
        self.g[x] = g

    def newvirt(self, g):
        self.virt += 1
        v = f"_v{self.virt}"
        self.g[v] = g
        return v

    def parents_of(self, x):
        self.node(x)
        if x not in self.father:
            self.father[x] = self.newvirt("M")
        if x not in self.mother:
            self.mother[x] = self.newvirt("F")
        return self.father[x], self.mother[x]

    def set_parent(self, child, parent, g):
        self.setg(parent, g)
        self.node(child)
        d = self.father if g == "M" else self.mother
        if child in d and d[child] != parent:
            raise ValueError("parent clash")
        d[child] = parent

    def make_sibs(self, a, b):
        fa, ma = self.parents_of(a)
        if b in self.father and self.father[b] != fa:
            raise ValueError("clash")
        if b in self.mother and self.mother[b] != ma:
            raise ValueError("clash")
        self.father[b], self.mother[b] = fa, ma

    def marry(self, h, w):
        self.setg(h, "M")
        self.setg(w, "F")
        if self.spouse.get(h, w) != w or self.spouse.get(w, h) != h:
            raise ValueError("spouse clash")
        self.spouse[h], self.spouse[w] = w, h

    def apply(self, rel, a, b):
        """a is the <rel> of b."""
        if rel == "father":
            self.set_parent(b, a, "M")
        elif rel == "mother":
            self.set_parent(b, a, "F")
        elif rel == "brother":
            self.setg(a, "M"); self.make_sibs(a, b)
        elif rel == "sister":
            self.setg(a, "F"); self.make_sibs(a, b)
        elif rel == "husband":
            self.marry(a, b)
        elif rel == "wife":
            self.marry(b, a)

    def parents(self, x):
        return [p for p in (self.father.get(x), self.mother.get(x)) if p]

    def children(self, x):
        return [c for c in self.g if x in (self.father.get(c), self.mother.get(c))]

    def sibs(self, x):
        f, m = self.father.get(x), self.mother.get(x)
        if not f or not m:
            return []
        return [c for c in self.g if c != x and self.father.get(c) == f and self.mother.get(c) == m]


def relation_label(F, x, y):
    """Return what x is to y, or None when it is outside the supported set / gender unknown."""
    g = F.g.get(x)
    if g is None:
        return None
    M = g == "M"
    pick = lambda m, f: m if M else f
    if x in F.parents(y):
        return pick("father", "mother")
    if y in F.parents(x):
        return pick("son", "daughter")
    if F.spouse.get(x) == y:
        return pick("husband", "wife")
    if x in F.sibs(y):
        return pick("brother", "sister")
    gp = [q for p in F.parents(y) for q in F.parents(p)]
    if x in gp:
        side = "paternal" if any(x in F.parents(F.father[y]) for _ in [0] if y in F.father) else "maternal"
        return f"{side} {pick('grandfather', 'grandmother')}"
    if y in [q for p in F.children(x) for q in F.children(p)]:
        return pick("grandson", "granddaughter")
    for p in F.parents(y):
        if x in F.sibs(p):
            side = "paternal" if p == F.father.get(y) else "maternal"
            return f"{side} {pick('uncle', 'aunt')}"
    if x in [c for s in F.sibs(y) for c in F.children(s)]:
        return pick("nephew", "niece")
    for p in F.parents(y):
        for s in F.sibs(p):
            if x in F.children(s):
                return "cousin"
    sp = F.spouse.get(y)
    if sp and x in F.parents(sp):
        return pick("father-in-law", "mother-in-law")
    if any(F.spouse.get(c) == x for c in F.children(y)):
        return pick("son-in-law", "daughter-in-law")
    if (sp and x in F.sibs(sp)) or any(F.spouse.get(s) == x for s in F.sibs(y)):
        return pick("brother-in-law", "sister-in-law")
    return None


ALL_LABELS = ["father", "mother", "son", "daughter", "husband", "wife", "brother", "sister", "paternal grandfather", "maternal grandfather",
              "paternal grandmother", "maternal grandmother", "grandson", "granddaughter", "paternal uncle", "maternal uncle", "paternal aunt",
              "maternal aunt", "nephew", "niece", "cousin", "father-in-law", "mother-in-law", "son-in-law", "daughter-in-law",
              "brother-in-law", "sister-in-law"]
LINK_RELS = ["father", "mother", "brother", "sister", "husband", "wife"]
BR_TOPIC = "Blood Relations"


def blood_chain(rng, n_links, names):
    for _ in range(3000):
        rels = [rng.choice(LINK_RELS) for _ in range(n_links)]
        F = Fam()
        try:
            for i, r in enumerate(rels):
                F.apply(r, names[i], names[i + 1])
        except ValueError:
            continue
        pairs = [(a, b) for a in names[:n_links + 1] for b in names[:n_links + 1] if a != b]
        rng.shuffle(pairs)
        for a, b in pairs:
            lab = relation_label(F, a, b)
            if lab and abs(names.index(a) - names.index(b)) >= 2:
                return rels, F, a, b, lab
    raise RuntimeError("blood chain")


def blood_question(rng, coded):
    names = rng.sample(list("ABCDEFGHJKLMNPQRSTUVWXYZ"), 5)
    n_links = rng.choice([3, 4])
    names = names[:n_links + 1]
    rels, F, a, b, lab = blood_chain(rng, n_links, names)
    opts, ans = pick_opts(rng, lab, ALL_LABELS, key=str)
    if coded:
        kinds = list(dict.fromkeys(rels))
        extra = [r for r in LINK_RELS if r not in kinds]
        rng.shuffle(extra)
        kinds = (kinds + extra)[:max(4, len(kinds))]
        syms = dict(zip(kinds, rng.sample(["+", "−", "×", "÷", "@", "#", "$", "%", "©"], len(kinds))))
        legend = "; ".join(f"'P {syms[r]} Q' means 'P is the {r} of Q'" for r in kinds)
        expr = names[0]
        for i, r in enumerate(rels):
            expr += f" {syms[r]} {names[i + 1]}"
        q = f"Directions: {legend}.\nIn the expression '{expr}', how is {a} related to {b}?"
        steps = "; ".join(f"{names[i]} is the {r} of {names[i + 1]}" for i, r in enumerate(rels))
    else:
        order = list(range(n_links))
        rng.shuffle(order)
        stm = " ".join(f"{names[i]} is the {rels[i]} of {names[i + 1]}." for i in order)
        q = f"{stm}\nHow is {a} related to {b}?"
        steps = "; ".join(f"{names[i]} is the {r} of {names[i + 1]}" for i, r in enumerate(rels))
    exp = f"Decoding the chain: {steps}.<br>Putting the family together, {a} is the <b>{lab}</b> of {b}."
    return Q(BR_TOPIC, q, opts, ans, exp)


# ================================================================ direction sense
VEC = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
DIRS = ["north", "east", "south", "west"]
COMPASS = {(0, 1): "North", (1, 1): "North-East", (1, 0): "East", (1, -1): "South-East", (0, -1): "South", (-1, -1): "South-West", (-1, 0): "West", (-1, 1): "North-West"}


def compass(dx, dy):
    sgn = lambda v: (v > 0) - (v < 0)
    return COMPASS[(sgn(dx), sgn(dy))]


def walk(rng, steps):
    d = rng.randrange(4)
    start_dir = DIRS[d]
    x = y = 0
    parts, turns = [], []
    dist = []
    for i in range(steps):
        k = rng.choice([3, 4, 5, 6, 8, 9, 10, 12, 15])
        if i == 0:
            parts.append(f"walks {k} m towards the {DIRS[d]}")
        else:
            t = rng.choice(["left", "right"])
            d = (d + (1 if t == "right" else -1)) % 4
            parts.append(f"turns {t} and walks {k} m")
        dx, dy = VEC[DIRS[d]]
        x, y = x + dx * k, y + dy * k
    return parts, (x, y)


def join_parts(parts):
    return ", then ".join(parts[:-1]) + (", and finally " + parts[-1] if len(parts) > 1 else parts[0])


def mn(v):
    return str(v).replace('-', '−')


def direction_question(rng, two):
    for _ in range(3000):
        if not two:
            parts, (x, y) = walk(rng, rng.choice([4, 5]))
            dist = math.hypot(x, y)
            if (x, y) == (0, 0) or dist != int(dist):
                continue
            name = rng.choice(["Rohan", "Meera", "Kabir", "Anita", "Sameer"])
            text = f"{name} starts from point P and {join_parts(parts)}, reaching point Q. How far and in which direction is Q from P?"
            right = f"{int(dist)} m, {compass(x, y)}"
            pool = [f"{int(dist)} m, {c}" for c in COMPASS.values()] + [f"{int(dist) + e} m, {compass(x, y)}" for e in (-3, 3, 5, -5, 2)]
            opts, ans = pick_opts(rng, right, pool, key=str)
            exp = f"With P as origin (east = +x, north = +y), Q is at (x, y) = ({mn(x)}, {mn(y)}). Distance = √(({mn(x)})² + ({mn(y)})²) = {int(dist)} m and the direction is {compass(x, y)}.<br><b>Answer: {right}</b>"
        else:
            p1, (x1, y1) = walk(rng, rng.choice([3, 4]))
            p2, (x2, y2) = walk(rng, rng.choice([3, 4]))
            dx, dy = x1 - x2, y1 - y2
            dist = math.hypot(dx, dy)
            if (dx, dy) == (0, 0) or dist != int(dist):
                continue
            text = (f"Two friends A and B start from the same point P at the same time. A {join_parts(p1)}. B {join_parts(p2)}. "
                    "After both have stopped, how far and in which direction is A from B?")
            right = f"{int(dist)} m, {compass(dx, dy)}"
            pool = [f"{int(dist)} m, {c}" for c in COMPASS.values()] + [f"{int(dist) + e} m, {compass(dx, dy)}" for e in (-3, 3, 5, -5, 2)]
            opts, ans = pick_opts(rng, right, pool, key=str)
            exp = (f"With P as origin: A ends at ({mn(x1)}, {mn(y1)}) and B at ({mn(x2)}, {mn(y2)}).<br>A relative to B = ({mn(x1)} − ({mn(x2)}), {mn(y1)} − ({mn(y2)})) = ({mn(dx)}, {mn(dy)}); "
                   f"distance = √(({mn(dx)})² + ({mn(dy)})²) = {int(dist)} m, direction {compass(dx, dy)}.<br><b>Answer: {right}</b>")
        return Q("Direction Sense", text, opts, ans, exp)
    raise RuntimeError("direction")


# ================================================================ coding-decoding
CODE_VOCAB = ["loan", "bank", "deposit", "cheque", "customer", "branch", "card", "interest", "account", "cash", "saving", "credit"]
SYL = [a + b + c for a in "bdfgkmprstz" for b in "aeiou" for c in "bdklmnprstvz"]


def coding_language(rng, reverse=None):
    for _ in range(4000):
        vocab = rng.sample(CODE_VOCAB, 5)
        codes = rng.sample(SYL, 5)
        truth = dict(zip(vocab, codes))
        sents = [rng.sample(vocab, 3) for _ in range(rng.choice([3, 4]))]
        if len({tuple(sorted(x)) for x in sents}) < len(sents) or set(w for x in sents for w in x) != set(vocab):
            continue
        coded = [{truth[w] for w in x} for x in sents]
        sols = [perm for perm in itertools.permutations(codes)
                if all({dict(zip(vocab, perm))[w] for w in x} == cs for x, cs in zip(sents, coded))]
        if len(sols) != 1:
            continue
        shown = []
        for cs, ws in zip(coded, sents):
            lst = sorted(cs)
            rng.shuffle(lst)
            shown.append(f"'{' '.join(lst)}' means '{' '.join(ws)}'")
        rev = rng.random() < 0.5 if reverse is None else reverse
        w = rng.choice(vocab)
        base = "In a certain code language, " + "; ".join(shown) + ".\n"
        mapping = "; ".join(f"{k} = {v}" for k, v in truth.items())
        if rev:
            q = base + f"What is the code for '{w}'?"
            opts, ans = pick_opts(rng, truth[w], codes, key=str)
        else:
            q = base + f"What does the code '{truth[w]}' stand for?"
            opts, ans = pick_opts(rng, w, vocab, key=str)
        exp = ("Compare the sentences: a word that is common to two sentences has the code that is common to both. Repeating this separates every word, giving: "
               + mapping + f".<br><b>Answer: {truth[w] if rev else w}</b>")
        return Q("Coding-Decoding", q, opts, ans, exp)
    raise RuntimeError("coding lang")


CODE_WORDS5 = ["LOANS", "BANKS", "CARDS", "VAULT", "SHARE", "BONDS", "CLERK", "CHEQUE", "LEDGER", "CREDIT", "TELLER", "SAVING", "BRANCH", "POLICY"]


def shift_for(scheme, i):
    t = scheme[0]
    if t == "const":
        return scheme[1]
    if t == "alt":
        return scheme[1] if i % 2 == 0 else scheme[2]
    if t == "inc":
        return scheme[1] + i
    return scheme[1] - i


def apply_rule(word, rule):
    rev, scheme = rule
    w = word[::-1] if rev else word
    return "".join(chr((ord(ch) - 65 + shift_for(scheme, i)) % 26 + 65) for i, ch in enumerate(w))


def rule_text(rule):
    rev, sc = rule
    t = "the word is first reversed; then " if rev else ""
    d = {"const": lambda: f"every letter moves {abs(sc[1])} step{'s' if abs(sc[1]) > 1 else ''} {'forward' if sc[1] > 0 else 'backward'}",
         "alt": lambda: f"letters at odd places move {abs(sc[1])} {'forward' if sc[1] > 0 else 'backward'} and letters at even places move {abs(sc[2])} {'forward' if sc[2] > 0 else 'backward'}",
         "inc": lambda: f"the 1st, 2nd, 3rd … letters move {sc[1]}, {sc[1] + 1}, {sc[1] + 2}, … steps forward",
         "dec": lambda: f"the 1st, 2nd, 3rd … letters move {sc[1]}, {sc[1] - 1}, {sc[1] - 2}, … steps forward"}[sc[0]]()
    return t + d


def all_rules():
    schemes = [("const", k) for k in range(-4, 5) if k] + [("alt", a, b) for a in range(-3, 4) for b in range(-3, 4) if a and b and a != b] \
        + [("inc", s) for s in range(-2, 4)] + [("dec", s) for s in range(1, 8)]
    return [(rv, sc) for rv in (False, True) for sc in schemes]


def letter_coding(rng):
    rules = all_rules()
    for _ in range(3000):
        rule = rng.choice([r for r in rules if r[1][0] != "const" or r[0]])
        ex, tgt = rng.sample(CODE_WORDS5, 2)
        code_ex = apply_rule(ex, rule)
        consistent = [r for r in rules if apply_rule(ex, r) == code_ex]
        outs = {apply_rule(tgt, r) for r in consistent}
        if len(outs) != 1:
            continue
        right = apply_rule(tgt, rule)
        pool = list({apply_rule(tgt, r) for r in rules if r != rule})
        pool = [x for x in pool if x != right]
        opts, ans = pick_opts(rng, right, pool, key=str)
        q = f"In a certain code language, '{ex}' is written as '{code_ex}'. How will '{tgt}' be written in that language?"
        exp = (f"Comparing {ex} with {code_ex}: {rule_text(rule)}.<br>Applying the same rule to {tgt} gives <b>{right}</b>.")
        return Q("Coding-Decoding", q, opts, ans, exp)
    raise RuntimeError("letter coding")


# ================================================================ input - output
IO_WORDS = ["bank", "loan", "cash", "card", "bond", "firm", "gold", "king", "lamp", "mint", "note", "plan", "rate", "safe", "tax", "unit", "vote", "zero"]


def io_simulate(kind, items):
    left, right, mid = [], [], list(items)
    steps = []
    nums = lambda: [x for x in mid if x.isdigit()]
    words = lambda: [x for x in mid if not x.isdigit()]
    ds = lambda x: sum(int(c) for c in x)
    i = 0
    while len(mid) > 1:
        i += 1
        odd = i % 2 == 1
        if kind == "A":
            pick = max(mid, key=int) if odd else min(mid, key=int)
        elif kind == "B":
            pick = min(mid) if odd else max(mid)
        elif kind == "C":
            cand = nums() if odd else words()
            if not cand:
                break
            pick = max(cand, key=int) if odd else min(cand)
        else:
            pick = max(mid, key=lambda x: (ds(x), int(x))) if odd else min(mid, key=lambda x: (ds(x), int(x)))
        mid.remove(pick)
        (left.append(pick) if odd else right.insert(0, pick))
        steps.append(left + mid + right)
    while len(steps) > 1 and steps[-1] == steps[-2]:
        steps.pop()
    return steps


def io_rule_text(kind):
    return {"A": "In odd steps the largest remaining number moves to the left end of the unfixed part; in even steps the smallest remaining number moves to the right end.",
            "B": "In odd steps the alphabetically first remaining word moves to the left end of the unfixed part; in even steps the alphabetically last remaining word moves to the right end.",
            "C": "In odd steps the largest remaining number moves to the left end; in even steps the alphabetically first remaining word moves to the right end.",
            "D": "In odd steps the number with the highest digit-sum (larger number if tied) moves to the left end; in even steps the number with the lowest digit-sum (smaller number if tied) moves to the right end."}[kind]


def io_input(rng, kind):
    if kind == "B":
        return rng.sample(IO_WORDS, 6)
    if kind == "C":
        return [str(x) for x in rng.sample(range(11, 99), 3)] + rng.sample(IO_WORDS, 3)
    return [str(x) for x in rng.sample(range(11, 99), 6)]


def input_output(rng):
    ORDW = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]
    for _ in range(500):
        kind = rng.choice("ABCD")
        ex = io_input(rng, kind)
        if kind == "C":
            rng.shuffle(ex)
        new = io_input(rng, kind)
        if kind == "C":
            rng.shuffle(new)
        st_ex, st_new = io_simulate(kind, ex), io_simulate(kind, new)
        if len(st_ex) < 4 or len(st_new) < 4:
            continue
        chain_ex = [list(ex)] + st_ex[:3]
        if any(chain_ex[i] == chain_ex[i + 1] for i in range(3)):
            continue                                   # every shown step must visibly change the arrangement
        if any(st_new[i] == st_new[i + 1] for i in range(len(st_new) - 1)) or st_new[0] == list(new):
            continue
        shown = [f"Input: {' '.join(ex)}"] + [f"Step {r}: {' '.join(st_ex[i])}" for i, r in enumerate(["I", "II", "III"])]
        head = ("Study the following input and its rearrangement steps (the pattern continues in the same way until the arrangement is complete), "
                "and answer the question given below.\n" + "\n".join(shown) + "\n")
        qt = rng.choice(["step", "pos", "count", "rel"])
        total = len(st_new)
        if qt == "step":
            k = rng.randint(2, min(4, total))
            right = " ".join(st_new[k - 1])
            wrong = []
            for _ in range(60):
                arr = list(st_new[k - 1])
                i, j = rng.sample(range(len(arr)), 2)
                arr[i], arr[j] = arr[j], arr[i]
                a = " ".join(arr)
                if a != right and a not in wrong and a not in [" ".join(x) for x in st_new]:
                    wrong.append(a)
                if len(wrong) == 4:
                    break
            opts, ans = pick_opts(rng, right, wrong, key=None)
            text = head + f"Input: {' '.join(new)}\nWhich of the following will be Step {['I','II','III','IV','V','VI','VII'][k - 1]} for this input?"
        elif qt == "pos":
            k = rng.randint(2, min(4, total))
            x = rng.choice(new)
            side = rng.choice(["left", "right"])
            arr = st_new[k - 1]
            idx = arr.index(x) if side == "left" else len(arr) - 1 - arr.index(x)
            words = [ORDW[i].capitalize() for i in range(len(arr))]
            opts, ans = pick_opts(rng, words[idx], words, key=words.index)
            text = head + f"Input: {' '.join(new)}\nWhat is the position of '{x}' from the {side} end in Step {['I','II','III','IV','V','VI','VII'][k - 1]}?"
            right = words[idx]
        elif qt == "count":
            right = str(total)
            pool = [str(total + d) for d in (-2, -1, 1, 2, 3) if total + d > 0]
            opts, ans = pick_opts(rng, right, pool, key=int)
            text = head + f"Input: {' '.join(new)}\nHow many steps are required to complete the arrangement for this input?"
        else:
            k = rng.randint(2, min(4, total))
            arr = st_new[k - 1]
            off = rng.randint(2, 3)
            cands = [i for i in range(len(arr)) if i + off < len(arr)]
            if not cands:
                continue
            i = rng.choice(cands)
            right = arr[i + off]
            opts, ans = pick_opts(rng, right, [x for x in new if x != right], key=None)
            text = head + f"Input: {' '.join(new)}\nWhich element is {ORDW[off - 1]} to the right of '{arr[i]}' in Step {['I','II','III','IV','V','VI','VII'][k - 1]}?"
        lines = [f"Input: {' '.join(new)}"] + [f"Step {['I','II','III','IV','V','VI','VII','VIII'][i]}: {' '.join(a)}" for i, a in enumerate(st_new)]
        exp = io_rule_text(kind) + "<br>Applying it to the new input:<br>" + "<br>".join(lines) + f"<br><b>Answer: {right}</b>"
        return Q("Input-Output", text, opts, ans, exp)
    raise RuntimeError("io")


# ================================================================ alphanumeric arrangement
CLS = {"digit": "123456789", "consonant": "BCDFGHJKLMNPQRSTVWXYZ", "vowel": "AEU", "symbol": "@#$%&*"}
PLUR = {"digit": "digits", "consonant": "consonants", "vowel": "vowels", "symbol": "symbols"}


def cls_of(ch):
    for k, v in CLS.items():
        if ch in v:
            return k


def alnum_sequence(rng):
    d = rng.sample(CLS["digit"], 6)
    c = rng.sample(CLS["consonant"], 5)
    v = rng.sample(CLS["vowel"], 3)
    sy = rng.sample(CLS["symbol"], 4)
    seq = d + c + v + sy
    rng.shuffle(seq)
    return seq


def alnum_question(rng):
    ORDW = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
    for _ in range(3000):
        seq = alnum_sequence(rng)
        n = len(seq)
        kind = rng.choice(["count", "count", "pos", "drop"])
        arrangement = " ".join(seq)
        base = "Study the following arrangement and answer the question given below.\n" + arrangement + "\n"
        if kind == "count":
            X = rng.choice(["digit", "consonant", "vowel"])
            cb = rng.choice(["symbol", "digit", "consonant", "vowel"])
            ca = rng.choice(["symbol", "digit", "consonant", "vowel"])
            neg_b = rng.random() < 0.4
            if seq[0] in sum((list(CLS[X]) for _ in [0]), []) or seq[-1] in CLS[X]:
                continue
            cnt = 0
            for i in range(1, n - 1):
                if cls_of(seq[i]) != X:
                    continue
                b_ok = (cls_of(seq[i - 1]) == cb) != neg_b
                a_ok = cls_of(seq[i + 1]) == ca
                cnt += b_ok and a_ok
            if cnt > 4 or (cnt == 0 and rng.random() < 0.85):
                continue
            if neg_b:
                cond = f"immediately followed by a {ca} but not immediately preceded by a {cb}"
            else:
                cond = f"immediately preceded by a {cb} and immediately followed by a {ca}"
            q = base + f"How many {PLUR[X]} are there in the above arrangement, each of which is {cond}?"
            exp = (f"Check every {X} that has a neighbour on both sides. The ones that are {cond}: "
                   + (", ".join(f"{seq[i - 1]} {seq[i]} {seq[i + 1]}" for i in range(1, n - 1)
                                if cls_of(seq[i]) == X and ((cls_of(seq[i - 1]) == cb) != neg_b) and cls_of(seq[i + 1]) == ca) or "none")
                   + f".<br><b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")
            return Q("Alphanumeric Series", q, COUNT_OPTS, count_answer(cnt), exp)
        if kind == "pos":
            a, off = rng.randint(2, 9), rng.randint(2, 5)
            if a - 1 + off >= n:
                continue
            right = seq[a - 1 + off]
            opts, ans = pick_opts(rng, right, list(dict.fromkeys(seq)), key=None)
            q = base + f"Which element is {ORDW[off - 1]} to the right of the {ORDW[a - 1]} element from the left end?"
            exp = f"The {ORDW[a - 1]} element from the left is {seq[a - 1]}. Moving {off} places to the right gives <b>{right}</b>."
            return Q("Alphanumeric Series", q, opts, ans, exp)
        drop = rng.choice(["symbol", "digit", "vowel"])
        rest = [x for x in seq if cls_of(x) != drop]
        k = rng.randint(4, 8)
        if k > len(rest):
            continue
        right = rest[-k]
        opts, ans = pick_opts(rng, right, list(dict.fromkeys(rest)), key=None)
        q = base + f"If all the {PLUR[drop]} are removed from the arrangement, which element will be {ORDW[k - 1]} from the right end?"
        exp = f"After removing the {PLUR[drop]} the arrangement is: {' '.join(rest)}. The {ORDW[k - 1]} element from the right is <b>{right}</b>."
        return Q("Alphanumeric Series", q, opts, ans, exp)
    raise RuntimeError("alnum")


# ================================================================ data sufficiency (reasoning)
from build_mains_quant import DS_OPTS  # noqa: E402


def ds_reasoning(rng, want):
    people = list("ABCDE")
    perms = list(itertools.permutations(people))                       # tallest -> shortest
    for _ in range(20000):
        hidden = list(people)
        rng.shuffle(hidden)
        rank = {p: i for i, p in enumerate(hidden)}                     # 0 = tallest

        def make():
            k = rng.choice(["gt", "lt", "between", "count", "nottop", "gap", "below", "all"])
            a, b, c = rng.sample(people, 3)
            W = {1: "Only one person is", 2: "Exactly two persons are", 3: "Exactly three persons are", 4: "Exactly four persons are"}
            if k == "gt" and rank[a] < rank[b]:
                return f"{a} is taller than {b}", lambda r: r[a] < r[b]
            if k == "lt" and rank[a] > rank[b]:
                return f"{a} is shorter than {b}", lambda r: r[a] > r[b]
            if k == "between" and rank[c] < rank[a] < rank[b]:
                return f"{a} is taller than {b} but shorter than {c}", lambda r: r[c] < r[a] < r[b]
            if k == "count" and rank[a] >= 1:
                t = rank[a]
                return f"{W[t]} taller than {a}", lambda r: r[a] == t
            if k == "below" and rank[a] <= 3:
                t = 4 - rank[a]
                return f"{W[t]} shorter than {a}", lambda r: r[a] == 4 - t
            if k == "all" and rank[a] == 0:
                return f"{a} is taller than each of the other four persons", lambda r: r[a] == 0
            if k == "all" and rank[a] == 4:
                return f"{a} is shorter than each of the other four persons", lambda r: r[a] == 4
            if k == "nottop" and rank[a] != 0:
                return f"{a} is not the tallest", lambda r: r[a] != 0
            if k == "gap" and abs(rank[a] - rank[b]) == 2:
                return f"Exactly one person is between {a} and {b} in height", lambda r: abs(r[a] - r[b]) == 2
            return None
        s1, s2 = make(), make()
        if not s1 or not s2 or s1[0] == s2[0]:
            continue
        tq = rng.choice([("Who is the tallest among A, B, C, D and E?", 0), ("Who is the shortest among A, B, C, D and E?", 4), ("Who is the third tallest among A, B, C, D and E?", 2)])
        qtext, pos = tq

        def answers(preds):
            out = set()
            for pm in perms:
                r = {p: i for i, p in enumerate(pm)}
                if all(f(r) for f in preds):
                    out.add(pm[pos])
            return out
        a1, a2, a12 = answers([s1[1]]), answers([s2[1]]), answers([s1[1], s2[1]])
        suf1, suf2, suf12 = len(a1) == 1, len(a2) == 1, len(a12) == 1
        code = 3 if suf1 and suf2 else 0 if suf1 else 1 if suf2 else 2 if suf12 else 4
        if code != want:
            continue
        show = lambda s: ", ".join(sorted(s)) if len(s) > 1 else next(iter(s))
        exp = (f"Statement I alone: possible answers → {show(a1)}{' (sufficient)' if suf1 else ' (not sufficient)'}.<br>"
               f"Statement II alone: possible answers → {show(a2)}{' (sufficient)' if suf2 else ' (not sufficient)'}.<br>"
               f"Both together: possible answers → {show(a12)}{' (sufficient)' if suf12 else ' (not sufficient)'}.<br><b>Answer: {DS_OPTS[code]}</b>")
        q = ("Directions: Each question is followed by two statements. Decide whether the data given is sufficient to answer the question.\n"
             f"{qtext}\nStatement I: {s1[0]}.\nStatement II: {s2[0]}.")
        return Q("Data Sufficiency", q, DS_OPTS, code, exp)
    raise RuntimeError("ds reasoning")


# ================================================================ computer aptitude
from build_mains_quant import make_options as _quant_options, fmt  # noqa: E402

SUB = {2: "₂", 8: "₈", 10: "₁₀", 16: "₁₆"}
CT = "Computer Aptitude"


def to_base(n, b, width=0):
    digs = "0123456789ABCDEF"
    s = ""
    n = int(n)
    while n:
        s = digs[n % b] + s
        n //= b
    return (s or "0").rjust(width, "0")


def base_options(rng, value, base, width=0):
    right = to_base(value, base, width)
    cands, seen = [], {right}
    for d in rng.sample([1, 2, 3, 4, 5, 8, 16, 32, 9, 12], 10):
        for sign in (1, -1):
            v = value + sign * d
            if v > 0:
                s = to_base(v, base, width)
                if s not in seen:
                    seen.add(s)
                    cands.append((v, s))
    rng.shuffle(cands)
    items = sorted([(value, right)] + cands[:4])
    opts = [s for _, s in items]
    return opts, opts.index(right)


def comp_numsys(rng):
    kind = rng.choice(["b2d", "d2b", "b2h", "h2d", "o2b", "d2h"])
    if kind == "b2d":
        n = rng.randint(70, 250)
        b = to_base(n, 2, 8)
        opts, ans = _quant_options(rng, n, [n + 8, n - 16], none_ok=False)
        terms = " + ".join(f"{2 ** (7 - i)}" for i, ch in enumerate(b) if ch == "1")
        return Q(CT, f"What is the decimal value of the binary number ({b}){SUB[2]}?", opts, ans, f"Add the place values of the 1-bits: {terms} = <b>{n}</b>.")
    if kind == "d2b":
        n = rng.randint(70, 250)
        opts, ans = base_options(rng, n, 2, 8)
        steps = []
        m = n
        for _ in range(8):
            steps.append(f"{m} ÷ 2 → remainder {m % 2}")
            m //= 2
            if m == 0:
                break
        return Q(CT, f"Convert the decimal number ({n}){SUB[10]} into binary.", opts, ans, "Divide repeatedly by 2 and read the remainders upward: " + "; ".join(steps) + f".<br><b>Answer: {to_base(n, 2, 8)}</b>")
    if kind == "b2h":
        n = rng.randint(0x20, 0xFFF)
        width = 4 * len(to_base(n, 16))
        b = to_base(n, 2, width)
        opts, ans = base_options(rng, n, 16)
        groups = " ".join(b[i:i + 4] for i in range(0, len(b), 4))
        return Q(CT, f"What is the hexadecimal equivalent of the binary number ({b}){SUB[2]}?", opts, ans,
                 f"Group the bits in fours from the right: {groups} → " + " ".join(to_base(int(b[i:i + 4], 2), 16) for i in range(0, len(b), 4)) + f".<br><b>Answer: {to_base(n, 16)}</b>")
    if kind == "h2d":
        n = rng.randint(0x30, 0xFFF)
        h = to_base(n, 16)
        opts, ans = _quant_options(rng, n, [n + 16, n - 15], none_ok=False)
        parts = " + ".join(f"{int(ch, 16)}×{16 ** (len(h) - 1 - i)}" for i, ch in enumerate(h))
        return Q(CT, f"What is the decimal value of the hexadecimal number ({h}){SUB[16]}?", opts, ans, f"{parts} = <b>{n}</b>.")
    if kind == "o2b":
        n = rng.randint(0o100, 0o777)
        o = to_base(n, 8)
        opts, ans = base_options(rng, n, 2, 9)
        return Q(CT, f"Convert the octal number ({o}){SUB[8]} into binary.", opts, ans,
                 "Write each octal digit as 3 bits: " + " ".join(f"{d}→{int(d):03b}" for d in o) + f".<br><b>Answer: {to_base(n, 2, 9)}</b>")
    n = rng.randint(0x40, 0xFFF)
    opts, ans = base_options(rng, n, 16)
    return Q(CT, f"Convert the decimal number ({n}){SUB[10]} into hexadecimal.", opts, ans, f"Divide by 16 repeatedly and read the remainders upward → <b>{to_base(n, 16)}</b>.")


def comp_storage(rng):
    kind = rng.choice(["parts", "bytes", "image"])
    if kind == "parts":
        z = rng.choice([64, 128, 256, 512])
        parts = rng.randint(12, 90)
        total = parts * z
        mb, kb = divmod(total, 1024)
        size = (f"{mb} MB " if mb else "") + (f"{kb} KB" if kb else "")
        opts, ans = _quant_options(rng, parts, [parts * 2, parts // 2 + 1], none_ok=False)
        return Q(CT, f"A file of size {size.strip()} is split into equal parts of {z} KB each. How many parts are formed? (1 MB = 1024 KB)", opts, ans,
                 f"Total size = {mb} × 1024 + {kb} = {total} KB.<br>Parts = {total} ÷ {z} = <b>{parts}</b>.")
    if kind == "bytes":
        a, b = rng.randint(2, 40), rng.randint(16, 900)
        v = a * 1024 + b
        opts, ans = _quant_options(rng, v, [a * 1000 + b, a * 1024 - b], none_ok=False)
        return Q(CT, f"How many bytes are there in {a} KB {b} bytes? (1 KB = 1024 bytes)", opts, ans, f"{a} × 1024 + {b} = <b>{v}</b> bytes.")
    w, h = rng.choice([(1024, 768), (800, 640), (640, 512), (1280, 1024), (1024, 512), (2048, 1024)])
    bpp = rng.choice([8, 16, 24, 32])
    kb = Fr(w * h * bpp, 8 * 1024)
    if kb.denominator != 1:
        return comp_storage(rng)
    opts, ans = _quant_options(rng, kb, [kb * 8, kb / 2 if (kb / 2).denominator == 1 else kb + 100], none_ok=False)
    return Q(CT, f"An uncompressed image has {w} × {h} pixels and each pixel needs {bpp} bits. What is its size in KB? (1 KB = 1024 bytes)", opts, ans,
             f"Bits = {w} × {h} × {bpp}; bytes = that ÷ 8 = {w * h * bpp // 8}; KB = ÷ 1024 = <b>{int(kb)}</b>.")


def comp_excel(rng):
    for _ in range(500):
        A = [rng.randint(3, 30) for _ in range(5)]
        B = [rng.randint(2, 25) for _ in range(5)]
        kind = rng.randint(0, 4)
        if kind == 0:
            f = "=SUM(A1:A5)-MAX(B1:B5)+MIN(A1:A3)"
            v = sum(A) - max(B) + min(A[:3])
            how = f"SUM(A1:A5) = {sum(A)}; MAX(B1:B5) = {max(B)}; MIN(A1:A3) = {min(A[:3])} → {sum(A)} − {max(B)} + {min(A[:3])}"
        elif kind == 1:
            t = rng.randint(8, 18)
            f = f"=IF(AVERAGE(A1:A5)>{t},MAX(A1:A5)-MIN(B1:B5),SUM(B1:B2))"
            av = Fr(sum(A), 5)
            if av > t:
                v = max(A) - min(B)
                how = f"AVERAGE(A1:A5) = {fmt(av)} which is > {t}, so the first branch: MAX(A1:A5) − MIN(B1:B5) = {max(A)} − {min(B)}"
            else:
                v = B[0] + B[1]
                how = f"AVERAGE(A1:A5) = {fmt(av)} which is not > {t}, so the second branch: SUM(B1:B2) = {B[0]} + {B[1]}"
        elif kind == 2:
            t = rng.randint(8, 18)
            f = f'=COUNTIF(A1:A5,">{t}")*MAX(B1:B3)'
            c = sum(1 for x in A if x > t)
            v = c * max(B[:3])
            how = f"COUNTIF counts values above {t} in A1:A5 = {c}; MAX(B1:B3) = {max(B[:3])} → {c} × {max(B[:3])}"
        elif kind == 3:
            t = rng.randint(8, 18)
            f = f'=SUMIF(A1:A5,">{t}",B1:B5)'
            v = sum(b for a, b in zip(A, B) if a > t)
            how = f"Only rows where A > {t} are added from column B: " + (" + ".join(str(b) for a, b in zip(A, B) if a > t) or "none")
        else:
            f = "=ROUND(AVERAGE(A1:A5),0)+COUNT(A1:B5)"
            av = Fr(sum(A), 5)
            r = int(av + Fr(1, 2)) if (av - int(av)) >= Fr(1, 2) else int(av)
            v = r + 10
            how = f"AVERAGE(A1:A5) = {fmt(av)}, rounded to {r}; COUNT(A1:B5) counts the 10 numeric cells → {r} + 10"
        if v <= 0 or (kind in (2, 3) and v == 0):
            continue
        grid = "A1:A5 = " + ", ".join(map(str, A)) + "\nB1:B5 = " + ", ".join(map(str, B))
        opts, ans = _quant_options(rng, v, [v + 5, v - 3, v + 10], none_ok=False)
        q = f"In an Excel sheet the cells contain the following values (row 1 to row 5):\n{grid}\nWhat will be the result of the formula {f} ?"
        return Q(CT, q, opts, ans, f"{how} = <b>{v}</b>.")
    raise RuntimeError("excel")


def comp_logic(rng):
    gates = {"AND": lambda a, b: a & b, "OR": lambda a, b: a | b, "NAND": lambda a, b: 1 - (a & b), "NOR": lambda a, b: 1 - (a | b), "XOR": lambda a, b: a ^ b, "XNOR": lambda a, b: 1 - (a ^ b)}
    for _ in range(300):
        g1, g2 = rng.sample(list(gates), 2)
        third = rng.choice(["C", "NOT C"])
        f = f"({g1.join(['A ', ' B'])}) {g2} {third}"
        cnt, rows = 0, []
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    cc = c if third == "C" else 1 - c
                    out = gates[g2](gates[g1](a, b), cc)
                    cnt += out
                    rows.append(out)
        if cnt in (0, 8):
            continue
        opts, ans = pick_opts(rng, str(cnt), [str(x) for x in range(0, 9)], key=int)
        exp = f"Evaluate the output for all 8 combinations of (A, B, C) in the order 000, 001, …, 111: {' '.join(map(str, rows))}.<br>The output is 1 in <b>{cnt}</b> combinations."
        return Q(CT, f"For how many of the 8 possible input combinations of A, B and C is the output of the logic expression {f} equal to 1?", opts, ans, exp)
    raise RuntimeError("logic")


def comp_binary_arith(rng):
    op = rng.choice(["+", "−", "×"])
    a, b = rng.randint(21, 60), rng.randint(5, 20)
    if op == "−" and a <= b:
        a, b = b + 10, a - 10 if a > 10 else 5
    v = {"+": a + b, "−": a - b, "×": a * b}[op]
    opts, ans = base_options(rng, v, 2)
    return Q(CT, f"What is the result of ({to_base(a, 2)}){SUB[2]} {op} ({to_base(b, 2)}){SUB[2]} in binary?", opts, ans,
             f"In decimal: {a} {op} {b} = {v}; writing {v} in binary gives <b>{to_base(v, 2)}</b>.")


def comp_ip(rng):
    if rng.random() < 0.5:
        first = rng.choice([rng.randint(1, 126), rng.randint(128, 191), rng.randint(192, 223), rng.randint(224, 239)])
        cls = "Class A" if first <= 126 else "Class B" if first <= 191 else "Class C" if first <= 223 else "Class D"
        ip = f"{first}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
        opts, ans = pick_opts(rng, cls, ["Class A", "Class B", "Class C", "Class D", "Class E"], key=str)
        return Q(CT, f"The IP address {ip} belongs to which address class?", opts, ans,
                 "Class A starts with 1–126, B with 128–191, C with 192–223, D (multicast) with 224–239 and E (reserved) with 240–255. "
                 f"The first octet here is {first}, so it is <b>{cls}</b>.")
    def ok(s):
        p = s.split(".")
        return len(p) == 4 and all(x.isdigit() and 0 <= int(x) <= 255 for x in p)
    good = ".".join(str(rng.randint(10, 250)) for _ in range(4))
    bad = [f"{rng.randint(256, 400)}.{rng.randint(1, 250)}.{rng.randint(1, 250)}.{rng.randint(1, 250)}",
           ".".join(str(rng.randint(1, 250)) for _ in range(3)),
           ".".join(str(rng.randint(1, 250)) for _ in range(5)),
           f"{rng.randint(1, 250)}.{rng.randint(1, 250)}.{rng.randint(300, 999)}.{rng.randint(1, 250)}",
           f"{rng.randint(1, 250)}.{rng.randint(1, 250)}.A{rng.randint(1, 9)}.{rng.randint(1, 250)}"]
    rng.shuffle(bad)
    items = [good] + bad[:4]
    assert sum(ok(x) for x in items) == 1
    rng.shuffle(items)
    why = "; ".join(f"{x}: " + ("valid" if ok(x) else "invalid") for x in items)
    return Q(CT, "Which of the following is a valid IPv4 address?", items, items.index(good),
             f"An IPv4 address has exactly four decimal fields, each from 0 to 255. Checking: {why}.<br><b>Answer: {good}</b>")


def comp_ascii(rng):
    c1, c2 = rng.sample("ABCDEFGHJKLMNPQRSTUVWXYZ", 2)
    v = ord(c2)
    opts, ans = _quant_options(rng, v, [v + 32, v - 1, v + 1], none_ok=False)
    return Q(CT, f"In ASCII the capital letter '{c1}' has the decimal code {ord(c1)}. What is the decimal ASCII code of the capital letter '{c2}'?", opts, ans,
             f"Capital letters have consecutive codes. '{c2}' is {ord(c2) - ord(c1):+d} places from '{c1}', so the code is {ord(c1)} {'+' if ord(c2) > ord(c1) else '−'} {abs(ord(c2) - ord(c1))} = <b>{v}</b>.")


COMP_GEN = [comp_numsys, comp_numsys, comp_storage, comp_excel, comp_excel, comp_logic, comp_binary_arith, comp_ip, comp_ascii]


# original concept questions (written for ScoreFree): (question, correct, [4 wrong], explanation)
CONCEPTS = [
    ("Which of the following memories loses its contents when the power supply is switched off?", "RAM", ["ROM", "PROM", "EEPROM", "Hard disk"], "RAM is volatile: it keeps data only while powered. ROM, PROM, EEPROM and disks are non-volatile."),
    ("Which CPU register holds the address of the next instruction to be fetched?", "Program Counter", ["Accumulator", "Instruction Register", "Memory Data Register", "Status Register"], "The Program Counter points to the next instruction; the Instruction Register holds the instruction currently being decoded."),
    ("Which unit of the CPU performs arithmetic and logical operations?", "Arithmetic Logic Unit", ["Control Unit", "Cache Controller", "Bus Interface Unit", "Memory Management Unit"], "The ALU does addition, subtraction, comparisons and logical operations; the control unit only directs the flow."),
    ("Arrange in decreasing order of access speed: main memory, registers, hard disk, cache.", "Registers, cache, main memory, hard disk", ["Cache, registers, main memory, hard disk", "Registers, main memory, cache, hard disk", "Cache, main memory, registers, hard disk", "Registers, cache, hard disk, main memory"], "Speed falls as we move down the memory hierarchy: registers → cache → main memory → secondary storage."),
    ("Cache memory is placed between which two components?", "CPU and main memory", ["Main memory and hard disk", "Hard disk and optical disk", "CPU and registers", "Keyboard and CPU"], "Cache stores frequently used data close to the CPU so it need not wait for slower main memory."),
    ("Which of the following is a non-impact printer?", "Laser printer", ["Dot-matrix printer", "Daisy-wheel printer", "Drum printer", "Chain printer"], "Laser (and inkjet) printers form images without striking the paper; the others are impact printers."),
    ("The print quality of a printer is usually measured in:", "dpi", ["rpm", "MIPS", "baud", "FLOPS"], "dpi (dots per inch) tells how many dots are printed per inch."),
    ("The program that starts the computer and loads the operating system is stored in:", "ROM / firmware", ["RAM", "Cache", "Printer buffer", "Registers"], "The bootstrap loader lives in non-volatile firmware (ROM/BIOS-UEFI) so it is available at power-on."),
    ("Which storage device has no moving mechanical parts?", "Solid State Drive", ["Hard Disk Drive", "Magnetic tape drive", "Optical disc drive", "Floppy drive"], "An SSD stores data in flash memory chips, so there are no spinning platters or heads."),
    ("Which bus carries the memory location (address) that the CPU wants to access?", "Address bus", ["Data bus", "Control bus", "Power bus", "Expansion bus"], "The address bus is one-way from CPU to memory; the data bus carries the actual data."),
    ("A compiler differs from an interpreter because a compiler:", "translates the whole program before execution", ["executes the program line by line", "converts assembly to machine code only", "can run only on one operating system", "never reports errors"], "A compiler translates the complete source in one go and gives a reusable object file; an interpreter translates and runs line by line."),
    ("An assembler converts:", "assembly language into machine language", ["high-level language into assembly language", "machine language into assembly language", "source code into bytecode only", "binary code into a database"], "The assembler maps mnemonic instructions to machine code."),
    ("The core part of an operating system that manages memory, processes and devices is called the:", "Kernel", ["Shell", "Compiler", "Driver", "Registry"], "The kernel is the central, privileged component; the shell is only the user interface to it."),
    ("A deadlock is a situation in which:", "each process in a set waits for a resource held by another process in the set", ["a process uses too much CPU time", "memory pages are swapped too frequently", "a process finishes without releasing memory", "two programs have the same name"], "Circular waiting among processes means none can proceed."),
    ("Which CPU scheduling algorithm is non-preemptive by nature?", "First Come First Served", ["Round Robin", "Shortest Remaining Time First", "Preemptive priority scheduling", "Multilevel feedback queue"], "FCFS lets a process run until it finishes or blocks; Round Robin and SRTF can take the CPU away."),
    ("Virtual memory allows a system to:", "use part of the disk as an extension of RAM", ["increase the clock speed of the CPU", "store data permanently inside RAM", "avoid using secondary storage", "run only one program at a time"], "Pages not currently needed are kept on disk, letting programs be larger than physical RAM."),
    ("Thrashing in an operating system refers to:", "excessive paging that degrades performance", ["a virus that deletes files", "a hardware failure of the disk", "too many users logging in", "a compiler error"], "When processes do not have enough frames, the system spends most time swapping pages instead of executing."),
    ("Which of the following is NOT an operating system?", "Python", ["Linux", "Windows", "Android", "macOS"], "Python is a programming language; the others are operating systems."),
    ("The first step performed by a computer at start-up, before the operating system loads, is:", "Power-On Self Test", ["Loading the kernel into RAM", "Opening the desktop", "Connecting to the internet", "Running antivirus"], "POST checks essential hardware, after which the bootloader loads the OS."),
    ("Which protocol translates a domain name into an IP address?", "DNS", ["DHCP", "SMTP", "ARP", "FTP"], "The Domain Name System maps names like example.com to IP addresses."),
    ("Which protocol automatically assigns IP addresses to devices on a network?", "DHCP", ["DNS", "HTTP", "SNMP", "Telnet"], "DHCP leases IP configuration to hosts automatically."),
    ("Routing of packets between networks takes place at which layer of the OSI model?", "Network layer", ["Data link layer", "Transport layer", "Session layer", "Physical layer"], "The network layer (IP) handles logical addressing and routing."),
    ("The default port number of HTTPS is:", "443", ["80", "21", "25", "110"], "HTTP uses 80, FTP 21, SMTP 25 and POP3 110; HTTPS uses 443."),
    ("Which transport-layer protocol is connectionless?", "UDP", ["TCP", "SMTP", "FTP", "HTTPS"], "UDP sends datagrams without establishing a connection or guaranteeing delivery."),
    ("Which device connects different networks and forwards packets using IP addresses?", "Router", ["Hub", "Repeater", "Modem", "Network cable"], "A router uses IP addresses to forward packets between networks."),
    ("The length of a MAC address is:", "48 bits", ["32 bits", "64 bits", "128 bits", "16 bits"], "A MAC address has 48 bits (6 bytes); IPv4 has 32 bits and IPv6 128 bits."),
    ("The length of an IPv6 address is:", "128 bits", ["32 bits", "48 bits", "64 bits", "256 bits"], "IPv6 addresses are 128 bits long."),
    ("In which network topology are all nodes connected to a central hub or switch?", "Star", ["Bus", "Ring", "Mesh", "Point-to-point"], "Each device in a star topology has its own link to the central device."),
    ("An HTTP status code 404 means that:", "the requested page was not found", ["the server is overloaded", "access is forbidden", "the request was successful", "the page has moved permanently"], "404 = Not Found; 200 = OK; 403 = Forbidden; 301 = Moved Permanently."),
    ("Which protocol is used for SENDING e-mail from a client to a mail server?", "SMTP", ["POP3", "IMAP", "FTP", "SNMP"], "SMTP sends mail; POP3 and IMAP retrieve it."),
    ("A network limited to a single building or campus is called a:", "LAN", ["WAN", "MAN", "PAN", "VPN"], "LAN = Local Area Network."),
    ("Phishing is best described as:", "tricking people through fake e-mails or sites to reveal confidential data", ["flooding a server with traffic", "encrypting files for ransom", "guessing passwords by trying every combination", "installing a hardware keylogger"], "Phishing uses deceptive messages that look genuine to steal credentials or money."),
    ("Vishing is a fraud carried out through:", "voice calls", ["e-mails", "SMS", "USB drives", "social media posts"], "Vishing (voice phishing) uses phone calls to extract sensitive information."),
    ("Ransomware is a type of malware that:", "encrypts the victim's files and demands payment", ["only displays advertisements", "records keystrokes silently", "spreads only through floppy disks", "speeds up the computer"], "It locks data until a ransom is paid."),
    ("The main function of a firewall is to:", "filter incoming and outgoing network traffic by rules", ["compress files", "repair corrupted disks", "increase internet speed", "store backups"], "A firewall allows or blocks traffic according to security rules."),
    ("Two-factor authentication requires:", "two different kinds of proof such as a password and an OTP", ["two passwords of the same kind", "two usernames", "the same OTP twice", "two security questions only"], "Factors are something you know, have or are; 2FA combines two different ones."),
    ("Which of the following is a one-way function used to verify data integrity?", "Hashing", ["Symmetric encryption", "Asymmetric encryption", "Compression", "Encoding"], "A hash cannot be reversed to obtain the original data; encryption can be decrypted."),
    ("A Trojan horse is malware that:", "appears to be a useful program but carries harmful code", ["replicates itself without any host file", "only affects printers", "is always hardware", "cannot harm data"], "It disguises itself as legitimate software; unlike worms it does not self-replicate."),
    ("In public-key cryptography, a message encrypted with the receiver's public key can be decrypted only with:", "the receiver's private key", ["the sender's private key", "the sender's public key", "the receiver's public key", "any public key"], "Only the receiver holds the matching private key."),
    ("A digital signature primarily provides:", "authenticity and integrity of a message", ["faster transmission", "data compression", "protection against power failure", "anonymity of the sender"], "The signature, made with the sender's private key, proves who sent it and that it was not altered."),
    ("Which key combination is used to undo the last action in most Office applications?", "Ctrl + Z", ["Ctrl + Y", "Ctrl + X", "Ctrl + U", "Ctrl + B"], "Ctrl+Z undoes; Ctrl+Y redoes."),
    ("Which Excel function counts the cells in a range that contain numbers?", "COUNT", ["COUNTA", "SUM", "LEN", "TOTAL"], "COUNT ignores text and blank cells; COUNTA counts all non-blank cells."),
    ("In Excel, which shortcut moves the cell pointer to cell A1?", "Ctrl + Home", ["Ctrl + End", "Ctrl + Page Up", "Alt + Home", "Shift + Home"], "Ctrl+Home jumps to A1; Ctrl+End goes to the last used cell."),
    ("In Excel, the reference $B$3 is called a(n):", "absolute reference", ["relative reference", "mixed reference", "3-D reference", "external link"], "Both column and row are fixed with $, so it does not change when copied."),
    ("In MS Word, which shortcut centres the selected paragraph?", "Ctrl + E", ["Ctrl + L", "Ctrl + R", "Ctrl + J", "Ctrl + M"], "Ctrl+E centre, L left, R right, J justify."),
    ("In PowerPoint, which key starts the slide show from the first slide?", "F5", ["F7", "Shift + F5", "F12", "Ctrl + F5"], "F5 starts from the beginning; Shift+F5 starts from the current slide."),
    ("In Excel, VLOOKUP searches for the lookup value in:", "the first column of the table range", ["the last column of the table range", "any row of the sheet", "the header row only", "a separate workbook only"], "VLOOKUP looks down the first column of the table array and returns a value from a column to its right."),
    ("In Excel, which key combination inserts a line break inside a single cell?", "Alt + Enter", ["Ctrl + Enter", "Shift + Enter", "Tab", "Ctrl + Tab"], "Alt+Enter starts a new line within the cell."),
    ("The purpose of Mail Merge in MS Word is to:", "create personalised copies of a document from a data source", ["translate a document", "protect a file with a password", "compress images", "check spelling"], "A main document is combined with a list (names, addresses) to produce individual letters."),
    ("Which Excel function returns the current date and updates every time the sheet recalculates?", "TODAY", ["NOW", "DATE", "DAY", "CALENDAR"], "TODAY() returns the current date; NOW() returns date and time."),
    ("A primary key in a table:", "uniquely identifies each row and cannot be NULL", ["can contain duplicate values", "links two databases", "stores only numeric data", "is always the last column"], "It guarantees each record can be identified uniquely."),
    ("Which SQL command removes a table together with its structure?", "DROP", ["DELETE", "TRUNCATE", "REMOVE ROWS", "CLEAR"], "DROP deletes the table definition and data; TRUNCATE removes all rows but keeps the structure; DELETE removes selected rows."),
    ("A foreign key is a column that:", "refers to the primary key of another table", ["is always unique", "cannot be changed", "stores encrypted data", "is the first column of the table"], "It creates a relationship between tables."),
    ("The main purpose of normalisation in a database is to:", "reduce data redundancy and anomalies", ["increase file size", "speed up the monitor", "encrypt data", "remove all primary keys"], "Normalisation organises data to avoid duplication and update anomalies."),
    ("Which of the following is a DDL (Data Definition Language) command?", "CREATE", ["SELECT", "INSERT", "UPDATE", "DELETE"], "CREATE, ALTER and DROP define structure; the others manipulate data."),
    ("The time complexity of binary search on a sorted list of n items is:", "O(log n)", ["O(n)", "O(n²)", "O(1)", "O(n log n)"], "Each comparison halves the search range."),
    ("Which data structure follows the Last-In-First-Out principle?", "Stack", ["Queue", "Array", "Linked list", "Tree"], "The most recently pushed item is the first to be popped."),
    ("Which data structure follows the First-In-First-Out principle?", "Queue", ["Stack", "Binary tree", "Hash table", "Graph"], "The earliest inserted element is removed first."),
    ("Delivering software such as web-mail over the internet on a subscription basis is an example of:", "SaaS", ["IaaS", "PaaS", "DaaS", "On-premises licensing"], "Software as a Service gives users the finished application through a browser."),
    ("Renting virtual servers, storage and networks from a cloud provider is called:", "IaaS", ["SaaS", "PaaS", "BPaaS", "FaaS"], "Infrastructure as a Service provides raw computing infrastructure."),
    ("The key property of a blockchain that makes past records hard to alter is that:", "each block contains the hash of the previous block", ["all blocks are stored on one server", "it uses no cryptography", "blocks are deleted after use", "only one user can read it"], "Changing an old block would change its hash and break every later block."),
    ("The Internet of Things (IoT) refers to:", "physical devices with sensors connected to the internet", ["a very fast fibre cable", "a type of programming language", "a search engine", "an antivirus package"], "IoT devices collect and exchange data over networks."),
    ("Machine learning is best described as:", "systems that improve at a task by learning patterns from data", ["manually writing every rule", "a type of monitor", "a backup technique", "a network protocol"], "Models are trained on data instead of being explicitly programmed for each case."),
    ("A QR code stores information in:", "two dimensions", ["one dimension only", "three dimensions", "audio form", "magnetic form"], "QR codes encode data in a two-dimensional matrix; ordinary barcodes are one-dimensional."),
    ("Bluetooth technology is mainly used for:", "short-range wireless communication", ["long-distance satellite links", "wired networking", "optical fibre links", "cable television"], "Bluetooth works over a few metres."),
    ("NFC, used for tap-and-pay, works over a distance of about:", "a few centimetres", ["100 metres", "1 kilometre", "10 kilometres", "unlimited distance"], "Near Field Communication needs devices to be very close, which adds security."),
    ("A cookie in web browsing is:", "a small file stored by the browser on behalf of a website", ["a virus", "a type of search engine", "a hardware part", "an e-mail attachment only"], "Cookies remember session or preference data."),
    ("The full form of URL is:", "Uniform Resource Locator", ["Universal Resource Link", "Uniform Registry Locator", "Unified Resource Location", "Universal Routing Logic"], "A URL gives the address of a resource on the internet."),
]


# ---------------------------------------------------------------- assembly
PUZ_KINDS = ["linear", "circular", "floors", "days"]
_CONCEPT_ORDER = list(range(len(CONCEPTS)))
random.Random("scorefree-computer-concepts").shuffle(_CONCEPT_ORDER)


def concept_slice(t):
    """Distinct concept questions per test: tests 1-8 take 7 each, tests 9-10 take 6 each."""
    start = (t - 1) * 7 if t <= 8 else 56 + (t - 9) * 6
    size = 7 if t <= 8 else 6
    return [CONCEPTS[i] for i in _CONCEPT_ORDER[start:start + size]]


def concept_question(rng, item):
    q, right, wrong, exp = item
    opts = [right] + list(wrong)
    rng.shuffle(opts)
    return Q(CT, q, opts, opts.index(right), exp)


_RBP = {}
RCOUNTS = {
    "ibps": dict(syl=[0, 3, 4, 5], ineq=[0, 3, 4, 5], blood=[2, 3, 4], dirn=[1, 2, 3], coding=[2, 3, 4], io=[2, 3, 4], alnum=[2, 3, 4], ds=[0, 1, 2, 3],
                 order=[0, 2, 3], letter=[0, 2, 3], mathops=[0, 2], numarr=[0, 2], calendar=[0, 2]),
    "sbi": dict(syl=[0, 3, 4, 5], ineq=[0, 3, 4, 5], blood=[1, 2, 3], dirn=[1, 2], coding=[1, 2, 3], io=[1, 2, 3], alnum=[1, 2, 3], ds=[0, 1, 2],
                order=[0, 2], letter=[0, 2], mathops=[0, 2], numarr=[0, 2], calendar=[0, 2]),
}


def blueprints(exam):
    """Ten different blueprints per exam: puzzle sets (2-3, sizes 4-5) plus a different mix, count and order of every other type."""
    if exam in _RBP:
        return _RBP[exam]
    sbi = exam == "sbi"
    target = (SBI_Q - SBI_COMPUTER) if sbi else IBPS_Q
    from collections import Counter
    for salt in range(300):
        rng = random.Random(f"scorefree-mains-reasoning-blueprint-{exam}-{salt}")
        plans, seen, guard = [], set(), 0
        while len(plans) < 10 and guard < 60000:
            guard += 1
            k = rng.choice([2, 3])
            sizes = [rng.choice([4, 5]) for _ in range(k)]
            c = {key: rng.choice(vals) for key, vals in RCOUNTS[exam].items()}
            if c["syl"] == 0 and c["ineq"] == 0:
                continue
            if sum(sizes) + sum(c.values()) != target or sum(1 for v in c.values() if v) < 8:
                continue
            key = (tuple(sorted(sizes)), tuple(sorted(c.items())))
            if key in seen:
                continue
            seen.add(key)
            kinds = rng.sample(PUZ_KINDS, k)
            units = [f"puz{i}" for i in range(k)] + [name for name, v in c.items() if v]
            rng.shuffle(units)
            plans.append(dict(sizes=sizes, kinds=kinds, counts=c, units=units))
        if len(plans) < 10:
            continue
        firsts = [p_["units"][0].rstrip("0123456789") for p_ in plans]
        spread = all(len({p_["counts"][k_] for p_ in plans}) >= 3 for k_ in ("syl", "ineq", "blood", "coding", "io", "alnum"))
        if spread and max(Counter(firsts).values()) <= 3 and all(firsts[i] != firsts[i + 1] for i in range(9)):
            _RBP[exam] = plans
            return plans
    raise RuntimeError("reasoning blueprints")


def build_test(exam, t):
    rng = random.Random(f"scorefree-mains-reasoning-{exam}-{t}")
    sbi = exam == "sbi"
    bp = blueprints(exam)[t - 1]
    c = bp["counts"]
    out = []
    for unit in bp["units"]:
        if unit.startswith("puz"):
            i = int(unit[3:])
            title, intro, qs = puzzle_set(rng, bp["kinds"][i])
            rng.shuffle(qs)
            qs = qs[:bp["sizes"][i]]
            for q in qs:
                q["setTitle"], q["setIntro"] = title, intro
            out += qs
        elif unit in ("syl", "ineq"):
            wants = rng.sample(range(5), c[unit])
            fn = syllogism if unit == "syl" else inequality
            out += [fn(rng, w) for w in wants]
        elif unit == "blood":
            flags = [rng.random() < 0.5 for _ in range(c["blood"])]
            if c["blood"] >= 2 and len(set(flags)) == 1:
                flags[0] = not flags[0]
            out += [blood_question(rng, f_) for f_ in flags]
        elif unit == "dirn":
            fns = rng.sample([lambda: direction_question(rng, False), lambda: direction_question(rng, True), lambda: direction_facing(rng)], c["dirn"])
            out += [f_() for f_ in fns]
        elif unit == "coding":
            pool = [lambda: coding_language(rng), lambda: letter_coding(rng), lambda: digit_coding(rng), lambda: coding_language(rng)]
            out += [f_() for f_ in rng.sample(pool, c["coding"])]
        elif unit == "io":
            out += [input_output(rng) for _ in range(c["io"])]
        elif unit == "alnum":
            out += [rng.choice([alnum_question, alnum_between])(rng) for _ in range(c["alnum"])]
        elif unit == "ds":
            out += [ds_reasoning(rng, w) for w in rng.sample(range(5), c["ds"])]
        elif unit == "order":
            out += [order_ranking(rng) for _ in range(c["order"])]
        elif unit == "letter":
            out += [letter_position(rng) for _ in range(c["letter"])]
        elif unit == "mathops":
            out += [math_ops(rng) for _ in range(c["mathops"])]
        elif unit == "numarr":
            out += [number_arrangement(rng) for _ in range(c["numarr"])]
        elif unit == "calendar":
            out += [calendar_clock(rng) for _ in range(c["calendar"])]
    if sbi:
        picks = concept_slice(t)
        out += [concept_question(rng, cq) for cq in picks]
        out += [rng.choice(COMP_GEN)(rng) for _ in range(SBI_COMPUTER - len(picks))]
    assert len(out) == (SBI_Q if sbi else IBPS_Q), (len(out), bp)
    seen = set()
    for q in out:
        key = (q["q"], q.get("setTitle", ""))
        if key in seen:
            raise RuntimeError("duplicate question " + q["q"][:60])
        seen.add(key)
        assert len(q["opts"]) == 5 and len(set(q["opts"])) == 5 and 0 <= q["ans"] < 5 and q["exp"], q["q"][:80]
    return out


def build_test_safe(exam, t):
    for salt in range(8):
        try:
            return build_test(exam, t) if salt == 0 else _build_with_salt(exam, t, salt)
        except RuntimeError as e:
            last = e
    raise last


def _build_with_salt(exam, t, salt):
    import types
    real = random.Random
    try:
        random.Random = lambda seed=None, _s=salt: real(f"{seed}-salt{_s}")
        return build_test(exam, t)
    finally:
        random.Random = real


def main():
    bank = {e: {t: build_test_safe(e, t) for t in range(1, 11)} for e in ("ibps", "sbi")}
    sets = []
    for e in bank:
        for t in bank[e]:
            for q in bank[e][t]:
                if q.get("setIntro"):
                    key = (q.pop("setTitle"), q.pop("setIntro"))
                    if key not in sets:
                        sets.append(key)
                    q["s"] = sets.index(key)
    js = ("/* ScoreFree original Mains-level Reasoning Ability (+ Computer Aptitude for SBI) bank.\n"
          "   GENERATED by tools/build_mains_reasoning.py - edit the generator, not this file.\n"
          "   Replaces SF_BANK.<exam>.reasoning[1..10] so earlier basic practice items never mix into Mains reasoning tests. */\n"
          "(function(){\n  if(!window.SF_BANK) return;\n  var S=" + json.dumps(sets, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "  var B=" + json.dumps(bank, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "  ['ibps','sbi'].forEach(function(e){for(var t=1;t<=10;t++){B[e][t].forEach(function(q){if(q.s!==undefined){q.setTitle=S[q.s][0];q.setIntro=S[q.s][1];delete q.s;}});SF_BANK[e].reasoning[t]=B[e][t];}});\n})();\n")
    OUT.write_text(js, encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT), f"({len(js) // 1024} KB, {len(sets)} shared sets)")
    for e in bank:
        print(e, {t: len(v) for t, v in bank[e].items()})



# ====================================================== more question types (added for variety)
from build_mains_quant import make_options as _qopt, nice  # noqa: E402


def order_ranking(rng):
    T = "Order and Ranking"
    kind = rng.choice(["swap", "class", "between"])
    if kind == "swap":
        N = rng.randint(24, 48)
        pX = rng.randint(5, N // 2 - 2)
        pY = rng.randint(N // 2 + 2, N - 4)
        qy = N - pY + 1
        ask_n = rng.random() < 0.6
        stem = (f"In a row of students, A is {pX}th from the left end and B is {qy}th from the right end. When A and B interchange their positions, "
                f"A becomes {pY}th from the left end. ")
        if ask_n:
            stem += "How many students are there in the row?"
            val, how = N, f"After the interchange A stands where B stood, which is {pY}th from the left; B was {qy}th from the right, so N = {pY} + {qy} − 1 = <b>{N}</b>."
        else:
            val = pY - pX - 1
            stem += "How many students are standing between A and B?"
            how = f"A and B are at positions {pX} and {pY} from the left (B's old position = A's new position), so students between them = {pY} − {pX} − 1 = <b>{val}</b>."
        opts, ans = _qopt(rng, val, [val + 1, val - 1], none_ok=False)
        return Q(T, stem, opts, ans, how)
    if kind == "class":
        N = rng.randint(35, 60)
        r = rng.randint(8, 20)
        below, above = rng.randint(4, 9), rng.randint(2, 6)
        s_top = r + below
        who = rng.choice([("Sohan", "Mohan"), ("Tara", "Meera"), ("Kunal", "Varun")])
        ask = rng.choice(["bottom", "top_other"])
        if ask == "bottom":
            val = N - s_top + 1
            stem = (f"In a class of {N} students, {who[0]} is ranked {r}th from the top. {who[1]} is {below} ranks below {who[0]}. What is {who[1]}'s rank from the bottom?")
            how = f"{who[1]}'s rank from the top = {r} + {below} = {s_top}. Rank from the bottom = {N} − {s_top} + 1 = <b>{val}</b>."
        else:
            val = r - above
            stem = (f"In a class of {N} students, {who[0]} is ranked {r}th from the top. {who[1]} is {above} ranks above {who[0]}. What is {who[1]}'s rank from the top?")
            how = f"{who[1]}'s rank = {r} − {above} = <b>{val}</b>."
        opts, ans = _qopt(rng, val, [val + 1, val - 1], none_ok=False)
        return Q(T, stem, opts, ans, how)
    N = rng.randint(30, 50)
    pA, g = rng.randint(6, 14), rng.randint(4, 9)
    qB = N - (pA + g + 1) + 1
    if qB < 4:
        return order_ranking(rng)
    stem = (f"In a row of persons, A is {pA}th from the left end and B is {qB}th from the right end. A is to the left of B, and exactly {g} persons stand between them. How many persons are there in the row?")
    how = f"A is at position {pA}; B is at position {pA + g + 1} from the left. Total = {pA} + {g} + {qB} = <b>{N}</b> (positions up to B plus {qB} − 1 persons to its right, counted from the left)."
    how = f"B's position from the left = {pA} + {g} + 1 = {pA + g + 1}. Total persons = {pA + g + 1} + {qB} − 1 = <b>{N}</b>."
    opts, ans = _qopt(rng, N, [N + 1, N - 1], none_ok=False)
    return Q(T, stem, opts, ans, how)


BANK_WORDS = ["BANKING", "MARKETS", "STORAGE", "CREDITS", "PLATFORM", "DEPOSIT", "TREASURY", "INFLATION", "CURRENCY", "EXCHANGE", "PAYMENT", "SAVINGS", "BUDGETED", "CAPITAL"]


def letter_position(rng):
    T = "Letter and Word Based"
    kind = rng.choice(["gap", "same_pos", "vc", "shift"])
    word = rng.choice(BANK_WORDS)
    A = lambda c: ord(c) - 64
    if kind == "gap":
        pairs = [(i, j) for i in range(len(word)) for j in range(i + 1, len(word)) if word[i] != word[j] and abs(j - i) == abs(A(word[i]) - A(word[j]))]
        cnt = len(pairs)
        q = f"How many pairs of letters are there in the word '{word}' such that each pair has as many letters between them in the word as there are between them in the English alphabet?"
        how = ("Compare positions with alphabet gaps: " + (", ".join(f"{word[i]}{word[j]}" for i, j in pairs) if pairs else "no pair qualifies") + ".")
    elif kind == "same_pos":
        arranged = "".join(sorted(word))
        same = [word[i] for i in range(len(word)) if word[i] == arranged[i]]
        cnt = len(same)
        q = f"If the letters of the word '{word}' are arranged in alphabetical order, how many letters remain at the same position as in the original word?"
        how = f"Alphabetical order: {arranged}. Letters unchanged in position: {', '.join(same) if same else 'none'}."
    elif kind == "vc":
        cnt = sum(1 for i in range(len(word) - 1) if word[i] in "AEIOU" and word[i + 1] not in "AEIOU")
        q = f"How many vowels in the word '{word}' are immediately followed by a consonant?"
        how = "Pairs (vowel, next letter): " + ", ".join(f"{word[i]}{word[i + 1]}" for i in range(len(word) - 1) if word[i] in "AEIOU") + "."
    else:
        new = "".join(chr((ord(c) - 65 + 1) % 26 + 65) for c in word)
        cnt = sum(1 for c in new if c in "AEIOU")
        q = f"If every letter of the word '{word}' is replaced by the next letter of the English alphabet, how many vowels will the new word contain?"
        how = f"New word: {new}; vowels in it: {', '.join(c for c in new if c in 'AEIOU') or 'none'}."
    return Q(T, q, COUNT_OPTS, count_answer(cnt), f"{how}<br><b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")


def math_ops(rng):
    T = "Mathematical Operations"
    ops = ["+", "−", "×", "÷"]
    for _ in range(3000):
        perm = ops[:]
        rng.shuffle(perm)
        if any(a == b for a, b in zip(ops, perm)):
            continue
        mapping = dict(zip(ops, perm))                              # shown symbol -> real operation
        n = rng.randint(4, 5)
        nums = [rng.randint(2, 24) for _ in range(n)]
        shown_syms = [rng.choice(ops) for _ in range(n - 1)]
        real = [mapping[x] for x in shown_syms]
        pyop = {"+": "+", "−": "-", "×": "*", "÷": "/"}
        expr = "".join([f"Fr({nums[0]})"] + [f"{pyop[o]}Fr({nums[i + 1]})" for i, o in enumerate(real)])
        try:
            val = eval(expr, {"Fr": Fr})
        except ZeroDivisionError:
            continue
        if not nice(val, 2) or val <= 0 or val > 400 or val.denominator != 1 or len(set(shown_syms)) < 3:
            continue
        shown = str(nums[0]) + "".join(f" {sy} {nums[i + 1]}" for i, sy in enumerate(shown_syms))
        legend = ", ".join(f"'{a}' means '{b}'" for a, b in mapping.items())
        q = f"If {legend}, then what is the value of the following expression?\n{shown} = ?"
        sub = str(nums[0]) + "".join(f" {o} {nums[i + 1]}" for i, o in enumerate(real))
        how = f"Replace the symbols as per the given meanings: {sub}.<br>Applying BODMAS (division/multiplication first, then addition/subtraction) gives <b>{fmt(val)}</b>."
        opts, ans = _qopt(rng, val, [val + 2, val - 3], none_ok=False)
        return Q(T, q, opts, ans, how)
    raise RuntimeError("math ops")


def number_arrangement(rng):
    T = "Number Arrangement"
    for _ in range(500):
        nums = rng.sample(range(120, 990), 5)
        if any(len(set(str(x))) < 3 for x in nums):
            continue
        arr = " ".join(str(x) for x in nums)
        kind = rng.choice(["swap", "desc", "cond"])
        if kind == "swap":
            new = [int(str(x)[2] + str(x)[1] + str(x)[0]) for x in nums]
            if len(set(new)) < 5 or any(str(x)[2] == "0" for x in nums):
                continue
            rank = rng.choice([("second highest", 1, True), ("second lowest", 1, False), ("third highest", 2, True)])
            srt = sorted(new, reverse=rank[2])
            ans_new = srt[rank[1]]
            idx = new.index(ans_new)
            opts_new = [str(x) for x in new]
            opts_new_sorted = sorted(opts_new, key=int)
            q = f"Study the numbers: {arr}\nIf the first and the last digits of every number are interchanged, which of the following will be the {rank[0]} number in the new set?"
            how = "New numbers: " + ", ".join(f"{nums[i]}→{new[i]}" for i in range(5)) + f". Arranged {'high to low' if rank[2] else 'low to high'}: {', '.join(map(str, srt))}.<br><b>Answer: {ans_new}</b>"
            return Q(T, q, opts_new_sorted, opts_new_sorted.index(str(ans_new)), how)
        if kind == "desc":
            unchanged = [x for x in nums if "".join(sorted(str(x), reverse=True)) == str(x)]
            cnt = len(unchanged)
            q = f"Study the numbers: {arr}\nIf the digits of every number are rearranged in descending order, how many numbers remain unchanged?"
            how = "Numbers already in descending digit order: " + (", ".join(map(str, unchanged)) or "none") + "."
            return Q(T, q, COUNT_OPTS, count_answer(cnt), f"{how}<br><b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")
        good = [x for x in nums if int(str(x)[0]) + int(str(x)[2]) > int(str(x)[1])]
        cnt = len(good)
        if cnt > 3:
            continue
        q = f"Study the numbers: {arr}\nHow many of these numbers have the sum of their first and last digits greater than their middle digit?"
        how = "Numbers satisfying the condition: " + (", ".join(map(str, good)) or "none") + "."
        return Q(T, q, COUNT_OPTS, count_answer(cnt), f"{how}<br><b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")
    raise RuntimeError("number arrangement")


def calendar_clock(rng):
    import datetime as dt
    T = "Calendar and Clock"
    kind = rng.choice(["day", "angle", "gain"])
    if kind == "day":
        d0 = dt.date(rng.randint(2021, 2032), rng.randint(1, 12), rng.randint(1, 28))
        d1 = d0 + dt.timedelta(days=rng.randint(30, 420))
        fm = lambda d: f"{d.day} {d.strftime('%B')} {d.year}"
        correct = d1.strftime("%A")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        opts, ans = pick_opts(rng, correct, days, key=days.index)
        q = f"If {fm(d0)} was a {d0.strftime('%A')}, which day of the week will {fm(d1)} be?"
        how = f"Number of days between the two dates = {(d1 - d0).days}. {(d1 - d0).days} = 7 × {(d1 - d0).days // 7} + {(d1 - d0).days % 7}, so the day moves {(d1 - d0).days % 7} step(s) ahead of {d0.strftime('%A')}: <b>{correct}</b>."
        return Q(T, q, opts, ans, how)
    if kind == "angle":
        for _ in range(200):
            h, m = rng.randint(1, 11), rng.choice([5, 10, 15, 20, 25, 35, 40, 45, 50, 55, 12, 18, 24, 36])
            a = abs(30 * h - Fr(11, 2) * m)
            a = min(a, 360 - a)
            if nice(a, 1) and a > 0:
                break
        opts, ans = _qopt(rng, a, [Fr(30 * h) - m * 6 if False else a + 15, a - 5], none_ok=False)
        q = f"What is the angle (in degrees) between the hour hand and the minute hand of a clock at {h}:{m:02d}?"
        how = f"Angle = |30h − 5.5m| = |30 × {h} − 5.5 × {m}| = |{30 * h} − {fmt(Fr(11, 2) * m)}| = {fmt(abs(30 * h - Fr(11, 2) * m))}°; the smaller angle is <b>{fmt(a)}°</b>."
        return Q(T, q, opts, ans, how)
    g = rng.choice([2, 3, 4, 5, 6])
    hrs = rng.choice([8, 10, 12, 15, 18, 20, 24])
    total_gain = g * hrs
    start_h = rng.randint(5, 9)
    actual_min = start_h * 60 + hrs * 60
    shown_min = actual_min + total_gain
    fmt_t = lambda mm: f"{((mm // 60 - 1) % 12) + 1}:{mm % 60:02d} {'a.m.' if (mm // 60) % 24 < 12 else 'p.m.'}"
    right = fmt_t(shown_min)
    pool = [fmt_t(shown_min + d) for d in (-g * 2, -g, g, 2 * g, 10, -10, 20)]
    opts, ans = pick_opts(rng, right, pool, key=None)
    q = (f"A clock gains {g} minutes every hour. It was set right at {fmt_t(start_h * 60)}. What time will it show when the correct time is {fmt_t(actual_min)}?")
    how = f"Elapsed true time = {hrs} hours, so the clock gains {hrs} × {g} = {total_gain} minutes. It will show {fmt_t(actual_min)} + {total_gain} min = <b>{right}</b>."
    return Q(T, q, opts, ans, how)


def direction_facing(rng):
    names8 = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
    for _ in range(200):
        h = rng.randrange(8)
        steps = []
        cur = h
        for _i in range(rng.choice([3, 4])):
            ang = rng.choice([45, 90, 135, 180])
            side = rng.choice(["clockwise", "anticlockwise"])
            cur = (cur + (ang // 45 if side == "clockwise" else -(ang // 45))) % 8
            steps.append((ang, side))
        if cur == h:
            continue
        who = rng.choice(["Ravi", "Neha", "Imran", "Sara"])
        text = f"{who} is facing {names8[h].lower()}. "
        text += "He/She turns " + ", then ".join(f"{a}° {s}" for a, s in steps) + ". In which direction is the person facing now?"
        opts, ans = pick_opts(rng, names8[cur], names8, key=names8.index)
        how = f"Start: {names8[h]}. " + "; ".join(f"{a}° {s}" for a, s in steps) + f" (clockwise = +, anticlockwise = −, each 45° is one step on the compass).<br>Final direction = <b>{names8[cur]}</b>."
        return Q("Direction Sense", text, opts, ans, how)
    raise RuntimeError("facing")


def digit_coding(rng):
    for _ in range(2000):
        ws = rng.sample(["BANK", "LOAN", "CASH", "FUND", "BOND", "NOTE", "CARD", "DEBT", "GAIN", "RATE", "TAXI", "SAFE", "MINT", "PLAN"], 3)
        letters = sorted(set("".join(ws)))
        if len(letters) > 10:
            continue
        ex, tgt = ws[:2], ws[2]
        if not set(tgt) <= set("".join(ex)) or len(set(tgt)) < 4:
            continue
        digs = rng.sample("123456789", len(letters)) if len(letters) <= 9 else None
        if not digs:
            continue
        mp = dict(zip(letters, digs))
        code = lambda w: "".join(mp[c] for c in w)
        right = code(tgt)
        pool = []
        for _t in range(40):
            lst = list(right)
            i, j = rng.sample(range(len(lst)), 2)
            lst[i], lst[j] = lst[j], lst[i]
            v = "".join(lst)
            if v != right and v not in pool:
                pool.append(v)
            k = rng.randrange(len(lst))
            lst2 = list(right)
            lst2[k] = rng.choice([d for d in "123456789" if d != right[k]])
            v2 = "".join(lst2)
            if v2 != right and v2 not in pool:
                pool.append(v2)
        if len(pool) < 4:
            continue
        opts, ans = pick_opts(rng, right, pool, key=None)
        q = f"In a certain code language, '{ex[0]}' is written as '{code(ex[0])}' and '{ex[1]}' is written as '{code(ex[1])}'. How will '{tgt}' be written in that code?"
        how = "Matching letters with digits from the two given words: " + ", ".join(f"{c} = {mp[c]}" for c in sorted(set(tgt))) + f".<br>So {tgt} is written as <b>{right}</b>."
        return Q("Coding-Decoding", q, opts, ans, how)
    raise RuntimeError("digit coding")


def alnum_between(rng):
    ORDW = ["first", "second", "third", "fourth", "fifth"]
    for _ in range(2000):
        seq = alnum_sequence(rng)
        A, B = rng.choice(["consonant", "vowel", "symbol", "digit"]), rng.choice(["consonant", "vowel", "symbol", "digit"])
        a_i, b_i = rng.randint(1, 3), rng.randint(1, 3)
        C = rng.choice(["digit", "symbol", "consonant"])
        pa = [i for i, x in enumerate(seq) if cls_of(x) == A]
        pb = [i for i, x in enumerate(seq) if cls_of(x) == B]
        if a_i > len(pa) or b_i > len(pb) or (A == B and a_i == b_i):
            continue
        lo, hi = sorted((pa[a_i - 1], pb[b_i - 1]))
        cnt = sum(1 for x in seq[lo + 1:hi] if cls_of(x) == C)
        if cnt > 4:
            continue
        q = ("Study the following arrangement and answer the question given below.\n" + " ".join(seq) +
             f"\nHow many {PLUR[C]} are there between the {ORDW[a_i - 1]} {A} and the {ORDW[b_i - 1]} {B} from the left end?")
        how = (f"The {ORDW[a_i - 1]} {A} from the left is {seq[pa[a_i - 1]]} and the {ORDW[b_i - 1]} {B} is {seq[pb[b_i - 1]]}. "
               f"Elements between them: {' '.join(seq[lo + 1:hi]) or '(none)'}; the {PLUR[C]} among them: {cnt}.<br><b>Answer: {COUNT_OPTS[count_answer(cnt)]}</b>")
        return Q("Alphanumeric Series", q, COUNT_OPTS, count_answer(cnt), how)
    raise RuntimeError("alnum between")


if __name__ == "__main__":
    main()
