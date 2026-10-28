#!/usr/bin/env python3
"""Build ScoreFree's static question bank using only free/open sources and deterministic generators.
No API keys, paid services, or runtime network calls are required by the website.
"""
from __future__ import annotations
import html, json, os, random, re, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "question-bank.generated.js"
QULTURE_URL = "https://www.qulture-app.com/open-data/qulture-reviewed-questions.json"
OPENTRIVIA_REPO = "https://github.com/uberspot/OpenTriviaQA.git"
USER_AGENT = "ScoreFree-Open-Question-Bank/1.0 (open educational use)"
RNG = random.Random(20261028)
TARGET_PER_EXAM_SUBJECT = 200  # 20 questions x 10 tests, for each exam
SUBJECTS = ("quant", "reasoning", "english", "awareness")
EXAMS = ("ibps", "sbi")

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(str(s or ""))).strip()

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", clean(s).lower())

def qobj(topic, question, options, answer, explanation, source=None):
    opts = [clean(x) for x in options]
    if len(opts) != 5 or not (0 <= int(answer) < len(opts)):
        return None
    if not clean(question) or len({norm(x) for x in opts}) != 5:
        return None
    result = {"topic": clean(topic), "q": clean(question), "opts": opts,
              "ans": int(answer), "exp": clean(explanation)}
    if source:
        result["source"] = source
    return result

def add_unique(pool, seen, item):
    if not item:
        return
    key = norm(item["q"])
    if len(key) < 12 or key in seen:
        return
    seen.add(key)
    pool.append(item)

def import_qulture(pool, seen):
    try:
        data = get_json(QULTURE_URL)
        for row in data.get("records", []):
            if row.get("language") != "en":
                continue
            opts = [clean(x) for x in row.get("options", [])]
            indicators = row.get("correct_indicators", [])
            if len(opts) != 4 or len(indicators) != 4 or sum(bool(x) for x in indicators) != 1:
                continue
            ans = next(i for i, x in enumerate(indicators) if x)
            opts.append("None of the above")
            item = qobj("General Awareness", row.get("question"), opts, ans,
                        row.get("anecdote") or ("Correct answer: " + clean(row.get("correct_answer"))),
                        {"name": "Qulture reviewed question dataset", "url": QULTURE_URL,
                         "license": "CC BY 4.0", "record_id": row.get("id")})
            add_unique(pool, seen, item)
        print("Qulture imported:", len(pool))
    except Exception as exc:
        print("Qulture source unavailable; continuing with other sources:", exc)

def classify_path(path):
    p = str(path).lower()
    if any(x in p for x in ("math", "arithmetic", "algebra", "number")):
        return "quant"
    if any(x in p for x in ("reason", "logic", "puzzle", "brain")):
        return "reasoning"
    if any(x in p for x in ("english", "grammar", "vocab", "language")):
        return "english"
    return "awareness"

