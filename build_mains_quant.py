#!/usr/bin/env python3
"""ScoreFree original Mains-level Quantitative Aptitude generator.

Writes ``question-bank.mains-quant.js`` which fills IBPS Clerk Mains (35 Q) and
SBI Clerk Mains (50 Q) Quantitative Aptitude tests 1-10 with ORIGINAL questions:
quadratic-equation relations, number series (missing / wrong term), data
interpretation sets with real tables and SVG charts, multi-step arithmetic
caselets, approximation, data sufficiency and quantity comparison.

Every question is built forward from hidden values, then re-solved from the
printed data only; ``assert`` statements make the build fail if the two disagree.
Run:  python tools/build_mains_quant.py
"""
import json
import math
import random
from fractions import Fraction as Fr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "question-bank.mains-quant.js"
IBPS_Q, SBI_Q = 35, 50
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


# ----------------------------------------------------------------- helpers
def sup(n):
    return str(n).translate(SUP)


def fmt(x):
    x = Fr(x)
    if x.denominator == 1:
        return str(x.numerator)
    return f"{float(x):.2f}".rstrip("0").rstrip(".")


def ind(n):
    """Indian digit grouping: 1250000 -> 12,50,000."""
    n = int(n)
    s = str(abs(n))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + s


def nice(x, places=2):
    """True when x has at most `places` decimal places (so it prints exactly)."""
    x = Fr(x)
    return (x * 10 ** places).denominator == 1


def signed(v, first=False):
    """' + 5' / ' − 5' style term for polynomial text."""
    return ("" if first else " ") + ("+ " if v > 0 else "− ") + str(abs(v))


def make_options(rng, ans, mistakes=(), none_ok=True, fmtf=fmt):
    """Return (options, index). Numeric options in ascending order, sometimes with
    'None of these' as option E (which is occasionally the correct choice)."""
    ans = Fr(ans)
    places = 0
    while not nice(ans, places):
        places += 1
        assert places <= 2, f"answer {ans} is not a clean 2-decimal value"
    unit = Fr(1, 10 ** places)
    mult = max(1, round(abs(ans) * Fr(6, 100) / unit))
    pool, seen = [], {fmtf(ans)}

    def add(v):
        v = Fr(v)
        if ans >= 0 and v <= 0:
            return
        if not nice(v, 2):
            return
        key = fmtf(v)
        if key in seen:
            return
        seen.add(key)
        pool.append(v)

    for m in mistakes:
        add(m)
    pool = pool[:2]
    tries = 0
    while len(pool) < 6 and tries < 200:
        tries += 1
        k = rng.randint(1, 7)
        add(ans + rng.choice([-1, 1]) * k * mult * unit)
    assert len(pool) >= 4, (ans, pool)
    rng.shuffle(pool)
    use_none = none_ok and rng.random() < 0.22
    if use_none:
        if rng.random() < 0.25:                       # "None of these" is correct
            vals = sorted(pool[:4])
            return [fmtf(v) for v in vals] + ["None of these"], 4
        vals = sorted(pool[:3] + [ans])
        return [fmtf(v) for v in vals] + ["None of these"], vals.index(ans)
    vals = sorted(pool[:4] + [ans])
    return [fmtf(v) for v in vals], vals.index(ans)


def text_options(rng, correct, wrong, sort_key=None):
    items = [correct] + list(wrong)[:4]
    if sort_key:
        items.sort(key=sort_key)
    else:
        rng.shuffle(items)
    return items, items.index(correct)


def ratio_str(p, q):
    g = math.gcd(int(p), int(q))
    return f"{int(p) // g}:{int(q) // g}"


def ratio_options(rng, p, q):
    g = math.gcd(int(p), int(q))
    p, q = int(p) // g, int(q) // g
    right = f"{p}:{q}"
    cand, seen = [], {right}
    for dp, dq in [(1, 0), (0, 1), (-1, 0), (0, -1), (2, 0), (0, 2), (1, 1), (-1, 1), (1, -1), (3, 0), (0, 3), (2, 1)]:
        a, b = p + dp, q + dq
        if a <= 0 or b <= 0:
            continue
        s = ratio_str(a, b)
        if s not in seen:
            seen.add(s)
            cand.append(s)
    rng.shuffle(cand)
    items = [right] + cand[:4]
    rng.shuffle(items)
    return items, items.index(right)


def Q(topic, q, opts, ans, exp, **extra):
    d = {"topic": topic, "q": q, "opts": opts, "ans": ans, "exp": exp}
    d.update(extra)
    return d


def numq(rng, topic, q, value, exp, mistakes=(), fig=None, none_ok=True):
    opts, ans = make_options(rng, value, mistakes, none_ok)
    assert opts[ans] == "None of these" or Fr(opts[ans]) == Fr(value), (opts, ans, value)
    d = Q(topic, q, opts, ans, exp)
    if fig:
        d["fig"] = fig
    return d


# ------------------------------------------------------ quadratic equations
def poly(A, B, C, v):
    s = (v + "²") if A == 1 else f"{A}{v}²"
    if B:
        s += (" + " if B > 0 else " − ") + (v if abs(B) == 1 else f"{abs(B)}{v}")
    if C:
        s += (" + " if C > 0 else " − ") + str(abs(C))
    return s + " = 0"


def factor(d, n, v):
    lead = v if d == 1 else f"{d}{v}"
    return f"({lead} − {n})" if n > 0 else f"({lead} + {-n})"


def quad_eq(rng):
    while True:
        roots = []
        for _ in range(2):
            den = rng.choice([1, 1, 1, 2, 3, 4, 5])
            num = rng.choice([x for x in range(-18, 25) if x != 0])
            roots.append(Fr(num, den))
        if roots[0] != roots[1] or rng.random() < 0.15:
            break
    (n1, d1), (n2, d2) = [(r.numerator, r.denominator) for r in roots]
    A, B, C = d1 * d2, -(d1 * n2 + d2 * n1), n1 * n2
    g = math.gcd(math.gcd(A, abs(B)), abs(C))
    return roots, (A // g, B // g, C // g), ((d1, n1), (d2, n2)), g


def relation(xs, ys):
    pairs = [(x, y) for x in xs for y in ys]
    if all(x > y for x, y in pairs):
        return ">"
    if all(x < y for x, y in pairs):
        return "<"
    if all(x >= y for x, y in pairs):
        return "≥"
    if all(x <= y for x, y in pairs):
        return "≤"
    return "="


def mf(x):
    return fmt(x).replace("-", "−")


def solve_text(eq, v):
    roots, (A, B, C), ((d1, n1), (d2, n2)), g = eq
    fac = f"{factor(d1, n1, v)}{factor(d2, n2, v)}"
    note = "" if g == 1 else f" (this is the equation multiplied by {g}; the roots are unchanged)"
    if len(set(roots)) == 1:
        return f"{poly(A, B, C, v)} → {fac} = 0{note} → {v} = {mf(roots[0])} (repeated root)"
    rs = " or ".join(mf(r) for r in roots)
    return f"{poly(A, B, C, v)} → {fac} = 0{note} → {v} = {rs}"


REL_OPTS = ["x > y", "x ≥ y", "x < y", "x ≤ y", "x = y or the relationship cannot be established"]
REL_IDX = {">": 0, "≥": 1, "<": 2, "≤": 3, "=": 4}


def build_quadratics(rng, count=5):
    wanted = ["<", ">", "≥", "≤", "="]
    rng.shuffle(wanted)
    out = []
    for i in range(count):
        want = wanted[i % 5]
        for _ in range(60000):
            ex, ey = quad_eq(rng), quad_eq(rng)
            if relation(ex[0], ey[0]) == want:
                break
        else:
            raise RuntimeError("could not build quadratic relation " + want)
        rel = relation(ex[0], ey[0])
        q = ("Directions: Two equations I and II are given. Solve both and choose the correct relation between x and y.\n"
             f"I.  {poly(*ex[1], 'x')}\nII. {poly(*ey[1], 'y')}")
        xs = ", ".join(mf(r) for r in sorted(ex[0]))
        ys = ", ".join(mf(r) for r in sorted(ey[0]))
        cmpd = {">": "every value of x is greater than every value of y",
                "<": "every value of x is smaller than every value of y",
                "≥": "every x is greater than or equal to every y, with equality possible",
                "≤": "every x is smaller than or equal to every y, with equality possible",
                "=": "x and y overlap, so no single relation holds for all value pairs"}[rel]
        exp = (f"I. {solve_text(ex, 'x')}<br>II. {solve_text(ey, 'y')}<br>"
               f"x ∈ {{{xs}}}, y ∈ {{{ys}}}. Comparing every x with every y: {cmpd}.<br>"
               f"<b>Answer: {REL_OPTS[REL_IDX[rel]]}</b>")
        out.append(Q("Quadratic Equations", q, REL_OPTS, REL_IDX[rel], exp))
    return out


# ------------------------------------------------------------- number series
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23]


def series_family(rng, fam):
    """Return (terms[8], step_texts, summary). Terms are ints."""
    if fam == 0:
        m, e, a = rng.choice([1, 2, 3]), rng.choice([2, 3]), rng.randint(1, 9)
        t = [a]
        for i in range(7):
            t.append(t[-1] * m + (i + 1) ** e)
        steps = [(f"{t[i]} × {m} + {i + 1}{sup(e)} = {t[i + 1]}" if m > 1 else f"{t[i]} + {i + 1}{sup(e)} = {t[i + 1]}") for i in range(7)]
        word = "squares" if e == 2 else "cubes"
        summary = (f"each term = previous term × {m} + the {word} of 1, 2, 3, … in order" if m > 1
                   else f"each term = previous term + the {word} of 1, 2, 3, … in order")
    elif fam == 1:
        c, a = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4, 5, 6]), rng.randint(2, 8)
        t = [a]
        for i in range(7):
            t.append(t[-1] * (i + 1) + c)
        steps = [f"{t[i]} × {i + 1}{signed(c)} = {t[i + 1]}" for i in range(7)]
        summary = f"multipliers rise 1, 2, 3, … and a constant {signed(c).strip().replace(' ', '')} is applied each time"
    elif fam == 2:
        s, e, a = rng.randint(1, 4), rng.choice([2, 3]), rng.randint(1, 30)
        t = [a]
        for i in range(7):
            t.append(t[-1] + (s + i) ** e)
        steps = [f"{t[i]} + {s + i}{sup(e)} = {t[i + 1]}" for i in range(7)]
        summary = f"the differences are consecutive {'squares' if e == 2 else 'cubes'} starting from {s}{sup(e)}"
    elif fam == 3:
        st, a = rng.randint(0, 2), rng.randint(1, 20)
        t = [a]
        for i in range(7):
            t.append(t[-1] + PRIMES[st + i] ** 2)
        steps = [f"{t[i]} + {PRIMES[st + i]}² = {t[i + 1]}" for i in range(7)]
        summary = "the differences are squares of consecutive prime numbers"
    elif fam == 4:
        k0, p, q = rng.randint(1, 3), rng.choice([-3, -2, -1, 1, 2, 3, 4]), rng.randint(-3, 6)
        ks = list(range(k0, k0 + 8))
        t = [k ** 3 + p * k + q for k in ks]
        steps = [f"n = {k}: {k}³{signed(p)}×{k}{signed(q)} = {k ** 3 + p * k + q}" for k in ks]
        summary = f"the n-th term is n³ {'+' if p > 0 else '−'} {'' if abs(p) == 1 else abs(p)}n {'+' if q >= 0 else '−'} {abs(q)}, starting from n = {k0}"
    elif fam == 5:
        o0, d, e0, m = rng.randint(1, 20), rng.randint(2, 9), rng.randint(2, 9), rng.choice([2, 3])
        odd, even = [o0], [e0]
        for j in range(3):
            odd.append(odd[-1] + d * (j + 1))
            even.append(even[-1] * m)
        t = [x for pair in zip(odd, even) for x in pair]
        steps = [f"odd-position terms: {odd[j]} + {d}×{j + 1} = {odd[j + 1]}" for j in range(3)] + \
                [f"even-position terms: {even[j]} × {m} = {even[j + 1]}" for j in range(3)]
        summary = f"two interleaved series — odd places add {d}, {2 * d}, {3 * d}, …; even places are multiplied by {m}"
    elif fam == 6:
        p, q, a0, b0, s = rng.choice([2, 3]), rng.choice([2, 3, 4]), rng.randint(1, 6), rng.randint(1, 6), rng.randint(1, 8)
        t = [s]
        steps = []
        for i in range(7):
            if i % 2 == 0:
                t.append(t[-1] * p + a0)
                steps.append(f"{t[i]} × {p} + {a0} = {t[i + 1]}")
            else:
                t.append(t[-1] * q - b0)
                steps.append(f"{t[i]} × {q} − {b0} = {t[i + 1]}")
        summary = f"operations alternate: (× {p}, + {a0}) then (× {q}, − {b0})"
    else:
        c, a, b = rng.randint(-2, 4), rng.randint(1, 6), rng.randint(2, 9)
        t = [a, b]
        for i in range(6):
            t.append(t[-1] + t[-2] + c)
        steps = [f"{t[i]} + {t[i + 1]}{signed(c)} = {t[i + 2]}" for i in range(6)]
        summary = f"each term = sum of the previous two terms{signed(c)}"
    trim = {0: 6, 1: 6, 2: 6, 3: 6, 4: 7, 6: 6, 7: 5}
    if fam == 5:
        steps = steps[:3] + steps[3:5]
    else:
        steps = steps[:trim[fam]]
    return t, steps, summary


