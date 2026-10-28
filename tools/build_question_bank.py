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
        for path in (clone / "categories").rglob("*"):
            if not path.is_file() or path.suffix.lower() in (".py", ".json", ".db", ".csv", ".rb"):
                continue
            if any(part.startswith(".") for part in path.relative_to(clone).parts):
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
                # OpenTriviaQA commonly supplies four choices including the answer.
                # Add a neutral fifth option in that case; never invent a new answer.
                if len(options) == 4 and any(norm(x) == norm(answer) for x in options):
                    options.append("None of the above")
                correct = next((i for i, x in enumerate(options) if norm(x) == norm(answer)), None)
                if correct is None:
                    current = None
                    return
                # Preserve the source's choices and correct answer, capped at five.
                if len(options) > 5:
                    correct_text = options[correct]
                    options = [x for x in options if norm(x) != norm(correct_text)][:4] + [correct_text]
                if len(options) != 5 or len({norm(x) for x in options}) != 5:
                    current = None
                    return
                opts = options[:]
                RNG.shuffle(opts)
                ans = next(i for i, x in enumerate(opts) if norm(x) == norm(answer))
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
        typ = i % 7
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
        elif typ == 3:
            x = RNG.randint(2, 20)
            left = x - 1
            person = RNG.choice(["Mira", "Rohan", "Kavya", "Arjun", "Neha", "Aman", "Priya", "Dev"])
            q = f"There are {left} people to {person}'s left in a row. What is {person}'s position from the left?"
            ansv = x
            topic = "Ranking and order"
            exp = f"Position from the left = people to the left + 1 = {left} + 1 = {x}."
        elif typ == 4:
            east, north = RNG.choice([(3,4),(5,12),(6,8),(8,15),(7,24),(9,12),(12,16)])
            ansv = int((east*east+north*north) ** 0.5)
            q = f"A person walks {east} m east and then {north} m north. What is the straight-line distance from the starting point?"
            topic = "Direction and distance"
            exp = f"By Pythagoras, distance = √({east}² + {north}²) = {ansv} m."
        elif typ == 5:
            word = RNG.choice(["BANK", "LOAN", "RISK", "CASH", "RATE", "FUND", "CREDIT", "DEBIT", "MONEY", "TRADE"])
            shift = RNG.choice([1, 2, 3])
            ansv = "".join(chr((ord(ch)-65+shift)%26+65) for ch in word)
            q = f"If each letter is moved {shift} place(s) forward in the alphabet, how is {word} coded?"
            topic = "Coding-decoding"
            exp = f"Move each letter forward by {shift}: {word} becomes {ansv}."
        elif typ == 6:
            x = RNG.randint(10, 90)
            q = f"Statements: A > B, B > {x}. Which conclusion follows?"
            ansv = f"A > {x}"
            options = [ansv, f"A < {x}", f"A = {x}", f"B < {x}", "A and B are equal"]
            RNG.shuffle(options)
            item = qobj("Inequalities", q, options, options.index(ansv), f"Since A > B and B > {x}, A > {x} by transitivity.")
            add_unique(out, seen, item)
            continue
        if typ in (0, 1, 3, 4):
            opts = {ansv}
            while len(opts) < 5: opts.add(ansv + RNG.choice([-13, -9, -5, -3, 3, 5, 9, 13]))
            choices = list(opts); RNG.shuffle(choices)
            item = qobj(topic, q, [str(v) for v in choices], choices.index(ansv), exp)
        elif typ == 5:
            wrongs = set()
            while len(wrongs) < 4:
                candidate = "".join(chr((ord(ch)-65+RNG.choice([shift-1, shift+1, shift+2]))%26+65) for ch in word)
                if candidate != ansv: wrongs.add(candidate)
            choices = list(wrongs) + [ansv]; RNG.shuffle(choices)
            item = qobj(topic, q, choices, choices.index(ansv), exp)
        add_unique(out, seen, item)
    return out