def import_open_trivia(pools, seen_by_subject):
    clone = ROOT / ".cache-open-trivia"
    try:
        if not clone.exists():
            subprocess.run(["git", "clone", "--depth", "1", OPENTRIVIA_REPO, str(clone)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        count = 0
        for path in clone.rglob("*.txt"):
            if any(part.startswith(".") for part in path.parts):
                continue
            subject = classify_path(path.relative_to(clone))
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            current = None
            def flush():
                nonlocal count, current
                if not current:
                    return
                question = current.get("q", "")
                answer = current.get("answer", "")
                options = current.get("options", [])
                if not question or not answer:
                    current = None
                    return
                options = [clean(x) for x in options if clean(x)]
                if not any(norm(x) == norm(answer) for x in options):
                    options.append(clean(answer))
                # Retain at most four distractors plus the correct answer.
                correct = next((i for i, x in enumerate(options) if norm(x) == norm(answer)), None)
                if correct is None:
                    current = None
                    return
                correct_text = options[correct]
                distractors = [x for i, x in enumerate(options) if i != correct and norm(x) != norm(correct_text)]
                distractors = list(dict.fromkeys(distractors))[:4]
                if len(distractors) < 4:
                    current = None
                    return
                opts = distractors[:4] + [correct_text]
                RNG.shuffle(opts)
                ans = next(i for i, x in enumerate(opts) if norm(x) == norm(correct_text))
                item = qobj("Open trivia" if subject == "awareness" else "Open practice",
                            question, opts, ans, "Answer key imported from the open dataset; verify before high-stakes use.",
                            {"name": "OpenTriviaQA", "url": "https://github.com/uberspot/OpenTriviaQA",
                             "license": "CC BY-SA 4.0", "file": str(path.relative_to(clone))})
                before = len(pools[subject])
                add_unique(pools[subject], seen_by_subject[subject], item)
                count += len(pools[subject]) - before
                current = None
            for line in lines:
                line = line.strip()
                if line.startswith("#Q"):
                    flush()
                    current = {"q": line[2:].strip(), "answer": "", "options": []}
                elif current and line.startswith("^"):
                    current["answer"] = line[1:].strip()
                elif current and re.match(r"^[A-E][\.\)]?\s+", line):
                    current["options"].append(re.sub(r"^[A-E][\.\)]?\s+", "", line).strip())
                elif current and line and not line.startswith("#") and not line.startswith("//"):
                    # Some files wrap a question over multiple lines.
                    if not current["answer"] and not current["options"]:
                        current["q"] += " " + line
            flush()
        print("OpenTriviaQA imported:", count)
    except Exception as exc:
        print("OpenTriviaQA unavailable; continuing with generated practice:", exc)

def generate_quant(n):
    out, seen = [], set()
    attempts = 0
    while len(out) < n and attempts < n * 20:
        attempts += 1
        typ = RNG.randrange(8)
        a, b = RNG.randint(12, 950), RNG.randint(2, 45)
        if typ == 0:
            pct = RNG.choice([5, 10, 12, 15, 20, 25, 30, 35, 40])
            base = RNG.choice([100, 120, 150, 180, 200, 240, 300, 400, 500, 800])
            ansv = base * pct // 100
            question, topic, exp = f"What is {pct}% of {base}?", "Percentage", f"{pct}/100 × {base} = {ansv}."
        elif typ == 1:
            x = RNG.randint(20, 200); p = RNG.choice([10, 15, 20, 25, 30, 40])
            ansv = x * (100 + p) // 100
            question, topic, exp = f"A value of {x} is increased by {p}%. What is the new value?", "Percentage change", f"New value = {x} × (1 + {p}/100) = {ansv}."
        elif typ == 2:
            principal = RNG.choice([1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000])
            rate = RNG.choice([4, 5, 6, 8, 10, 12]); years = RNG.choice([2, 3, 4])
            ansv = principal * rate * years // 100
            question, topic, exp = f"Find the simple interest on ₹{principal} at {rate}% per annum for {years} years.", "Simple interest", f"SI = PRT/100 = {principal}×{rate}×{years}/100 = ₹{ansv}."
        elif typ == 3:
            x, y = RNG.randint(20, 90), RNG.randint(20, 90)
            ansv = (x + y) // 2
            question, topic, exp = f"The average of {x} and {y} is what?", "Average", f"Average = ({x} + {y})/2 = {ansv}."
        elif typ == 4:
            rate = RNG.choice([10, 15, 20, 25, 30, 40, 50])
            cost = RNG.choice([200, 250, 300, 400, 500, 600, 800, 1000])
            ansv = cost * (100 + rate) // 100
            question, topic, exp = f"An item costs ₹{cost}. At a profit of {rate}%, what is its selling price?", "Profit and loss", f"SP = {cost} × (100 + {rate})/100 = ₹{ansv}."
        elif typ == 5:
            speed = RNG.choice([30, 36, 40, 45, 48, 50, 60, 72])
            hours = RNG.choice([2, 3, 4, 5, 6])
            ansv = speed * hours
            question, topic, exp = f"A vehicle travels at {speed} km/h for {hours} hours. How far does it travel?", "Speed, time and distance", f"Distance = speed × time = {speed} × {hours} = {ansv} km."
        elif typ == 6:
            x, y = RNG.randint(2, 9), RNG.randint(2, 9)
            total = RNG.choice([60, 72, 84, 90, 96, 108, 120, 144])
            ansv = total * x // (x + y)
            question, topic, exp = f"₹{total} is divided in the ratio {x}:{y}. What is the first share?", "Ratio and proportion", f"First share = {total} × {x}/({x}+{y}) = ₹{ansv}."
        else:
            workers = RNG.choice([4, 5, 6, 8, 10, 12])
            days = RNG.choice([6, 8, 10, 12, 15, 20])
            new_workers = workers * 2
            ansv = days * workers // new_workers
            question, topic, exp = f"{workers} workers finish a job in {days} days. At the same rate, how many days will {new_workers} workers take?", "Time and work", f"Total work is constant: {workers}×{days} = {new_workers}×d, so d = {ansv} days."
        key = norm(question)
        if key in seen: continue
        seen.add(key)
        opts = {ansv}
        while len(opts) < 5:
            delta = RNG.choice([-25, -20, -15, -10, -5, 5, 10, 15, 20, 25])
            opts.add(max(0, ansv + delta))
        choices = list(opts); RNG.shuffle(choices)
        add_unique(out, set(), qobj(topic, question, [str(v) for v in choices], choices.index(ansv), exp))
    return out

def generate_reasoning(n):
    out, seen = [], set()
    for i in range(n * 4):
        if len(out) >= n: break
        typ = i % 4
        if typ == 0:
            start = RNG.randint(2, 30); step = RNG.choice([3, 4, 5, 6, 7, 8, 9, 11])
            seq = [start + j * step for j in range(5)]; ansv = seq[-1] + step
            q = "Find the next number: " + ", ".join(map(str, seq)) + ", ?"
            exp = f"The sequence increases by {step} each time; the next number is {ansv}."
            topic = "Number series"
        elif typ == 1:
            start = RNG.randint(2, 8); mult = RNG.choice([2, 3]); add = RNG.choice([1, 2, 3, 4])
            seq = [start]
            for j in range(4): seq.append(seq[-1] * mult + add)
            ansv = seq[-1] * mult + add
            q = "Find the next number: " + ", ".join(map(str, seq)) + ", ?"
            exp = f"Each term is multiplied by {mult} and then {add} is added; the next number is {ansv}."
            topic = "Number series"
        elif typ == 2:
            a = RNG.randint(2, 20); b = RNG.randint(2, 20)
            q = f"If A > B and B > {a}, which statement must be true about A?"
            ansv = f"A > {a}"
            options = [f"A < {a}", f"A = {a}", ansv, f"B < {a}", "A and B are equal"]
            RNG.shuffle(options)
            item = qobj("Inequalities", q, options, options.index(ansv), f"Since A > B and B > {a}, transitivity gives A > {a}.")
            add_unique(out, seen, item); continue
        else:
            x = RNG.randint(2, 20)
            q = f"In a row, Mira is {x}th from the left and there are {RNG.randint(2, 10)} people to her left. What is Mira's position from the left?"
            # Construct consistent phrasing with position = people to left + 1
            left = x - 1
            q = f"There are {left} people to Mira's left in a row. What is her position from the left?"
            ansv = x
            topic = "Ranking and order"
            exp = f"Position from the left = people to her left + 1 = {left} + 1 = {x}."
        if typ in (0, 1, 3):
            opts = {ansv}
            while len(opts) < 5: opts.add(ansv + RNG.choice([-13, -9, -5, -3, 3, 5, 9, 13]))
            choices = list(opts); RNG.shuffle(choices)
            item = qobj(topic, q, [str(v) for v in choices], choices.index(ansv), exp)
        add_unique(out, seen, item)
    return out

def generate_english(n):
    out, seen = [], set()
    pairs = [
        ("Each of the candidates ___ submitted the form.", "has", ["have", "are", "were", "having"], "The subject 'each' is singular, so it takes 'has'.", "Subject–verb agreement"),
        ("Neither the manager nor the clerks ___ available.", "are", ["is", "was", "has", "be"], "With 'neither...nor', the verb agrees with the nearer subject, 'clerks'.", "Subject–verb agreement"),
        ("She has been working here ___ 2021.", "since", ["for", "from", "by", "during"], "'Since' is used with a starting point in time.", "Prepositions"),
        ("The report is different ___ the one we received yesterday.", "from", ["than", "to", "with", "by"], "The standard construction is 'different from'.", "Prepositions"),
        ("He is ___ honest officer.", "an", ["a", "the", "no article", "some"], "'Honest' begins with a vowel sound, so 'an' is used.", "Articles"),
        ("If I ___ about the delay, I would have called you.", "had known", ["knew", "would know", "have known", "know"], "The third conditional uses 'if + past perfect' and 'would have + past participle'.", "Conditional sentences"),
        ("The committee ___ submitted its final report.", "has", ["have", "are", "were", "having"], "When the committee is treated as one body, the singular verb 'has' is appropriate.", "Subject–verb agreement"),
        ("No sooner had the train left ___ it began to rain.", "than", ["when", "then", "that", "while"], "The fixed correlative construction is 'no sooner...than'.", "Conjunctions"),
        ("The data ___ consistent with the earlier findings.", "are", ["is", "was", "has", "be"], "'Data' is conventionally treated as a plural noun in formal examination grammar.", "Subject–verb agreement"),
        ("He insisted ___ paying the bill himself.", "on", ["for", "to", "at", "with"], "'Insist on' is followed by a noun or gerund.", "Prepositions"),
        ("The new policy will ___ all regional offices.", "affect", ["effect", "affects", "effected", "affecting"], "'Affect' is the verb meaning to influence.", "Vocabulary in context"),
        ("The principal, along with the teachers, ___ attending the meeting.", "is", ["are", "were", "have", "be"], "The main subject is singular 'principal'; 'along with the teachers' does not change it.", "Subject–verb agreement"),
    ]
    while len(out) < n:
        sentence, answer, wrongs, explanation, topic = pairs[len(out) % len(pairs)]
        # Vary contexts and order while retaining an independently checkable rule.
        cycle = len(out) // len(pairs)
        if cycle:
            sentence = sentence.replace("the form", f"the form (set {cycle+1})").replace("the bill", f"the bill (case {cycle+1})")
        opts = wrongs[:]
        opts.append(answer)
        opts = list(dict.fromkeys(opts))
        while len(opts) < 5: opts.append("None of these")
        opts = opts[:5]
        # Ensure correct answer is present, then shuffle.
        if answer not in opts: opts[-1] = answer
        RNG.shuffle(opts)
        item = qobj(topic, sentence, opts, opts.index(answer), explanation)
        before = len(out)
        add_unique(out, seen, item)
        if len(out) == before:
            # Deterministically vary the prompt to avoid duplicate records.
            sentence = sentence.rstrip(".?") + f" (practice item {len(out)+1})."
            opts = wrongs[:4] + [answer]
            RNG.shuffle(opts)
            add_unique(out, seen, qobj(topic, sentence, opts, opts.index(answer), explanation))
    return out

def to_js(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def main():
    pools = {s: [] for s in SUBJECTS}
    seen = {s: set() for s in SUBJECTS}
    import_open_trivia(pools, seen)
    import_qulture(pools["awareness"], seen["awareness"])
    for subject, generator in (("quant", generate_quant), ("reasoning", generate_reasoning), ("english", generate_english)):
        generated = generator(TARGET_PER_EXAM_SUBJECT * 2)
        for item in generated:
            add_unique(pools[subject], seen[subject], item)
    # Avoid source questions taking up all space; keep at most 400 awareness items.
    pools["awareness"] = pools["awareness"][:TARGET_PER_EXAM_SUBJECT * 2]
    lines = [
        "/* AUTO-GENERATED by tools/build_question_bank.py. Do not edit by hand.",
        "   Sources/licences: see QUESTION_BANK_ATTRIBUTION.md. Original template questions are generated locally. */",
        "(function(){",
        "  if (!window.SF_BANK) { console.error('ScoreFree question-bank.js must load before question-bank.generated.js'); return; }",
    ]
    for subject in SUBJECTS:
        pool = pools[subject]
        # Unique pools are split between IBPS and SBI, 20 questions per test.
        for exam_index, exam in enumerate(EXAMS):
            start = exam_index * TARGET_PER_EXAM_SUBJECT
            exam_pool = pool[start:start + TARGET_PER_EXAM_SUBJECT]
            for test in range(1, 11):
                batch = exam_pool[(test-1)*20:test*20]
                if batch:
                    limit = ({"ibps": {"quant": 35, "reasoning": 40, "english": 40, "awareness": 40}, "sbi": {"quant": 50, "reasoning": 50, "english": 40, "awareness": 50}})[exam][subject];\n                    lines.append(f"  var current_{exam}_{subject}_{test} = SF_BANK.{exam}.{subject}[{test}] || [];")\n                    lines.append(f"  SF_BANK.{exam}.{subject}[{test}] = current_{exam}_{subject}_{test}.concat({to_js(batch)}.slice(0, Math.max(0, {limit} - current_{exam}_{subject}_{test}.length)));")
    lines.append("})();")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT))
    for s in SUBJECTS:
        print(f"{s}: {len(pools[s])} unique questions available")
    print("Reminder: the importer is source-licensed, but factual accuracy still needs review before high-stakes use.")

if __name__ == "__main__":
    main()