def series_terms(rng, fam_choices):
    for _ in range(400):
        fam = rng.choice(fam_choices)
        t, steps, summary = series_family(rng, fam)
        if len(set(t[:7])) == 7 and 0 < min(t[:7]) and max(t[:7]) < 100000:
            return fam, t, steps, summary
    raise RuntimeError("series")


def series_missing(rng):
    fam, t, steps, summary = series_terms(rng, [0, 1, 2, 3, 4, 5, 6, 7])
    j = rng.randint(2, 5)
    shown = [("?" if i == j else str(v)) for i, v in enumerate(t[:7])]
    q = "Find the missing term in the series:\n" + ", ".join(shown)
    near = [t[j] + (t[j] - t[j - 1]) - (t[j - 1] - t[j - 2]), t[j - 1] + (t[j - 1] - t[j - 2])]
    exp = f"Pattern: {summary}.<br>" + "<br>".join(steps) + f"<br>The missing term is <b>{t[j]}</b>."
    return numq(rng, "Number Series", q, t[j], exp, mistakes=near)


def series_wrong(rng):
    fam, t, steps, summary = series_terms(rng, [0, 1, 2, 3, 4, 6, 7])
    shown = t[:7]
    j = rng.randint(2, 5)
    for _ in range(100):
        delta = rng.choice([-1, 1]) * rng.choice([1, 2, 3, 4, 5, 6, 7, 9, 11])
        wrong = shown[j] + delta
        if wrong > 0 and wrong not in shown:
            break
    else:
        raise RuntimeError("wrong term")
    row = shown[:]
    row[j] = wrong
    others = [i for i in range(7) if i != j]
    rng.shuffle(others)
    pick = sorted([j] + others[:4])
    opts = [str(row[i]) for i in pick]
    q = "Find the wrong term in the series:\n" + ", ".join(str(v) for v in row)
    exp = (f"Pattern: {summary}.<br>" + "<br>".join(steps) +
           f"<br>Term number {j + 1} should be {shown[j]}, not {wrong}. <b>Wrong term: {wrong}</b>.")
    return Q("Number Series", q, opts, pick.index(j), exp)


# ------------------------------------------------------------- approximation
def approx_question(rng):
    kind = rng.randint(0, 3)

    def jig(v, pct=0.0015):
        return round(v * (1 + rng.choice([-1, 1]) * rng.uniform(0.0003, pct)), 2)

    if kind == 0:
        p, n1 = rng.choice([15, 25, 35, 45, 55, 65, 75]), rng.choice([400, 600, 800, 1200, 1600])
        r, s = rng.randint(11, 19), rng.randint(6, 13)
        mult = rng.randint(4, 12)
        val = Fr(p * n1, 100) + r ** 2 - s * mult
        shown = f"{jig(p)}% of {jig(n1)} + ({jig(r)})² − {jig(s)} × {jig(mult)}"
        exp = f"{p}% of {n1} = {fmt(Fr(p * n1, 100))}; {r}² = {r * r}; {s} × {mult} = {s * mult}.<br>{fmt(Fr(p * n1, 100))} + {r * r} − {s * mult} = <b>{fmt(val)}</b>."
    elif kind == 1:
        a, m = rng.choice([144, 196, 225, 289, 324, 361, 441, 529]), rng.randint(6, 15)
        n2, f = rng.choice([360, 480, 720, 840, 960]), rng.choice([Fr(3, 8), Fr(5, 6), Fr(7, 12), Fr(5, 8)])
        root = int(math.isqrt(a))
        val = root * m + f * n2
        shown = f"√{jig(a)} × {jig(m)} + ({f.numerator}/{f.denominator}) of {jig(n2)}"
        exp = f"√{a} = {root}; {root} × {m} = {root * m}; {f.numerator}/{f.denominator} of {n2} = {fmt(f * n2)}.<br>{root * m} + {fmt(f * n2)} = <b>{fmt(val)}</b>."
    elif kind == 2:
        n1, d, p = rng.choice([1260, 1890, 2520, 3150, 4200]), rng.choice([6, 7, 9, 14, 15]), rng.choice([20, 30, 40, 60, 80])
        c = rng.randint(4, 9)
        val = Fr(n1, d) * Fr(p, 100) + c ** 3
        shown = f"({jig(n1)} ÷ {jig(d)}) × {jig(p)}% + ({jig(c)})³"
        exp = f"{n1} ÷ {d} = {n1 // d}; {p}% of {n1 // d} = {fmt(Fr(n1, d) * Fr(p, 100))}; {c}³ = {c ** 3}.<br>{fmt(Fr(n1, d) * Fr(p, 100))} + {c ** 3} = <b>{fmt(val)}</b>."
    else:
        a, b = rng.randint(24, 48), rng.randint(14, 26)
        p, n = rng.choice([12, 18, 24, 36]), rng.choice([250, 500, 750, 1250])
        val = a * a - b * b + Fr(p * n, 100)
        shown = f"({jig(a)})² − ({jig(b)})² + {jig(p)}% of {jig(n)}"
        exp = f"{a}² − {b}² = {a * a - b * b}; {p}% of {n} = {fmt(Fr(p * n, 100))}.<br>{a * a - b * b} + {fmt(Fr(p * n, 100))} = <b>{fmt(val)}</b>."
    if not nice(val, 0):
        return approx_question(rng)
    q = ("What approximate value should come in place of the question mark (?) in the following question? "
         "(You are not expected to calculate the exact value.)\n" + shown + " = ?")
    exp = "Round each number to the nearest convenient value:<br>" + exp
    return numq(rng, "Approximation", q, val, exp, none_ok=False)


# ------------------------------------------------------------- charts & tables
COLS = ["#5b4bdb", "#f59e0b", "#10b981", "#ef4444", "#0ea5e9", "#a855f7"]


def html_table(headers, rows, caption=None):
    th = "".join(f'<th style="border:1px solid #cfc9ee;background:#efeaff;padding:7px 9px;text-align:center;font-weight:800">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f'<td style="border:1px solid #e1ddf4;padding:7px 9px;text-align:center">{c}</td>' for c in r) + "</tr>" for r in rows)
    cap = f'<p style="margin:0 0 8px;font-weight:700">{caption}</p>' if caption else ""
    return (f'{cap}<div style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;font-size:.93rem;font-weight:500">'
            f"<tr>{th}</tr>{body}</table></div>")


def _axes(W, H, ml, mr, mt, mb, ymin, ymax, step, ytitle):
    ph = H - mt - mb
    g = []
    v = ymin
    while v <= ymax + 1e-9:
        y = mt + ph * (1 - (v - ymin) / (ymax - ymin))
        g.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W - mr}" y2="{y:.1f}" stroke="#e3e0f2" stroke-width="1"/>'
                 f'<text x="{ml - 6}" y="{y + 3.5:.1f}" font-size="11" text-anchor="end" fill="#4d4862">{fmt(v)}</text>')
        v += step
    g.append(f'<text x="12" y="{mt + ph / 2:.0f}" font-size="10" fill="#4d4862" transform="rotate(-90 12 {mt + ph / 2:.0f})" text-anchor="middle">{ytitle}</text>')
    g.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{H - mb}" stroke="#4d4862"/><line x1="{ml}" y1="{H - mb}" x2="{W - mr}" y2="{H - mb}" stroke="#4d4862"/>')
    return "".join(g)


def _legend(names, x0, y0):
    out, x = [], x0
    for i, n in enumerate(names):
        out.append(f'<rect x="{x}" y="{y0}" width="11" height="11" rx="2" fill="{COLS[i]}"/><text x="{x + 16}" y="{y0 + 10}" font-size="12" fill="#302a4c">{n}</text>')
        x += 32 + 6.6 * len(n)
    return "".join(out)


def bar_svg(cats, series, ymax, step, ytitle, title):
    W, H, ml, mr, mt, mb = 420, 300, 40, 8, 52, 34
    pw, ph = W - ml - mr, H - mt - mb
    gw = pw / len(cats)
    bw = gw * 0.74 / len(series)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{title}" xmlns="http://www.w3.org/2000/svg" style="max-width:640px;background:#fff;border:1px solid #e1ddf4;border-radius:12px">',
         f'<text x="{W / 2}" y="18" font-size="12" font-weight="700" text-anchor="middle" fill="#302a4c">{title}</text>',
         _legend([n for n, _ in series], ml, 28), _axes(W, H, ml, mr, mt, mb, 0, ymax, step, ytitle)]
    for ci, c in enumerate(cats):
        x0 = ml + gw * ci + gw * 0.13
        for si, (_, vals) in enumerate(series):
            h = ph * vals[ci] / ymax
            x = x0 + bw * si
            s.append(f'<rect x="{x:.1f}" y="{mt + ph - h:.1f}" width="{bw - 1.5:.1f}" height="{h:.1f}" fill="{COLS[si]}" rx="2"/>'
                     f'<text x="{x + bw / 2 - .7:.1f}" y="{mt + ph - h - 4:.1f}" font-size="10.5" text-anchor="middle" fill="#302a4c" font-weight="700">{fmt(vals[ci])}</text>')
        s.append(f'<text x="{ml + gw * ci + gw / 2:.1f}" y="{H - mb + 16}" font-size="12" text-anchor="middle" fill="#302a4c">{c}</text>')
    return "".join(s) + "</svg>"