def generate_english(n):
    out, seen = [], set()
    contexts = [
        ["candidates", "applicants", "trainees", "officers", "students", "participants", "employees", "customers", "clerks", "analysts", "volunteers", "inspectors", "cashiers", "supervisors", "interns", "delegates", "members", "auditors", "managers", "researchers"],
        ["clerks", "officers", "agents", "assistants", "candidates", "tellers", "analysts", "cashiers", "supervisors", "inspectors", "auditors", "trainees", "employees", "managers", "members", "delegates", "volunteers", "reviewers", "consultants", "representatives"],
        [str(y) for y in range(2005, 2025)],
        ["recruitment", "verification", "account opening", "loan processing", "customer service", "risk review", "data entry", "branch operations", "cash management", "staff training", "compliance checks", "document review", "payment settlement", "audit planning", "record keeping", "fraud monitoring", "credit assessment", "complaint handling", "digital onboarding", "report preparation"],
        ["honest", "honourable", "hourly", "unusual", "experienced", "eligible", "efficient", "important", "accurate", "optimistic", "educated", "innovative", "independent", "alert", "ethical", "impartial", "organised", "effective", "unavailable", "unreliable"],
        ["the schedule", "the warning", "the instruction", "the revised policy", "the email", "the circular", "the deadline", "the change", "the notice", "the message", "the update", "the new rule", "the request", "the alert", "the correction", "the reminder", "the announcement", "the instruction manual", "the revised timetable", "the supervisor's advice"],
        ["committee", "board", "panel", "council", "team", "jury", "task force", "selection panel", "review committee", "finance board", "audit committee", "advisory council", "working group", "management team", "ethics committee", "steering committee", "executive board", "assessment panel", "planning committee", "disciplinary board"],
        ["training session", "morning briefing", "review meeting", "orientation", "interview", "presentation", "conference", "workshop", "inspection", "audit", "seminar", "staff meeting", "announcement", "demonstration", "webinar", "negotiation", "consultation", "hearing", "lecture", "discussion"],
        ["the survey", "customer feedback", "the audit", "the interviews", "the field study", "the inspection", "the questionnaire", "the assessment", "the review", "the experiment", "the branch visits", "the report", "the observation", "the pilot project", "the trial", "the interviews", "the records", "the sample", "the analysis", "the evaluation"],
        ["the totals", "the balance sheet", "the ledger", "the cash flow", "the transaction log", "the annual report", "the statement", "the spreadsheet", "the reconciliation", "the account entries", "the invoices", "the loan schedule", "the audit trail", "the payment file", "the daily figures", "the monthly summary", "the register", "the receipts", "the records", "the final calculation"],
        ["reduce delays", "improve access", "support customers", "protect records", "simplify payments", "strengthen controls", "improve reporting", "reduce errors", "support branches", "speed up verification", "protect deposits", "improve service", "reduce costs", "support lending", "improve accuracy", "prevent fraud", "support onboarding", "improve compliance", "reduce paperwork", "strengthen security"],
        ["principal", "director", "manager", "supervisor", "auditor", "accountant", "officer", "chairperson", "secretary", "treasurer", "coordinator", "registrar", "inspector", "controller", "administrator", "team leader", "branch head", "examiner", "reviewer", "consultant"],
        ["the first draft", "the previous quarter", "the original report", "last year's figures", "the earlier version", "the previous audit", "the old procedure", "the initial proposal", "the first estimate", "the prior statement", "the earlier record", "the original schedule", "the former policy", "the first submission", "the earlier forecast", "the previous plan", "the initial result", "the first calculation", "the old register", "the earlier document"],
        ["the three teams", "the regional offices", "the five departments", "the two branches", "the project groups", "the review panels", "the working units", "the field officers", "the support desks", "the audit teams", "the partner banks", "the service counters", "the shortlisted applicants", "the local committees", "the three vendors", "the project members", "the supervisors", "the clerical staff", "the branch managers", "the training groups"],
        ["heavy workload", "unexpected delays", "limited resources", "staff shortages", "technical problems", "tight schedule", "poor weather", "several interruptions", "late start", "system downtime", "difficult audit", "large backlog", "last-minute changes", "transport strike", "uncertain data", "demanding client", "equipment failure", "multiple revisions", "power cut", "competing deadlines"],
        ["the opening session", "the morning briefing", "the audit", "the interview", "the training", "the presentation", "the review", "the inspection", "the conference", "the workshop", "the examination", "the negotiation", "the hearing", "the demonstration", "the webinar", "the staff meeting", "the orientation", "the discussion", "the consultation", "the assessment"],
        ["the application", "the final report", "the figures", "the checklist", "the contract", "the ledger", "the draft", "the proposal", "the minutes", "the statement", "the schedule", "the payment file", "the account", "the summary", "the record", "the form", "the notice", "the spreadsheet", "the submission", "the invoice"],
        ["manage", "supervise", "audit", "inspect", "operate", "review", "monitor", "coordinate", "maintain", "verify", "process", "examine", "handle", "support", "approve", "prepare", "update", "reconcile", "evaluate", "record"],
        ["the policy change", "the recruitment drive", "the service launch", "the new branch", "the online portal", "the revised process", "the public notice", "the payment facility", "the training programme", "the digital campaign", "the customer helpline", "the new circular", "the updated form", "the revised deadline", "the merger", "the awareness drive", "the new scheme", "the branch relocation", "the mobile app", "the revised guidelines"],
        ["the disputed transaction", "the incomplete form", "the audit finding", "the delay", "the missing document", "the complaint", "the mismatch", "the revised estimate", "the payment issue", "the data gap", "the error", "the discrepancy", "the pending request", "the failed transfer", "the unexpected result", "the unusual entry", "the shortfall", "the system alert", "the incorrect total", "the unresolved case"],
    ]
    templates = [
        ("Each of the {v} ___ completed the application.", "has", ["have", "are", "were", "having"], "The subject 'each' is singular, so it takes 'has'.", "Subject–verb agreement", 0),
        ("Neither the supervisor nor the {v} ___ available for the audit.", "are", ["is", "was", "has", "be"], "With 'neither...nor', the verb agrees with the nearer subject, which is plural here.", "Subject–verb agreement", 1),
        ("The applicant has worked at the branch ___ {v}.", "since", ["for", "from", "during", "by"], "'Since' is used with a starting point in time.", "Prepositions", 2),
        ("The revised procedure is different ___ the earlier procedure for {v}.", "from", ["than", "to", "with", "by"], "The standard construction is 'different from'.", "Prepositions", 3),
        ("She is ___ {v} employee.", "an", ["a", "the", "some", "no article"], "The adjective begins with a vowel sound, so 'an' is appropriate.", "Articles", 4),
        ("If the team ___, it would have avoided the delay involving {v}.", "had heeded the instruction", ["heeded the instruction", "would heed the instruction", "has heeded the instruction", "was heeding the instruction"], "The third conditional uses 'if + past perfect' and 'would have + past participle'.", "Conditional sentences", 5),
        ("The {v} ___ approved its annual report.", "has", ["have", "are", "were", "having"], "A collective body treated as one unit takes a singular verb here.", "Subject–verb agreement", 6),
        ("No sooner had the {v} ended ___ the lights went out.", "than", ["when", "then", "that", "while"], "The fixed correlative construction is 'no sooner...than'.", "Conjunctions", 7),
        ("The data collected during {v} ___ consistent with the findings.", "are", ["is", "was", "has", "be"], "'Data' is conventionally treated as plural in formal examination grammar.", "Subject–verb agreement", 8),
        ("The analyst insisted ___ checking {v}.", "on", ["for", "to", "at", "with"], "'Insist on' is followed by a noun or gerund.", "Prepositions", 9),
        ("The new policy may ___ to {v}.", "affect", ["effect", "affects", "effected", "affecting"], "'Affect' is the verb meaning to influence.", "Vocabulary in context", 10),
        ("The {v}, along with the other reviewers, ___ attending the review.", "is", ["are", "were", "have", "be"], "The main subject is singular; the phrase 'along with...' does not change it.", "Subject–verb agreement", 11),
        ("There are ___ errors in the revised version than in {v}.", "fewer", ["less", "little", "few", "least"], "'Fewer' is used with countable plural nouns such as errors.", "Determiners", 12),
        ("The tasks were divided ___ {v}.", "among", ["between", "beside", "within", "across"], "'Among' is appropriate when distributing something to more than two groups.", "Prepositions", 13),
        ("___ the {v}, the staff met the deadline.", "Despite", ["Although", "Because", "Since", "Unless"], "'Despite' is followed by a noun phrase, not a full clause.", "Conjunctions and connectors", 14),
        ("Hardly had {v} begun ___ the alarm rang.", "when", ["than", "then", "that", "while"], "The standard construction is 'hardly...when'.", "Conjunctions", 15),
        ("You had better ___ {v} before submitting it.", "verify", ["to verify", "verified", "verifying", "verifies"], "'Had better' is followed by the base form of the verb.", "Verb forms", 16),
        ("One of the officers who ___ the branch is absent because of {v}.", "manage", ["manages", "managing", "has managed", "is manage"], "The relative pronoun 'who' refers to the plural 'officers', so use 'manage'.", "Subject–verb agreement", 17),
        ("The number of applications ___ increased after {v}.", "has", ["have", "are", "were", "having"], "'The number' is singular and takes 'has'.", "Subject–verb agreement", 18),
        ("Neither of the two explanations ___ convincing in {v}.", "is", ["are", "were", "have", "be"], "'Neither' is singular in formal examination grammar.", "Subject–verb agreement", 19),
    ]
    while len(out) < n:
        template_index = len(out) % len(templates)
        variant_index = (len(out) // len(templates)) % 20
        sentence, answer, wrongs, explanation, topic, context_index = templates[template_index]
        context = contexts[context_index][variant_index]
        question = sentence.format(v=context)
        options = list(dict.fromkeys(list(wrongs) + [answer]))
        if len(options) < 5:
            for filler in ["None of these", "All of these"]:
                if filler not in options:
                    options.append(filler)
                if len(options) == 5:
                    break
        options = options[:5]
        if answer not in options:
            options[-1] = answer
        RNG.shuffle(options)
        item = qobj(topic, question, options, options.index(answer), explanation)
        before = len(out)
        add_unique(out, seen, item)
        if len(out) == before:
            # Each template/context pair should be unique; this is a safe fallback.
            question = question.rstrip(".?") + f" (variant {len(out)+1})."
            RNG.shuffle(options)
            add_unique(out, seen, qobj(topic, question, options, options.index(answer), explanation))
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
    # Mix categories before selecting a balanced, deterministic sample of awareness questions.
    RNG.shuffle(pools["awareness"])
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
                    limit = ({"ibps": {"quant": 35, "reasoning": 40, "english": 40, "awareness": 40}, "sbi": {"quant": 50, "reasoning": 50, "english": 40, "awareness": 50}})[exam][subject]
                    lines.append(f"  var current_{exam}_{subject}_{test} = SF_BANK.{exam}.{subject}[{test}] || [];")
                    lines.append(f"  SF_BANK.{exam}.{subject}[{test}] = current_{exam}_{subject}_{test}.concat({to_js(batch)}.slice(0, Math.max(0, {limit} - current_{exam}_{subject}_{test}.length)));")
    lines.append("})();")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT))
    for s in SUBJECTS:
        print(f"{s}: {len(pools[s])} unique questions available")
    print("Reminder: the importer is source-licensed, but factual accuracy still needs review before high-stakes use.")

if __name__ == "__main__":
    main()