def line_svg(cats, series, ymin, ymax, step, ytitle, title):
    W, H, ml, mr, mt, mb = 420, 300, 40, 14, 52, 34
    pw, ph = W - ml - mr, H - mt - mb
    gw = pw / len(cats)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{title}" xmlns="http://www.w3.org/2000/svg" style="max-width:640px;background:#fff;border:1px solid #e1ddf4;border-radius:12px">',
         f'<text x="{W / 2}" y="18" font-size="12" font-weight="700" text-anchor="middle" fill="#302a4c">{title}</text>',
         _legend([n for n, _ in series], ml, 28), _axes(W, H, ml, mr, mt, mb, ymin, ymax, step, ytitle)]
    for si, (_, vals) in enumerate(series):
        pts = [(ml + gw * i + gw / 2, mt + ph * (1 - (v - ymin) / (ymax - ymin))) for i, v in enumerate(vals)]
        s.append(f'<polyline fill="none" stroke="{COLS[si]}" stroke-width="2.4" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>')
        for i, (x, y) in enumerate(pts):
            dy = -9 if si == 0 else 17
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{COLS[si]}"/>'
                     f'<text x="{x:.1f}" y="{y + dy:.1f}" font-size="11" font-weight="800" text-anchor="middle" fill="{COLS[si]}">{fmt(vals[i])}</text>')
    for i, c in enumerate(cats):
        s.append(f'<text x="{ml + gw * i + gw / 2:.1f}" y="{H - mb + 16}" font-size="12" text-anchor="middle" fill="#302a4c">{c}</text>')
    return "".join(s) + "</svg>"


def pie_svg(labels, pcts, title):
    W, H, cx, cy, r = 420, 320, 210, 170, 92
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{title}" xmlns="http://www.w3.org/2000/svg" style="max-width:520px;background:#fff;border:1px solid #e1ddf4;border-radius:12px">',
         f'<text x="{W / 2}" y="20" font-size="12" font-weight="700" text-anchor="middle" fill="#302a4c">{title}</text>']
    ang = -math.pi / 2
    for i, (lab, p) in enumerate(zip(labels, pcts)):
        a2 = ang + 2 * math.pi * p / 100
        x1, y1, x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang), cx + r * math.cos(a2), cy + r * math.sin(a2)
        large = 1 if p > 50 else 0
        s.append(f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} Z" fill="{COLS[i % 6]}" stroke="#fff" stroke-width="2"/>')
        mid = (ang + a2) / 2
        lx, ly = cx + (r + 28) * math.cos(mid), cy + (r + 28) * math.sin(mid)
        anchor = "start" if math.cos(mid) > 0.25 else ("end" if math.cos(mid) < -0.25 else "middle")
        s.append(f'<text x="{lx:.1f}" y="{ly - 2:.1f}" font-size="12" font-weight="700" text-anchor="{anchor}" fill="#302a4c">{lab}</text>'
                 f'<text x="{lx:.1f}" y="{ly + 11:.1f}" font-size="12" text-anchor="{anchor}" fill="#4d4862">{fmt(p)}%</text>')
        ang = a2
    return "".join(s) + "</svg>"


def pick_nice(rng, items, test, tries=None):
    items = list(items)
    rng.shuffle(items)
    for it in items:
        r = test(it)
        if r is not None:
            return r
    return None


# ------------------------------------------------------------ DI set builders
DEPTS = ["Operations", "Finance", "Marketing", "Human Resources", "Technology", "Logistics", "Legal", "Sales", "Audit", "Research"]
RATIOS = [(3, 2), (5, 3), (7, 5), (4, 3), (5, 4), (2, 1), (7, 3), (9, 7), (3, 1), (11, 9), (8, 7), (5, 2)]


def di_shift(rng):
    names = rng.sample(DEPTS, 5)
    rows = []
    for _ in names:
        for _t in range(20000):
            a, b = rng.choice(RATIOS)
            lo, hi = math.ceil(360 / (a + b)), math.floor(1300 / (a + b))
            if lo > hi:
                continue
            k = rng.randint(lo, hi)
            men, women = a * k, b * k
            pm, pw = rng.choice([20, 25, 30, 40, 50, 60, 75]), rng.choice([10, 20, 25, 30, 40, 50, 60])
            if (men * pm) % 100 == 0 and (women * pw) % 100 == 0:
                rows.append(dict(total=men + women, a=a, b=b, men=men, women=women, pm=pm, pw=pw,
                                 nm=men * pm // 100, nw=women * pw // 100))
                break
        else:
            raise RuntimeError("shift data")
    title = "Data Interpretation · Table · Night-shift staffing"
    tbl = html_table(["Department", "Total employees", "Men : Women", "Men on night shift (%)", "Women on night shift (%)"],
                     [[names[i], rows[i]["total"], f'{rows[i]["a"]}:{rows[i]["b"]}', f'{rows[i]["pm"]}%', f'{rows[i]["pw"]}%'] for i in range(5)])
    intro = ("<p>The table gives, for five departments of a company, the total number of employees, the ratio of men to women, and the "
             "percentage of men and of women who work the night shift. All remaining employees work the day shift.</p>" + tbl)
    T = "Data Interpretation · Table"
    qs = []

    def t1():
        x, y = rng.sample(range(5), 2)
        val = rows[x]["nm"] + rows[x]["nw"] + rows[y]["nm"] + rows[y]["nw"]
        exp = (f"{names[x]}: men {rows[x]['men']} × {rows[x]['pm']}% = {rows[x]['nm']}; women {rows[x]['women']} × {rows[x]['pw']}% = {rows[x]['nw']}.<br>"
               f"{names[y]}: men {rows[y]['men']} × {rows[y]['pm']}% = {rows[y]['nm']}; women {rows[y]['women']} × {rows[y]['pw']}% = {rows[y]['nw']}.<br>"
               f"Total night shift = {rows[x]['nm']} + {rows[x]['nw']} + {rows[y]['nm']} + {rows[y]['nw']} = <b>{val}</b>.")
        return numq(rng, T, f"How many employees of {names[x]} and {names[y]} together work the night shift?", val, exp,
                    mistakes=[rows[x]["nm"] + rows[y]["nm"], rows[x]["nw"] + rows[y]["nw"]])

    def t2():
        x, y = rng.sample(range(5), 2)
        p, q = rows[x]["nw"], rows[y]["men"] - rows[y]["nm"]
        exp = (f"Women on night shift in {names[x]} = {rows[x]['women']} × {rows[x]['pw']}% = {p}.<br>"
               f"Men on day shift in {names[y]} = {rows[y]['men']} − {rows[y]['nm']} = {q}.<br>Ratio = {p}:{q} = <b>{ratio_str(p, q)}</b>.")
        opts, ans = ratio_options(rng, p, q)
        return Q(T, f"What is the ratio of the number of women working the night shift in {names[x]} to the number of men working the day shift in {names[y]}?", opts, ans, exp)

    def t3():
        def ok(x):
            r = rows[x]
            v = Fr((r["nm"] + r["nw"]) * 100, r["total"])
            return (x, v) if nice(v, 2) else None
        res = pick_nice(rng, range(5), ok)
        if not res:
            return None
        x, v = res
        r = rows[x]
        exp = (f"Night shift in {names[x]} = {r['nm']} + {r['nw']} = {r['nm'] + r['nw']}.<br>"
               f"Required % = {r['nm'] + r['nw']}/{r['total']} × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"The night-shift employees of {names[x]} form what percent of its total employees?", v, exp,
                    mistakes=[Fr(r["nm"] * 100, r["men"]), Fr(r["nw"] * 100, r["women"])])

    def t4():
        v = Fr(sum(r["women"] - r["nw"] for r in rows), 5)
        parts = " + ".join(str(r["women"] - r["nw"]) for r in rows)
        exp = ("Day-shift women = total women − night-shift women, department by department: "
               + ", ".join(f"{names[i]} {rows[i]['women']} − {rows[i]['nw']} = {rows[i]['women'] - rows[i]['nw']}" for i in range(5))
               + f".<br>Average = ({parts})/5 = <b>{fmt(v)}</b>.")
        return numq(rng, T, "What is the average number of women working the day shift across the five departments?", v, exp,
                    mistakes=[Fr(sum(r["nw"] for r in rows), 5), Fr(sum(r["men"] - r["nm"] for r in rows), 5)])

    def t5():
        def ok(arg):
            x, f, w = arg
            r = rows[x]
            moved = Fr(r["nm"] * f, 100)
            if moved.denominator != 1:
                return None
            new_night = r["nm"] + r["nw"] - moved + w
            v = Fr(new_night * 100, r["total"])
            return (x, f, w, moved, new_night, v) if nice(v, 2) and new_night > 0 else None
        cands = [(x, f, w) for x in range(5) for f in (20, 25, 50) for w in (10, 12, 15, 20, 24, 30)]
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        x, f, w, moved, nn, v = res
        r = rows[x]
        exp = (f"Night-shift men in {names[x]} = {r['nm']}; {f}% of them = {fmt(moved)} move to the day shift. Night-shift women = {r['nw']}, and {w} more women move to nights.<br>"
               f"New night shift = {r['nm']} + {r['nw']} − {fmt(moved)} + {w} = {fmt(nn)}.<br>"
               f"Required % = {fmt(nn)}/{r['total']} × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"In {names[x]}, {f}% of the men on night shift are moved to the day shift and {w} women from the day shift are moved to the night shift. What percent of the department's employees will then work the night shift?", v, exp,
                    mistakes=[Fr((r['nm'] + r['nw'] - moved) * 100, r['total']), Fr((r['nm'] + r['nw'] + w) * 100, r['total'])])

    def t6():
        idx = rng.sample(range(5), 3)
        v = sum(rows[i]["men"] - rows[i]["nm"] for i in idx)
        exp = "Day-shift men = men − night-shift men: " + "; ".join(f"{names[i]}: {rows[i]['men']} − {rows[i]['nm']} = {rows[i]['men'] - rows[i]['nm']}" for i in idx) + f".<br>Total = <b>{v}</b>."
        return numq(rng, T, f"How many men in {names[idx[0]]}, {names[idx[1]]} and {names[idx[2]]} together work the day shift?", v, exp,
                    mistakes=[sum(rows[i]["nm"] for i in idx), sum(rows[i]["women"] - rows[i]["nw"] for i in idx)])

    def t7():
        x, y = rng.sample(range(5), 2)
        v = abs(rows[x]["nm"] - rows[y]["nw"])
        exp = (f"Night-shift men in {names[x]} = {rows[x]['men']} × {rows[x]['pm']}% = {rows[x]['nm']}.<br>"
               f"Night-shift women in {names[y]} = {rows[y]['women']} × {rows[y]['pw']}% = {rows[y]['nw']}.<br>Difference = <b>{v}</b>.")
        if v == 0:
            return None
        return numq(rng, T, f"What is the difference between the number of men on night shift in {names[x]} and the number of women on night shift in {names[y]}?", v, exp,
                    mistakes=[rows[x]["nm"] + rows[y]["nw"]])

    fns = [t1, t2, t3, t4, t5, t6, t7]
    rng.shuffle(fns)
    for f in fns:
        q = f()
        if q:
            qs.append(q)
        if len(qs) == 5:
            break
    assert len(qs) == 5
    return title, intro, qs


NICE_SOLD = [160, 200, 240, 250, 300, 320, 400, 450, 480, 500, 600, 640, 750, 800]


def di_bar(rng):
    start = rng.randint(2017, 2020)
    cats = [str(start + i) for i in range(6)]
    sold = [rng.choice(NICE_SOLD) for _ in range(6)]
    while len(set(sold)) < 5:
        sold = [rng.choice(NICE_SOLD) for _ in range(6)]
    prod = [s + rng.choice([40, 60, 80, 100, 120, 160, 200, 240]) for s in sold]
    unsold = [p - s for p, s in zip(prod, sold)]
    ymax = (max(prod) // 100 + 1) * 100
    step = 100 if ymax <= 900 else 200
    fig = bar_svg(cats, [("Units produced", prod), ("Units sold", sold)], ymax, step, "Units (in thousands)", "Production and sales of a factory (in thousand units)")
    title = "Data Interpretation · Bar graph · Production and sales"
    intro = "<p>The bar graph shows the number of units (in thousands) produced and sold by a factory over six consecutive years. Unsold units = produced − sold.</p>" + fig
    T = "Data Interpretation · Bar graph"
    qs = []

    def b1():
        L = rng.choice([4, 5])
        i = rng.randint(0, 6 - L)
        v = Fr(sum(unsold[i:i + L]), L)
        if not nice(v, 2):
            return None
        parts = " + ".join(f"({prod[k]} − {sold[k]})" for k in range(i, i + L))
        exp = f"Unsold units: {', '.join(f'{cats[k]}: {unsold[k]}' for k in range(i, i + L))}.<br>Average = ({parts})/{L} = {sum(unsold[i:i + L])}/{L} = <b>{fmt(v)}</b> thousand."
        return numq(rng, T, f"What is the average number of unsold units (in thousands) from {cats[i]} to {cats[i + L - 1]}?", v, exp,
                    mistakes=[Fr(sum(sold[i:i + L]), L)])

    def b2():
        pairs = [(i, j) for i in range(6) for j in range(i + 1, 6) if sold[j] > sold[i] and nice(Fr((sold[j] - sold[i]) * 100, sold[i]), 2)]
        if not pairs:
            return None
        i, j = rng.choice(pairs)
        v = Fr((sold[j] - sold[i]) * 100, sold[i])
        exp = (f"Sales in {cats[i]} = {sold[i]}; sales in {cats[j]} = {sold[j]}.<br>"
               f"Increase = {sold[j] - sold[i]}; percentage = {sold[j] - sold[i]}/{sold[i]} × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"By what percent were the units sold in {cats[j]} more than the units sold in {cats[i]}?", v, exp,
                    mistakes=[Fr((sold[j] - sold[i]) * 100, sold[j]), Fr((prod[j] - prod[i]) * 100, prod[i]) if prod[j] > prod[i] else v + 5])

    def b3():
        x, y = rng.sample(range(6), 2)
        exp = f"Production in {cats[x]} = {prod[x]}; sales in {cats[y]} = {sold[y]}.<br>Ratio = {prod[x]}:{sold[y]} = <b>{ratio_str(prod[x], sold[y])}</b>."
        opts, ans = ratio_options(rng, prod[x], sold[y])
        return Q(T, f"What is the ratio of the units produced in {cats[x]} to the units sold in {cats[y]}?", opts, ans, exp)

    def b4():
        ratios = [Fr(s, p) for s, p in zip(sold, prod)]
        top = max(ratios)
        if ratios.count(top) != 1:
            return None
        k = ratios.index(top)
        others = [c for c in cats if c != cats[k]]
        rng.shuffle(others)
        opts, ans = text_options(rng, cats[k], others[:4], sort_key=lambda c: int(c))
        lines = "; ".join(f"{cats[i]}: {sold[i]}/{prod[i]} = {float(ratios[i]) * 100:.1f}%" for i in range(6))
        exp = f"Sold as a percentage of produced — {lines}.<br>The highest is in <b>{cats[k]}</b>."
        return Q(T, "In which year were the units sold the highest percentage of the units produced?", opts, ans, exp)

    def b5():
        cands = [(i, j, p, q) for i in range(6) for j in range(i + 1, 6) for p in (20, 25, 30, 40, 50) for q in (60, 70, 75, 80, 85, 90)]
        def ok(c):
            i, j, p, q = c
            prodn = Fr(prod[i] + prod[j], 2) * Fr(100 + p, 100)
            uns = prodn * Fr(100 - q, 100)
            return (c, prodn, uns) if nice(uns, 2) and nice(prodn, 2) and uns > 0 else None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (i, j, p, q), prodn, uns = res
        exp = (f"Average production of {cats[i]} and {cats[j]} = ({prod[i]} + {prod[j]})/2 = {fmt(Fr(prod[i] + prod[j], 2))}.<br>"
               f"Next-year production = {fmt(Fr(prod[i] + prod[j], 2))} × {100 + p}% = {fmt(prodn)}.<br>"
               f"Sales = {q}% of it; unsold = {100 - q}% × {fmt(prodn)} = <b>{fmt(uns)}</b> thousand.")
        return numq(rng, T, f"In the following year, production is expected to be {p}% more than the average production of {cats[i]} and {cats[j]}, and the units sold are expected to be {q}% of that production. How many units (in thousands) are expected to remain unsold?", uns, exp,
                    mistakes=[prodn * Fr(q, 100), Fr(prod[i] + prod[j], 2) * Fr(100 - q, 100)])

    for f in (b1, b2, b3, b4, b5):
        q = f()
        if q is None:
            return di_bar(rng)
        qs.append(q)
    rng.shuffle(qs)
    return title, intro, qs


def di_line(rng):
    start = rng.randint(2016, 2020)
    cats = [str(start + i) for i in range(6)]
    pcts = [10, 12.5, 15, 20, 25, 30, 35, 40, 45, 50]
    E = [rng.choice([120, 160, 200, 240, 280, 320, 360, 400]) for _ in range(6)]
    Pf = [Fr(rng.choice(pcts)).limit_denominator(10) for _ in range(6)]
    R = [e * (1 + p / 100) for e, p in zip(E, Pf)]
    if any(r.denominator != 1 for r in R):
        return di_line(rng)
    R = [int(r) for r in R]
    P = [r - e for r, e in zip(R, E)]
    if len(set(P)) < 6:
        return di_line(rng)
    ymax = (max(R) // 100 + 1) * 100
    ymin = 0
    fig = line_svg(cats, [("Revenue", R), ("Expenditure", E)], ymin, ymax, 100, "₹ lakh", "Revenue and expenditure of a company (₹ lakh)")
    title = "Data Interpretation · Line graph · Revenue and expenditure"
    intro = "<p>The line graph shows a company's revenue and expenditure (in ₹ lakh) over six consecutive years. Profit = revenue − expenditure; profit % = profit/expenditure × 100.</p>" + fig
    T = "Data Interpretation · Line graph"
    qs = []

    def l1():
        i, j = sorted(rng.sample(range(6), 2))
        v = Fr((P[i] + P[j]) * 100, E[i] + E[j])
        if not nice(v, 2):
            return None
        exp = (f"{cats[i]}: profit = {R[i]} − {E[i]} = {P[i]}; {cats[j]}: profit = {R[j]} − {E[j]} = {P[j]}.<br>"
               f"Combined profit % = ({P[i]} + {P[j]})/({E[i]} + {E[j]}) × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"What is the overall profit percent of the company over {cats[i]} and {cats[j]} taken together?", v, exp,
                    mistakes=[(Pf[i] + Pf[j]) / 2, Fr((P[i] + P[j]) * 100, R[i] + R[j])])

    def l2():
        L = rng.choice([4, 5])
        i = rng.randint(0, 6 - L)
        v = Fr(sum(P[i:i + L]), L)
        if not nice(v, 2):
            return None
        exp = f"Profits ({cats[i]} to {cats[i + L - 1]}): " + ", ".join(str(x) for x in P[i:i + L]) + f".<br>Average = {sum(P[i:i + L])}/{L} = <b>{fmt(v)}</b> lakh."
        return numq(rng, T, f"What is the average annual profit (in ₹ lakh) from {cats[i]} to {cats[i + L - 1]}?", v, exp,
                    mistakes=[Fr(sum(R[i:i + L]), L) - Fr(sum(E[i:i + L]), L) + 10, Fr(sum(E[i:i + L]), L)])

    def l3():
        x, y = rng.sample(range(6), 2)
        exp = f"Revenue in {cats[x]} = {R[x]}; expenditure in {cats[y]} = {E[y]}.<br>Ratio = {R[x]}:{E[y]} = <b>{ratio_str(R[x], E[y])}</b>."
        opts, ans = ratio_options(rng, R[x], E[y])
        return Q(T, f"What is the ratio of the company's revenue in {cats[x]} to its expenditure in {cats[y]}?", opts, ans, exp)

    def l4():
        pairs = [(i, j) for i in range(6) for j in range(6) if i != j and P[j] > P[i] and nice(Fr((P[j] - P[i]) * 100, P[i]), 2)]
        if not pairs:
            return None
        i, j = rng.choice(pairs)
        v = Fr((P[j] - P[i]) * 100, P[i])
        exp = f"Profit in {cats[i]} = {P[i]}; profit in {cats[j]} = {P[j]}.<br>Required % = ({P[j]} − {P[i]})/{P[i]} × 100 = <b>{fmt(v)}%</b>."
        return numq(rng, T, f"The profit earned in {cats[j]} is what percent more than the profit earned in {cats[i]}?", v, exp,
                    mistakes=[Fr((P[j] - P[i]) * 100, P[j]), Pf[j] - Pf[i]])

    def l5():
        cands = [(x, k) for x in range(6) for k in (10, 20, 25, 40, 50)]
        def ok(c):
            x, k = c
            e2 = Fr(E[x] * (100 - k), 100)
            v = Fr((R[x] - e2) * 100, e2)
            return (c, e2, v) if nice(v, 2) and nice(e2, 2) else None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (x, k), e2, v = res
        exp = (f"Revised expenditure in {cats[x]} = {E[x]} × {100 - k}% = {fmt(e2)}; revenue stays {R[x]}.<br>"
               f"Profit = {R[x]} − {fmt(e2)} = {fmt(R[x] - e2)}; profit % = {fmt(R[x] - e2)}/{fmt(e2)} × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"If the expenditure in {cats[x]} had been {k}% lower while the revenue remained the same, what would the profit percent have been?", v, exp,
                    mistakes=[Pf[x] + k, Fr((R[x] - e2) * 100, R[x])])

    for f in (l1, l2, l3, l4, l5):
        q = f()
        if q is None:
            return di_line(rng)
        qs.append(q)
    rng.shuffle(qs)
    return title, intro, qs


STREAMS = ["Science", "Commerce", "Arts", "Engineering", "Medicine", "Law", "Management", "Design"]


def di_pie(rng):
    names = rng.sample(STREAMS, 6)
    for _ in range(20000):
        pct = [rng.choice([5, 10, 15, 20, 25, 30]) for _ in range(5)]
        last = 100 - sum(pct)
        if last in (5, 10, 15, 20, 25, 30):
            pct.append(last)
            break
    N = rng.choice([2400, 3000, 3600])
    cnt = [N * p // 100 for p in pct]
    rat = []
    for c in cnt:
        for _ in range(500):
            a, b = rng.choice(RATIOS)
            if c % (a + b) == 0:
                rat.append((a, b))
                break
        else:
            return di_pie(rng)
    boys = [c // (a + b) * a for c, (a, b) in zip(cnt, rat)]
    girls = [c - bb for c, bb in zip(cnt, boys)]
    fig = pie_svg(names, pct, f"Distribution of {ind(N)} students across streams")
    tbl = html_table(["Stream", "Boys : Girls"], [[names[i], f"{rat[i][0]}:{rat[i][1]}"] for i in range(6)])
    title = "Data Interpretation · Pie chart + table · Students by stream"
    intro = (f"<p>A university has {ind(N)} students. The pie chart shows the percentage of students in each stream, and the table gives the ratio of boys to girls in each stream.</p>"
             + fig + "<div style='height:12px'></div>" + tbl)
    T = "Data Interpretation · Pie chart"
    qs = []

    def p1():
        x = rng.randrange(6)
        exp = f"Students in {names[x]} = {pct[x]}% of {ind(N)} = {cnt[x]}.<br>Girls = {cnt[x]} × {rat[x][1]}/{rat[x][0] + rat[x][1]} = <b>{girls[x]}</b>."
        return numq(rng, T, f"How many girls study {names[x]}?", girls[x], exp, mistakes=[boys[x]])

    def p2():
        x, y = rng.sample(range(6), 2)
        v = abs(boys[x] - girls[y])
        if v == 0:
            return None
        exp = (f"Boys in {names[x]} = {cnt[x]} × {rat[x][0]}/{rat[x][0] + rat[x][1]} = {boys[x]}.<br>"
               f"Girls in {names[y]} = {cnt[y]} × {rat[y][1]}/{rat[y][0] + rat[y][1]} = {girls[y]}.<br>Difference = <b>{v}</b>.")
        return numq(rng, T, f"What is the difference between the number of boys in {names[x]} and the number of girls in {names[y]}?", v, exp,
                    mistakes=[boys[x] + girls[y]])

    def p3():
        idx = rng.sample(range(6), 3)
        v = sum(boys[i] for i in idx)
        exp = "Boys: " + "; ".join(f"{names[i]} = {cnt[i]} × {rat[i][0]}/{rat[i][0] + rat[i][1]} = {boys[i]}" for i in idx) + f".<br>Total = <b>{v}</b>."
        return numq(rng, T, f"What is the total number of boys in {names[idx[0]]}, {names[idx[1]]} and {names[idx[2]]}?", v, exp,
                    mistakes=[sum(girls[i] for i in idx)])

    def p4():
        def ok(x):
            v = Fr(girls[x] * 100, sum(girls))
            return (x, v) if nice(v, 2) else None
        res = pick_nice(rng, range(6), ok)
        if not res:
            return None
        x, v = res
        exp = (f"Girls: " + ", ".join(f"{names[i]} {girls[i]}" for i in range(6)) + f". Total girls = {sum(girls)}.<br>"
               f"Required % = {girls[x]}/{sum(girls)} × 100 = <b>{fmt(v)}%</b>.")
        return numq(rng, T, f"The girls of {names[x]} form what percent of all girls in the university?", v, exp,
                    mistakes=[Fr(pct[x]), Fr(girls[x] * 100, cnt[x])])

    def p5():
        cands = [(x, y, f) for x in range(6) for y in range(6) if x != y for f in (20, 25, 50)]
        def ok(c):
            x, y, f = c
            moved = Fr(girls[x] * f, 100)
            return (c, moved) if moved.denominator == 1 and moved > 0 else None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (x, y, f), moved = res
        v = cnt[y] + moved
        exp = (f"Girls in {names[x]} = {girls[x]}; {f}% of them = {fmt(moved)}.<br>"
               f"New strength of {names[y]} = {cnt[y]} + {fmt(moved)} = <b>{fmt(v)}</b>.")
        return numq(rng, T, f"If {f}% of the girls of {names[x]} shift to {names[y]}, how many students will {names[y]} then have?", v, exp,
                    mistakes=[cnt[y] - moved, cnt[y] + Fr(cnt[x] * f, 100)])

    for f in (p1, p2, p3, p4, p5):
        q = f()
        if q is None:
            return di_pie(rng)
        qs.append(q)
    rng.shuffle(qs)
    return title, intro, qs


def di_mixture(rng):
    names = ["P", "Q", "R", "S", "T"]
    rows = []
    for _ in names:
        while True:
            a, b = rng.choice([(3, 2), (4, 1), (5, 3), (7, 3), (2, 1), (3, 1), (7, 5), (5, 4), (9, 1), (3, 5), (1, 3), (2, 3), (5, 7)])
            k = rng.randint(100 // (a + b) + 1, 400 // (a + b))
            total = (a + b) * k
            if 80 <= total <= 480:
                rows.append(dict(total=total, a=a, b=b, milk=a * k, water=b * k))
                break
    title = "Data Interpretation · Table · Milk–water mixtures"
    tbl = html_table(["Vessel", "Mixture (litres)", "Milk : Water"], [[names[i], rows[i]["total"], f'{rows[i]["a"]}:{rows[i]["b"]}'] for i in range(5)])
    intro = "<p>Five vessels P, Q, R, S and T contain mixtures of milk and water. The quantity of each mixture and its milk : water ratio are given.</p>" + tbl
    T = "Data Interpretation · Mixtures"
    qs = []

    def m1():
        x, y = rng.sample(range(5), 2)
        v = rows[x]["milk"] + rows[y]["milk"]
        exp = (f"Milk in {names[x]} = {rows[x]['total']} × {rows[x]['a']}/{rows[x]['a'] + rows[x]['b']} = {rows[x]['milk']} L.<br>"
               f"Milk in {names[y]} = {rows[y]['total']} × {rows[y]['a']}/{rows[y]['a'] + rows[y]['b']} = {rows[y]['milk']} L.<br>Total = <b>{v} L</b>.")
        return numq(rng, T, f"How many litres of milk are there in vessels {names[x]} and {names[y]} together?", v, exp,
                    mistakes=[rows[x]["water"] + rows[y]["water"]])

    def m2():
        x, y = rng.sample(range(5), 2)
        p, q = rows[x]["milk"] + rows[y]["milk"], rows[x]["water"] + rows[y]["water"]
        exp = (f"{names[x]}: milk {rows[x]['milk']}, water {rows[x]['water']}. {names[y]}: milk {rows[y]['milk']}, water {rows[y]['water']}.<br>"
               f"Combined milk : water = {p}:{q} = <b>{ratio_str(p, q)}</b>.")
        opts, ans = ratio_options(rng, p, q)
        return Q(T, f"If the contents of vessels {names[x]} and {names[y]} are mixed, what is the ratio of milk to water in the new mixture?", opts, ans, exp)

    def m3():
        cands = [(x, pc) for x in range(5) for pc in (40, 50, 60, 75, 80)]
        def ok(c):
            x, pc = c
            r = rows[x]
            need = Fr(r["milk"] * 100, pc) - r["total"]
            return (c, need) if need > 0 and need.denominator == 1 else None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (x, pc), need = res
        r = rows[x]
        exp = (f"Milk in {names[x]} = {r['milk']} L (it stays constant). For milk to be {pc}%, total mixture = {r['milk']} × 100/{pc} = {fmt(Fr(r['milk'] * 100, pc))} L.<br>"
               f"Water to add = {fmt(Fr(r['milk'] * 100, pc))} − {r['total']} = <b>{fmt(need)} L</b>.")
        return numq(rng, T, f"How many litres of water must be added to vessel {names[x]} so that milk forms {pc}% of the mixture?", need, exp,
                    mistakes=[r["water"], Fr(r["total"] * pc, 100)])

    def m4():
        cands = [(x, f) for x in range(5) for f in (10, 20, 25, 40, 50)]
        def ok(c):
            x, f = c
            r = rows[x]
            rem = Fr(r["total"] * f, 100)
            milk_left = r["milk"] - rem * r["a"] / (r["a"] + r["b"])
            return (c, rem, milk_left) if rem.denominator == 1 and milk_left.denominator == 1 and nice(milk_left, 2) else None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (x, f), rem, left = res
        r = rows[x]
        exp = (f"{f}% of {r['total']} L = {fmt(rem)} L is removed; milk removed = {fmt(rem)} × {r['a']}/{r['a'] + r['b']} = {fmt(rem * r['a'] / (r['a'] + r['b']))} L.<br>"
               f"Milk left = {r['milk']} − {fmt(rem * r['a'] / (r['a'] + r['b']))} = <b>{fmt(left)} L</b> (water added does not change the milk).")
        return numq(rng, T, f"{f}% of the mixture in vessel {names[x]} is taken out and replaced with an equal quantity of water. How many litres of milk are now in the vessel?", left, exp,
                    mistakes=[r["milk"] - rem, r["milk"]])

    def m5():
        cands = [(x, c) for x in range(5) for c in (40, 50, 60, 80)]
        def ok(cc):
            x, c = cc
            r = rows[x]
            cost = c * r["milk"]
            for s in range(c - 10, 2 * c + 40):
                rev = s * r["total"]
                prof = Fr((rev - cost) * 100, cost)
                if prof > 0 and nice(prof, 2) and prof < 80:
                    return (cc, s, prof)
            return None
        res = pick_nice(rng, cands, ok)
        if not res:
            return None
        (x, c), s, prof = res
        r = rows[x]
        exp = (f"Cost price = milk only = {r['milk']} × ₹{c} = ₹{ind(c * r['milk'])} (water is free).<br>"
               f"Selling price = {r['total']} × ₹{s} = ₹{ind(s * r['total'])}.<br>"
               f"Profit % = ({ind(s * r['total'])} − {ind(c * r['milk'])})/{ind(c * r['milk'])} × 100 = <b>{fmt(prof)}%</b>.")
        return numq(rng, T, f"Milk costs ₹{c} per litre and water is free. If the whole mixture in vessel {names[x]} is sold at ₹{s} per litre, what is the profit percent?", prof, exp,
                    mistakes=[Fr((s - c) * 100, c) if s > c else prof + 6])

    fns = [m1, m2, m3, m4, m5]
    for f in fns:
        q = f()
        if q is None:
            return di_mixture(rng)
        qs.append(q)
    rng.shuffle(qs)
    return title, intro, qs


DI_BUILDERS = [di_shift, di_bar, di_line, di_pie, di_mixture]


# --------------------------------------------------- arithmetic caselet builders
# Each returns a dict P(topic, stem, value, exp, mistakes). Values are built forward from
# hidden numbers and then re-derived from the printed data only (assert).
def P(topic, stem, value, exp, mistakes=()):
    return dict(topic=topic, stem=stem, value=Fr(value), exp=exp, mistakes=list(mistakes))


def ar_boats1(rng):
    while True:
        s, b = rng.randint(2, 6), None
        b = rng.randint(s + 4, s + 14)
        du, dd = b - s, b + s
        d = math.lcm(du, dd) * rng.randint(1, 3)
        r = rng.randint(1, min(3, du - 1))
        if d <= 700:
            break
    tup, tdn = d // du, d // dd
    up, dn = Fr(d, tup), Fr(d, tdn)
    b2, s2 = (up + dn) / 2, (dn - up) / 2
    assert (b2, s2) == (b, s)
    up2, dn2 = b2 - (s2 + r), b2 + s2 + r
    k1, k2 = rng.randint(2, 6), rng.randint(2, 6)
    D1, D2 = int(up2 * k1), int(dn2 * k2)
    val = Fr(D1, 1) / up2 + Fr(D2, 1) / dn2
    assert val == k1 + k2
    stem = (f"A boat takes {tup} hours to travel {d} km upstream and {tdn} hours to return the same {d} km downstream. If the speed of the stream "
            f"increases by {r} km/h, how many hours will the boat take to travel {D1} km upstream and then {D2} km downstream?")
    exp = (f"Upstream speed = {d}/{tup} = {fmt(up)} km/h; downstream speed = {d}/{tdn} = {fmt(dn)} km/h.<br>"
           f"Boat in still water = ({fmt(up)} + {fmt(dn)})/2 = {fmt(b2)} km/h; stream = ({fmt(dn)} − {fmt(up)})/2 = {fmt(s2)} km/h.<br>"
           f"New stream = {fmt(s2 + r)} km/h → upstream {fmt(up2)} km/h, downstream {fmt(dn2)} km/h.<br>"
           f"Time = {D1}/{fmt(up2)} + {D2}/{fmt(dn2)} = {k1} + {k2} = <b>{k1 + k2} hours</b>.")
    return P("Boats and Streams", stem, val, exp, [Fr(D1 + D2, 1) / b2, Fr(D1, 1) / up2])


def ar_boats2(rng):
    while True:
        k = rng.choice([3, 5, 7])
        n = rng.randint(2, 6) * (k - 1) // 2
        diff = Fr(2 * n, k - 1)
        up, dn = diff * (k + 1) / 2, diff * (k - 1) / 2
        if diff.denominator == 1 and dn == n:
            break
    d_units = diff * (k * k - 1) / 2            # distance when stream speed = 1 unit
    val = d_units / k
    if not nice(val, 2):
        return ar_boats2(rng)
    stem = (f"The speed of a boat in still water is {k} times the speed of the stream. For the same distance, the boat takes {diff} hours more "
            f"to go upstream than downstream. How many hours would it take to cover that distance in still water?")
    exp = (f"Let the stream speed be 1 unit; boat = {k} units → upstream {k - 1}, downstream {k + 1}.<br>"
           f"Time difference: d/{k - 1} − d/{k + 1} = d × 2/{k * k - 1} = {diff} → d = {fmt(d_units)} units.<br>"
           f"Time in still water = {fmt(d_units)}/{k} = <b>{fmt(val)} hours</b>.")
    return P("Boats and Streams", stem, val, exp, [up, dn])


def ar_mixture(rng):
    while True:
        a, b = rng.choice([(3, 2), (4, 1), (5, 3), (7, 3), (3, 1), (5, 2), (7, 5), (2, 3), (4, 3)])
        x = (a + b) * rng.randint(4, 14)
        y = rng.choice([z for z in range(6, x // 2 + 1) if (z * a) % (a + b) == 0] or [0])
        if not y:
            continue
        M = Fr(x * a, a + b)
        M2 = M - Fr(y * a, a + b)
        W2 = x - M2
        g = math.gcd(int(M2), int(W2)) if M2.denominator == 1 else 0
        if g and M2 > 0:
            c, d = int(M2) // g, int(W2) // g
            if c + d <= 25 and (c, d) != (a, b) and c != d:
                break
    fa = Fr(a, a + b)
    x2 = y * fa / (fa - Fr(c, c + d))
    assert x2 == x
    stem = (f"A vessel contains a mixture of milk and water in the ratio {a}:{b}. When {y} litres of the mixture are removed and replaced with water, "
            f"the ratio of milk to water becomes {c}:{d}. What was the initial quantity of the mixture (in litres)?")
    exp = (f"Let the initial quantity be x. Milk = {a}x/{a + b}. Removing {y} L removes {y} × {a}/{a + b} = {fmt(Fr(y * a, a + b))} L of milk.<br>"
           f"Milk left = {a}x/{a + b} − {fmt(Fr(y * a, a + b))}, and the total is still x, so milk left = {c}x/{c + d}.<br>"
           f"x({a}/{a + b} − {c}/{c + d}) = {fmt(Fr(y * a, a + b))} → x = <b>{x}</b> litres.")
    return P("Mixtures and Alligation", stem, x, exp, [y * (a + b), x - y, Fr(y * (c + d), 1)])


def ar_interest(rng):
    while True:
        r, t1, s = rng.choice([8, 10, 12, 15]), rng.choice([3, 4, 5]), rng.choice([10, 20, 25])
        a, b = rng.choice([(2, 3), (3, 5), (4, 5), (3, 4), (5, 6), (2, 5)])
        cf = (1 + Fr(s, 100)) ** 2 - 1
        coef = b * cf - a * Fr(t1 * r, 100)
        if coef <= 0:
            continue
        kk = rng.choice([100, 200, 250, 400, 500, 600, 800, 1000])
        Dv = coef * kk
        if Dv.denominator == 1:
            break
    k2 = Dv / coef
    assert k2 == kk
    ask_total = rng.random() < 0.5
    val = (a + b) * kk if ask_total else a * kk
    stem = (f"Neha invests ₹P₁ in Scheme A at {r}% p.a. simple interest for {t1} years and ₹P₂ in Scheme B at {s}% p.a. compound interest (compounded annually) for 2 years, "
            f"where P₁:P₂ = {a}:{b}. The interest earned from Scheme B exceeds that from Scheme A by ₹{ind(Dv)}. "
            + ("What is the total sum invested in the two schemes (in ₹)?" if ask_total else "What is the sum invested in Scheme A (in ₹)?"))
    exp = (f"Let P₁ = {a}k and P₂ = {b}k. CI factor for 2 years at {s}% = (1 + {s}/100)² − 1 = {fmt(cf)}.<br>"
           f"Interest B = {b}k × {fmt(cf)} = {fmt(b * cf)}k; interest A = {a}k × {t1} × {r}/100 = {fmt(a * Fr(t1 * r, 100))}k.<br>"
           f"Difference: ({fmt(b * cf)} − {fmt(a * Fr(t1 * r, 100))})k = {fmt(coef)}k = {ind(Dv)} → k = {ind(kk)}.<br>"
           + (f"Total = ({a} + {b}) × {ind(kk)} = <b>₹{ind(val)}</b>." if ask_total else f"P₁ = {a} × {ind(kk)} = <b>₹{ind(val)}</b>."))
    wrong = b * kk if not ask_total else a * kk
    return P("Simple and Compound Interest", stem, val, exp, [wrong, val + 2 * kk])


def ar_pipes(rng):
    for _ in range(5000):
        a, b, c = rng.sample([10, 12, 15, 18, 20, 24, 30, 36, 40, 45, 60], 3)
        t = rng.randint(2, 6)
        r_ab = Fr(1, a) + Fr(1, b)
        net = r_ab - Fr(1, c)
        rem = 1 - t * r_ab
        if net <= 0 or rem <= 0:
            continue
        total = t + rem / net
        L = math.lcm(a, b, c)
        units = t * (L // a + L // b)
        assert t + Fr(L - units, L // a + L // b - L // c) == total
        if nice(total, 1) and total <= 40:
            break
    else:
        raise RuntimeError("pipes")
    stem = (f"Two inlet pipes A and B can fill a tank in {a} hours and {b} hours respectively, while an outlet pipe C can empty the full tank in {c} hours. "
            f"A and B are opened together; after {t} hours, C is also opened. In how many hours (from the start) will the tank be completely full?")
    exp = (f"Take tank = {L} units. A fills {L // a}/h, B fills {L // b}/h, C empties {L // c}/h.<br>"
           f"In {t} hours (A + B): {t} × {L // a + L // b} = {units} units. Remaining = {L - units} units.<br>"
           f"Net rate with C open = {L // a} + {L // b} − {L // c} = {L // a + L // b - L // c} units/h → time = {L - units}/{L // a + L // b - L // c} = {fmt(rem / net)} h.<br>"
           f"Total = {t} + {fmt(rem / net)} = <b>{fmt(total)} hours</b>.")
    return P("Time, Work and Pipes", stem, total, exp, [rem / net, Fr(1, 1) / net])


def ar_cycle(rng):
    for _ in range(5000):
        a, b, c = rng.sample([8, 10, 12, 15, 16, 20, 24, 30, 40, 48, 60], 3)
        L = math.lcm(a, b, c)
        rates = [L // a, L // b, L // c]
        done, day = 0, 0
        while True:
            who = day % 3
            if done + rates[who] >= L:
                total = day + Fr(L - done, rates[who])
                break
            done += rates[who]
            day += 1
        cyc = sum(rates)
        q = (L - 1) // cyc
        alt = q * 3
        d2 = q * cyc
        for who in range(3):
            if d2 + rates[who] >= L:
                alt = alt + who + Fr(L - d2, rates[who])
                break
            d2 += rates[who]
        assert alt == total
        if nice(total, 2) and 8 <= total <= 40:
            break
    else:
        raise RuntimeError("cycle")
    names = ["A", "B", "C"]
    stem = (f"A, B and C can complete a piece of work alone in {a}, {b} and {c} days respectively. They work on alternate days in the order A, B, C, A, B, C, … "
            f"starting with A. In how many days will the work be completed?")
    left, day, steps = L - q * cyc, 3 * q, []
    for who in range(3):
        if left <= 0:
            break
        day += 1
        if rates[who] >= left:
            steps.append(f"Day {day} ({names[who]}): needs only {left} of his {rates[who]} units → {fmt(Fr(left, rates[who]))} day")
            left = 0
        else:
            steps.append(f"Day {day} ({names[who]}): {rates[who]} units → {left - rates[who]} left")
            left -= rates[who]
    exp = (f"Work = {L} units; A does {rates[0]}, B does {rates[1]}, C does {rates[2]} units per day.<br>"
           f"One 3-day cycle = {cyc} units. After {q} full cycles ({3 * q} days): {q * cyc} units done, {L - q * cyc} left.<br>"
           + "<br>".join(steps) + f"<br>Total time = <b>{fmt(total)} days</b>.")
    return P("Time and Work", stem, total, exp, [Fr(L, cyc) * 3, Fr(a + b + c, 3)])


def ar_partner(rng):
    while True:
        Pa, Pb = rng.choice([20000, 25000, 30000, 40000, 45000, 50000]), rng.choice([15000, 25000, 30000, 35000, 40000])
        z, x, m = rng.choice([5000, 10000, 15000]), rng.choice([4, 6, 8]), rng.choice([3, 4, 6])
        Pc = rng.choice([30000, 40000, 45000, 50000, 60000])
        ua, ub, uc = Pa * 12, Pb * x + (Pb + z) * (12 - x), Pc * (12 - m)
        g = math.gcd(math.gcd(ua, ub), uc)
        ra, rb, rc = ua // g, ub // g, uc // g
        if ra + rb + rc <= 60:
            break
    mult = rng.choice([250, 300, 400, 500, 600, 750, 800, 1000])
    profit = (ra + rb + rc) * mult
    val = Fr(profit * uc, ua + ub + uc)
    assert val == rc * mult
    stem = (f"A invests ₹{ind(Pa)} for the whole year. B invests ₹{ind(Pb)} and after {x} months adds another ₹{ind(z)}. C joins the business after {m} months "
            f"with ₹{ind(Pc)}. At the end of the year the total profit is ₹{ind(profit)}. What is C's share of the profit (in ₹)?")
    exp = (f"Capital × time: A = {ind(Pa)} × 12 = {ind(ua)}; B = {ind(Pb)} × {x} + {ind(Pb + z)} × {12 - x} = {ind(ub)}; C = {ind(Pc)} × {12 - m} = {ind(uc)}.<br>"
           f"Ratio A:B:C = {ra}:{rb}:{rc}. C's share = {ind(profit)} × {rc}/{ra + rb + rc} = <b>₹{ind(val)}</b>.")
    return P("Partnership", stem, val, exp, [profit * ra // (ra + rb + rc), profit * rb // (ra + rb + rc)])


def ar_pl(rng):
    while True:
        m, d1, d2 = rng.choice([20, 25, 30, 40, 50, 60]), rng.choice([10, 20, 25]), rng.choice([5, 10, 15, 20])
        q = (1 + Fr(m, 100)) * (1 - Fr(d1, 100)) * (1 - Fr(d2, 100)) - 1
        if q <= 0:
            continue
        CP = rng.choice([500, 800, 1000, 1200, 1500, 2000, 2400, 2500, 3000, 4000, 5000])
        prof = CP * q
        if prof.denominator == 1:
            break
    CP2 = prof / q
    MP = CP2 * (1 + Fr(m, 100))
    assert MP == CP * (1 + Fr(m, 100))
    stem = (f"A shopkeeper marks an article {m}% above its cost price and then allows two successive discounts of {d1}% and {d2}%. "
            f"He still earns a profit of ₹{ind(prof)}. What is the marked price of the article (in ₹)?")
    sp_f = (1 + Fr(m, 100)) * (1 - Fr(d1, 100)) * (1 - Fr(d2, 100))
    exp = (f"Let CP = 100. MP = {100 + m}. After {d1}% discount: {fmt(Fr(100 + m) * (100 - d1) / 100)}; after {d2}% more: {fmt(sp_f * 100)}.<br>"
           f"Profit = {fmt(sp_f * 100)} − 100 = {fmt(q * 100)}% of CP → CP = {ind(prof)} × 100/{fmt(q * 100)} = ₹{ind(CP)}.<br>"
           f"MP = {ind(CP)} × {100 + m}% = <b>₹{ind(MP)}</b>.")
    return P("Profit, Loss and Discount", stem, MP, exp, [CP, CP * (1 + Fr(m - d1, 100))])


def ar_ages(rng):
    while True:
        a, b = rng.choice([(3, 2), (5, 4), (7, 5), (4, 3), (5, 3), (8, 5), (9, 7)])
        x = rng.randint(2, 7)
        n = rng.randint(3, 10)
        A, B = a * x, b * x
        c, d = (A + n), (B + n)
        g = math.gcd(c, d)
        c, d = c // g, d // g
        p = rng.randint(3, 9)
        if A - p > 0 and c + d <= 30 and nice(Fr(A + B + (A - p), 3), 2):
            break
    x2 = Fr(n * (c - d), a * d - b * c)
    assert x2 == x
    C = A - p
    val = Fr(A + B + C, 3)
    stem = (f"The present ages of A and B are in the ratio {a}:{b}. After {n} years the ratio of their ages will be {c}:{d}. C is {p} years younger than A. "
            f"What is the average of the present ages of A, B and C (in years)?")
    exp = (f"Let the present ages be {a}x and {b}x. ({a}x + {n})/({b}x + {n}) = {c}/{d} → {d}({a}x + {n}) = {c}({b}x + {n}).<br>"
           f"{a * d}x + {n * d} = {b * c}x + {n * c} → x = {n * (c - d)}/{a * d - b * c} = {x}.<br>"
           f"A = {A}, B = {B}, C = {A} − {p} = {C}. Average = ({A} + {B} + {C})/3 = <b>{fmt(val)}</b>.")
    return P("Ages", stem, val, exp, [Fr(A + B, 2), B, A])


def ar_trains1(rng):
    v = rng.choice([10, 12, 15, 16, 20, 24, 25])
    t1, extra = rng.randint(8, 18), rng.randint(12, 30)
    L, Lp = v * t1, v * extra
    t2 = t1 + extra
    v2 = Fr(Lp, t2 - t1)
    assert v2 == v and v2 * t1 == L
    kmh = v * Fr(18, 5)
    stem = (f"A train crosses a signal pole in {t1} seconds and a platform {Lp} m long in {t2} seconds. What is the length of the train (in metres)?")
    exp = (f"Extra time on the platform = {t2} − {t1} = {extra} s to cover {Lp} m → speed = {Lp}/{extra} = {v} m/s = {fmt(kmh)} km/h.<br>"
           f"Length of train = speed × time to cross the pole = {v} × {t1} = <b>{L} m</b>.")
    return P("Trains", stem, L, exp, [Lp, v * t2])


def ar_trains2(rng):
    while True:
        vA, vB = rng.sample([10, 12, 15, 18, 20, 24, 25, 30], 2)
        tA, tB = rng.randint(6, 15), rng.randint(6, 15)
        LA, LB = vA * tA, vB * tB
        val = Fr(LA + LB, vA + vB)
        if nice(val, 2):
            break
    stem = (f"Train A of length {LA} m crosses a pole in {tA} seconds and train B of length {LB} m crosses the same pole in {tB} seconds. "
            f"If they run on parallel tracks in opposite directions, how many seconds will they take to cross each other completely?")
    exp = (f"Speed of A = {LA}/{tA} = {vA} m/s; speed of B = {LB}/{tB} = {vB} m/s.<br>"
           f"Relative speed (opposite directions) = {vA + vB} m/s; distance = {LA} + {LB} = {LA + LB} m.<br>Time = {LA + LB}/{vA + vB} = <b>{fmt(val)} s</b>.")
    return P("Trains", stem, val, exp, [Fr(LA + LB, abs(vA - vB)), Fr(tA + tB, 2)])


def ar_avg(rng):
    while True:
        n = rng.randint(6, 12)
        A = rng.randint(48, 78)
        inc = rng.choice([Fr(1, 2), Fr(1), Fr(3, 2), Fr(2), Fr(5, 2), Fr(3)])
        w = rng.randint(40, 70)
        w2 = rng.randint(40, 80)
        newtot = n * (A + inc)
        val = (newtot - w2) / (n - 1)
        y = w + n * inc
        if nice(val, 2) and y > 30 and newtot.denominator == 1:
            break
    assert (n * A - w + y) == newtot
    stem = (f"The average weight of {n} players of a team is {A} kg. When a player weighing {w} kg is replaced by a new player, the average weight rises by {fmt(inc)} kg. "
            f"Later, a player weighing {w2} kg leaves the team without being replaced. What is the average weight of the remaining {n - 1} players (in kg)?")
    exp = (f"New total = {n} × ({A} + {fmt(inc)}) = {fmt(newtot)} kg (the new player weighs {w} + {n} × {fmt(inc)} = {fmt(y)} kg).<br>"
           f"After one player leaves: ({fmt(newtot)} − {w2})/{n - 1} = <b>{fmt(val)} kg</b>.")
    return P("Averages", stem, val, exp, [newtot / n, Fr(n * A - w2, n - 1)])


def ar_digits(rng):
    for _ in range(20000):
        N = rng.randint(21, 98)
        a, b = divmod(N, 10)
        if a == b or b == 0:
            continue
        S = a + b
        k = rng.randint(3, 8)
        c = N - k * S
        if not (1 <= abs(c) <= 9):
            continue
        rev = 10 * b + a
        dd = rev - N
        sols = [n for n in range(10, 100)
                if n == k * (n // 10 + n % 10) + c and (10 * (n % 10) + n // 10) - n == dd]
        if sols == [N]:
            break
    else:
        raise RuntimeError("digits")
    want = rng.choice(["product", "squares", "number"])
    val = {"product": a * b, "squares": a * a + b * b, "number": N}[want]
    ask = {"product": "the product of its digits", "squares": "the sum of the squares of its digits", "number": "the number"}[want]
    rel = f"{dd} more than" if dd > 0 else f"{-dd} less than"
    stem = (f"A two-digit number is {abs(c)} {'more' if c > 0 else 'less'} than {k} times the sum of its digits. The number obtained by reversing its digits is {rel} the original number. "
            f"Find {ask}.")
    exp = (f"Let the number be 10p + q. Condition 1: 10p + q = {k}(p + q) {'+' if c > 0 else '−'} {abs(c)} → {10 - k}p {'−' if k - 1 > 0 else '+'} {abs(k - 1)}q = {str(c).replace('-', '−')}.<br>"
           f"Condition 2: (10q + p) − (10p + q) = {dd} → 9(q − p) = {dd} → q − p = {dd // 9}.<br>"
           f"Solving: p = {a}, q = {b}, so the number is {N}." + (f" {ask.capitalize()} = <b>{val}</b>." if want != "number" else f" Required number = <b>{N}</b>.") + f"")
    return P("Number System", stem, val, exp, [N, a + b, a * b + 3])


def ar_wire(rng):
    while True:
        a, b = rng.choice([(3, 2), (4, 3), (5, 3), (7, 4), (5, 6), (9, 2), (8, 3)])
        k = rng.randint(2, 14)
        if (22 * k) % (a + b) == 0:
            break
    wire = 44 * k
    Lr, Br = Fr(22 * k * a, a + b), Fr(22 * k * b, a + b)
    r = Fr(wire * 7, 44)
    circ = Fr(22, 7) * r * r
    val = circ - Lr * Br
    assert r == 7 * k and val.denominator == 1
    stem = (f"A wire of length {wire} cm is first bent into a circle. The same wire is then straightened and bent into a rectangle whose length and breadth are in the ratio {a}:{b}. "
            f"What is the difference between the area of the circle and the area of the rectangle (in cm²)? (Take π = 22/7)")
    exp = (f"Circle: 2πr = {wire} → r = {wire} × 7/44 = {fmt(r)} cm; area = 22/7 × {fmt(r)}² = {fmt(circ)} cm².<br>"
           f"Rectangle: 2(L + B) = {wire} → L + B = {22 * k}; L = {fmt(Lr)}, B = {fmt(Br)}; area = {fmt(Lr * Br)} cm².<br>"
           f"Difference = {fmt(circ)} − {fmt(Lr * Br)} = <b>{fmt(val)} cm²</b>.")
    return P("Mensuration", stem, val, exp, [circ, Lr * Br])


def ar_salary(rng):
    while True:
        X = rng.choice([20000, 24000, 25000, 30000, 32000, 36000, 40000, 48000, 50000])
        p, q = rng.choice([20, 25, 40, 50]), rng.choice([20, 25, 40, 50, 60])
        sa, sb = rng.choice([10, 15, 20, 25, 30]), rng.choice([10, 15, 20, 25, 30])
        Bs = X * (1 - Fr(p, 100))
        As = Bs * (1 + Fr(q, 100))
        savA, savB = As * Fr(sa, 100), Bs * Fr(sb, 100)
        if As.denominator == 1 and savA.denominator == 1 and savB.denominator == 1 and savA != savB:
            break
    diff = abs(savA - savB)
    stem = (f"B's monthly salary is {p}% less than C's, and A's monthly salary is {q}% more than B's. C earns ₹{ind(X)} per month. "
            f"If A saves {sa}% of his salary and B saves {sb}% of his, what is the difference between their monthly savings (in ₹)?")
    exp = (f"B = {ind(X)} × {100 - p}% = ₹{ind(Bs)}; A = {ind(Bs)} × {100 + q}% = ₹{ind(As)}.<br>"
           f"A's saving = {sa}% of {ind(As)} = ₹{ind(savA)}; B's saving = {sb}% of {ind(Bs)} = ₹{ind(savB)}.<br>Difference = <b>₹{ind(diff)}</b>.")
    return P("Percentages", stem, diff, exp, [savA + savB, abs(As - Bs)])


def ar_meet(rng):
    p, q = rng.choice([(1, 2), (2, 3), (3, 4), (2, 5), (3, 5), (4, 5), (1, 3)])
    kk = rng.randint(1, 3)
    tA, tB = q * q * kk, p * p * kk
    t = math.isqrt(tA * tB)
    assert t * t == tA * tB and t == p * q * kk
    val = t + tA
    stem = (f"A and B start at the same time from points P and Q and travel towards each other at constant speeds. After they meet, A takes {tA} hours to reach Q "
            f"and B takes {tB} hours to reach P. How many hours does A take to travel the whole distance from P to Q?")
    exp = (f"If they meet after t hours, then (time A takes after meeting) × (time B takes after meeting) = t². So t = √({tA} × {tB}) = {t} hours.<br>"
           f"Time for A from P to Q = {t} + {tA} = <b>{val} hours</b> (speed ratio A:B = √({tB}/{tA}) = {p}:{q}).")
    return P("Time, Speed and Distance", stem, val, exp, [t, tA + tB])


def ar_prob(rng):
    from math import comb
    while True:
        R, B, G = rng.randint(2, 6), rng.randint(2, 6), rng.randint(2, 5)
        n = R + B + G
        if 10 <= n <= 14:
            break
    tot = comb(n, 3)
    events = {
        "at least one ball is blue": (tot - comb(n - B, 3), f"1 − C({n - B},3)/C({n},3) = 1 − {comb(n - B, 3)}/{tot}"),
        "all three balls are of the same colour": (comb(R, 3) + comb(B, 3) + comb(G, 3), f"[C({R},3) + C({B},3) + C({G},3)]/C({n},3) = ({comb(R, 3)} + {comb(B, 3)} + {comb(G, 3)})/{tot}"),
        "at least two balls are red": (comb(R, 2) * (n - R) + comb(R, 3), f"[C({R},2)×{n - R} + C({R},3)]/C({n},3) = ({comb(R, 2) * (n - R)} + {comb(R, 3)})/{tot}"),
        "exactly one ball of each colour is drawn": (R * B * G, f"({R} × {B} × {G})/C({n},3) = {R * B * G}/{tot}"),
    }
    others = {"no ball is green": comb(n - G, 3), "exactly one ball is red": R * comb(n - R, 2), "exactly two balls are blue": comb(B, 2) * (n - B)}
    name = rng.choice(list(events))
    num, how = events[name]
    right = Fr(num, tot)
    cand, seen = [], {str(right)}
    pool = [Fr(v, tot) for k2, (v, _) in events.items() if k2 != name] + [Fr(v, tot) for v in others.values()]
    rng.shuffle(pool)
    for v in pool:
        if str(v) not in seen and 0 < v < 1:
            seen.add(str(v))
            cand.append(v)
    opts_v = sorted([right] + cand[:4])
    opts = [f"{v.numerator}/{v.denominator}" for v in opts_v]
    stem = (f"A bag contains {R} red, {B} blue and {G} green balls. Three balls are drawn at random without replacement. What is the probability that {name}?")
    exp = f"Total ways = C({n},3) = {tot}.<br>P = {how} = {right.numerator}/{right.denominator}.<br><b>Answer: {right.numerator}/{right.denominator}</b>."
    return dict(topic="Probability", stem=stem, value=right, exp=exp, mistakes=[], custom=(opts, opts_v.index(right)))


ARITH = [ar_boats1, ar_boats2, ar_mixture, ar_interest, ar_pipes, ar_cycle, ar_partner, ar_pl, ar_ages,
         ar_trains1, ar_trains2, ar_avg, ar_digits, ar_wire, ar_salary, ar_meet, ar_prob]
QC_GROUPS = [[ar_interest, ar_pl, ar_salary, ar_partner], [ar_boats2, ar_meet, ar_pipes]]   # same unit within a group


def finish(rng, p):
    if p.get("custom"):
        opts, ans = p["custom"]
        return Q(p["topic"], p["stem"], opts, ans, p["exp"])
    return numq(rng, p["topic"], p["stem"], p["value"], p["exp"], p["mistakes"])


# --------------------------------------------------- data sufficiency / comparison
DS_OPTS = ["Statement I alone is sufficient, but statement II alone is not sufficient.",
           "Statement II alone is sufficient, but statement I alone is not sufficient.",
           "Both statements together are sufficient, but neither statement alone is sufficient.",
           "Each statement alone is sufficient.",
           "Both statements together are not sufficient."]


DS_CTX = {
    "age": dict(
        what="present age", unit="years",
        total=lambda s: f"The sum of the present ages of A and B is {s} years.",
        ratio=lambda p, q: f"The ratio of A's present age to B's present age is {p}:{q}.",
        diff=lambda d: f"A is {d} years older than B.",
        pct=lambda p: f"A's present age is {p}% more than B's present age.",
        fut=lambda n, v: f"After {n} years, A will be {v} years old.",
        past=lambda n, v: f"{n} years ago, B was {v} years old.",
        askA="What is A's present age (in years)?", askB="What is B's present age (in years)?",
        askR="What is the ratio of A's present age to B's present age?"),
    "weight": dict(
        what="weight", unit="kg",
        total=lambda s: f"The total weight of A and B is {s} kg.",
        ratio=lambda p, q: f"The ratio of A's weight to B's weight is {p}:{q}.",
        diff=lambda d: f"A is {d} kg heavier than B.",
        pct=lambda p: f"A's weight is {p}% more than B's weight.",
        fut=lambda n, v: f"If A gains {n} kg, A's weight becomes {v} kg.",
        past=lambda n, v: f"If B loses {n} kg, B's weight becomes {v} kg.",
        askA="What is A's weight (in kg)?", askB="What is B's weight (in kg)?",
        askR="What is the ratio of A's weight to B's weight?"),
    "savings": dict(
        what="savings", unit="₹ thousand",
        total=lambda s: f"The total savings of A and B is ₹{s} thousand.",
        ratio=lambda p, q: f"The ratio of A's savings to B's savings is {p}:{q}.",
        diff=lambda d: f"A's savings exceed B's savings by ₹{d} thousand.",
        pct=lambda p: f"A's savings are {p}% more than B's savings.",
        fut=lambda n, v: f"If A saves ₹{n} thousand more, A's savings become ₹{v} thousand.",
        past=lambda n, v: f"If B spends ₹{n} thousand from savings, B's savings become ₹{v} thousand.",
        askA="What is A's savings (in ₹ thousand)?", askB="What is B's savings (in ₹ thousand)?",
        askR="What is the ratio of A's savings to B's savings?"),
}


def ds_question(rng, want):
    ctx = DS_CTX[rng.choice(list(DS_CTX))]
    grid = [(a, b) for a in range(1, 131) for b in range(1, 131)]
    for _ in range(30000):
        ra, rb = rng.choice([(2, 3), (3, 2), (4, 3), (5, 3), (3, 5), (5, 4), (7, 4), (5, 2), (7, 5), (8, 5), (9, 5)])
        g = rng.randint(2, 9)
        A, B = ra * g, rb * g
        n = rng.choice([3, 4, 5, 6, 8, 10])
        stmts = [(ctx["total"](A + B), lambda a, b, s=A + B: a + b == s),
                 (ctx["ratio"](ra, rb), lambda a, b, p=ra, q=rb: a * q == b * p)]
        if A > B:
            stmts.append((ctx["diff"](A - B), lambda a, b, d=A - B: a - b == d))
            pc = Fr((A - B) * 100, B)
            if pc.denominator == 1:
                stmts.append((ctx["pct"](pc.numerator), lambda a, b, p=pc.numerator: 100 * a == (100 + p) * b))
        stmts.append((ctx["fut"](n, A + n), lambda a, b, n=n, v=A + n: a + n == v))
        if B > n:
            stmts.append((ctx["past"](n, B - n), lambda a, b, n=n, v=B - n: b - n == v))
        s1, s2 = rng.sample(stmts, 2)
        tk = rng.choice(["A", "B", "ratio"])
        if tk == "A":
            qtxt, f = ctx["askA"], lambda a, b: a
        elif tk == "B":
            qtxt, f = ctx["askB"], lambda a, b: b
        else:
            qtxt, f = ctx["askR"], lambda a, b: Fr(a, b)

        def vals(preds):
            return {f(a, b) for a, b in grid if all(p(a, b) for p in preds)}
        v1, v2, v12 = vals([s1[1]]), vals([s2[1]]), vals([s1[1], s2[1]])
        suf1, suf2, suf12 = len(v1) == 1, len(v2) == 1, len(v12) == 1
        if suf1 and suf2:
            code = 3
        elif suf1:
            code = 0
        elif suf2:
            code = 1
        elif suf12:
            code = 2
        else:
            code = 4
        if code != want:
            continue

        def show(v):
            return fmt(v) if tk != "ratio" else f"{v.numerator}:{v.denominator}"

        def desc(name, vs, suf):
            if suf:
                return f"{name} alone gives a single value ({show(next(iter(vs)))}) → sufficient."
            ex = ", ".join(show(v) for v in sorted(vs)[:3])
            return f"{name} alone allows several values (e.g. {ex}) → not sufficient."
        exp = (desc("Statement I", v1, suf1) + "<br>" + desc("Statement II", v2, suf2) + "<br>"
               + (f"Together: a single value ({show(next(iter(v12)))}) → sufficient." if suf12 else "Together: still more than one possible value → not sufficient.")
               + f"<br><b>Answer: {DS_OPTS[code]}</b>")
        q = f"{qtxt}\nStatement I: {s1[0]}\nStatement II: {s2[0]}"
        return Q("Data Sufficiency", "Directions: Each question is followed by two statements. Decide whether the data given is sufficient to answer the question.\n" + q, DS_OPTS, code, exp)
    raise RuntimeError("ds " + str(want))


QC_OPTS = ["Quantity I > Quantity II", "Quantity I ≥ Quantity II", "Quantity I < Quantity II", "Quantity I ≤ Quantity II",
           "Quantity I = Quantity II or the relation cannot be established"]


def qc_question(rng, want):
    for _ in range(500):
        f1, f2 = rng.sample(rng.choice(QC_GROUPS), 2)
        p1, p2 = f1(rng), f2(rng)
        v1, v2 = p1["value"], p2["value"]
        code = 0 if v1 > v2 else (2 if v1 < v2 else 4)
        if code != want:
            continue
        q = ("Directions: Two quantities are given. Compute both and choose the correct relation.\n"
             f"Quantity I: {p1['stem']}\nQuantity II: {p2['stem']}")
        exp = (f"<b>Quantity I:</b> {p1['exp']}<br><b>Quantity II:</b> {p2['exp']}<br>"
               f"Quantity I = {fmt(v1)} and Quantity II = {fmt(v2)} → <b>{QC_OPTS[code]}</b>.")
        return Q("Quantity Comparison", q, QC_OPTS, code, exp)
    raise RuntimeError("qc")


# ---------------------------------------------------------------- assembly
def build_test(exam, t):
    rng = random.Random(f"scorefree-mains-quant-{exam}-{t}")
    sbi = exam == "sbi"
    out = []
    out += build_quadratics(rng, 5)
    out += [series_missing(rng), series_missing(rng), series_missing(rng), series_wrong(rng), series_wrong(rng)]
    di_n = 4 if sbi else 3
    for i in range(di_n):
        fn = DI_BUILDERS[(t + i * 2 + (1 if sbi else 0)) % len(DI_BUILDERS)]
        title, intro, qs = fn(rng)
        for q in qs:
            q["setTitle"], q["setIntro"] = title, intro
        out += qs
    pool = ARITH + [approx_question]
    pick = rng.sample(pool, 15 if sbi else 10)
    for fn in pick:
        if fn is approx_question:
            out.append(approx_question(rng))
        else:
            out.append(finish(rng, fn(rng)))
    if sbi:
        wants = [0, 1, 2, 3, 4]
        rng.shuffle(wants)
        out += [ds_question(rng, w) for w in wants[:3]]
        out += [qc_question(rng, w) for w in rng.sample([0, 2, 4], 2)]
    assert len(out) == (SBI_Q if sbi else IBPS_Q), len(out)
    seen = set()
    for q in out:
        key = (q["q"], q.get("setTitle", ""))
        assert key not in seen, "duplicate question " + q["q"][:60]
        seen.add(key)
        assert len(q["opts"]) == 5 and len(set(q["opts"])) == 5 and 0 <= q["ans"] < 5 and q["exp"]
    return out


def main():
    bank = {e: {t: build_test(e, t) for t in range(1, 11)} for e in ("ibps", "sbi")}
    sets = []
    for e in bank:                                  # store each shared set intro once
        for t in bank[e]:
            for q in bank[e][t]:
                if q.get("setIntro"):
                    key = (q.pop("setTitle"), q.pop("setIntro"))
                    if key not in sets:
                        sets.append(key)
                    q["s"] = sets.index(key)
    js = ("/* ScoreFree original Mains-level Quantitative Aptitude bank.\n"
          "   GENERATED by tools/build_mains_quant.py - edit the generator, not this file.\n"
          "   Replaces SF_BANK.<exam>.quant[1..10] so earlier basic practice items never mix into Mains tests. */\n"
          "(function(){\n  if(!window.SF_BANK) return;\n  var S=" + json.dumps(sets, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "  var B=" + json.dumps(bank, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "  ['ibps','sbi'].forEach(function(e){for(var t=1;t<=10;t++){B[e][t].forEach(function(q){if(q.s!==undefined){q.setTitle=S[q.s][0];q.setIntro=S[q.s][1];delete q.s;}});SF_BANK[e].quant[t]=B[e][t];}});\n})();\n")
    OUT.write_text(js, encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT), f"({len(js) // 1024} KB, {len(sets)} shared data sets)")
    for e in bank:
        print(e, {t: len(v) for t, v in bank[e].items()})


if __name__ == "__main__":
    main()
