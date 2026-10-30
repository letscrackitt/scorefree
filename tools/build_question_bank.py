#!/usr/bin/env python3
"""Build ScoreFree's static question bank using only free/open sources and deterministic generators.
No API keys, paid services, or runtime network calls are required by the website.
"""
from __future__ import annotations
import hashlib, html, json, os, random, re, subprocess, sys, urllib.request
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
        before_count = len(pool)
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
        print("Qulture imported:", len(pool) - before_count)
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
    """Generate original Clerk Mains quantitative questions, including linked DI sets.

    The uploaded Quant material is used as a format/difficulty reference only.
    Questions and data below are independently authored; every numeric key is
    computed before options are shuffled and retained for regression testing.
    """
    out, seen = [], set()

    def add(topic, question, answer, explanation, set_title=None, set_intro=None):
        answer = int(answer)
        offsets = [5, 10, 15, 20, 25, 30, 40, 50]
        vals = {answer}
        for d in offsets:
            if len(vals) >= 5: break
            vals.add(answer + d)
            if answer - d >= 0 and len(vals) < 5: vals.add(answer - d)
        if len(vals) != 5: return
        opts = [str(v) for v in vals]
        RNG.shuffle(opts)
        item = qobj(topic, question, opts, opts.index(str(answer)), explanation)
        if not item: return
        item["answer_value"] = answer
        if set_title:
            item["setTitle"] = set_title
            item["setIntro"] = set_intro
        add_unique(out, seen, item)

    # Linked five-question DI caselets: shared data is repeated in each question
    # so the test renderer can show the complete case with every linked item.
    for case in range(1, 9):
        base = RNG.choice([120, 150, 180, 200, 240, 300]) + case * 5
        a, b, c, d, e = [base * x // 20 for x in [4, 5, 6, 7, 8]]
        total = a+b+c+d+e
        values = {"A":a,"B":b,"C":c,"D":d,"E":e}
        title = f"Data Interpretation · Branch deposits {case}"
        intro = (f"The following table gives the deposits (in ₹ lakh) collected by five branches "
                 f"A–E during a quarter: A={a}, B={b}, C={c}, D={d}, E={e}. "
                 "Assume all figures are exact. Answer Questions 1–5 using this common data.")
        qs = [
            ("Data interpretation · Table", f"What is the total deposit collected by branches A, C and E?", a+c+e,
             f"Required total = {a} + {c} + {e} = {a+c+e} lakh."),
            ("Data interpretation · Table", f"Deposits of branch D are what percent of the combined deposits of A and B?", d*100/(a+b),
             f"Required percentage = {d}/({a}+{b}) × 100 ≈ {d*100/(a+b):.2f}%."),
            ("Data interpretation · Table", f"If branch B increases its deposits by 20% and branch E decreases by 10%, what is the revised combined deposit of B and E?", round(b*1.2+e*0.9),
             f"Revised B = {b}×1.20 = {b*1.2:.2f}; revised E = {e}×0.90 = {e*0.9:.2f}; combined deposit ≈ ₹{round(b*1.2+e*0.9)} lakh."),
            ("Data interpretation · Table", f"Find the ratio of deposits of C and D in simplest form.", (c//5)//__import__('math').gcd(c//5,d//5)*1 if False else (c//__import__('math').gcd(c,d)),
             f"Ratio C:D = {c}:{d}; divide both terms by {__import__('math').gcd(c,d)} to obtain {c//__import__('math').gcd(c,d)}:{d//__import__('math').gcd(c,d)}."),
            ("Data interpretation · Table", f"By what amount do the deposits of D exceed the average deposits of A, B and C?", d-(a+b+c)//3,
             f"Average of A, B and C = ({a}+{b}+{c})/3 = {(a+b+c)//3}; excess = {d}-{(a+b+c)//3} = {d-(a+b+c)//3}.")
        ]
        for topic,q,ans,exp in qs:
            # Ratio question is encoded as the first ratio term for a numeric MCQ.
            if "simplest form" in q:
                g=__import__('math').gcd(c,d); q=f"If deposits of C and D are reduced in the ratio {c//g}:{d//g}, what is the first term of the ratio?"; ans=c//g
            add(topic,q,ans,exp,title,intro)

    attempts = 0
    while len(out) < n and attempts < n * 80:
        attempts += 1
        typ = RNG.randrange(12)
        if typ == 0:
            cp=RNG.choice([480,600,720,800,960,1200]); disc=RNG.choice([10,15,20,25]); profit=RNG.choice([12,15,20,25])
            mp=cp*100//(100-disc)
            sp=cp*(100+profit)//100
            ans=mp-sp
            q=f"An article is marked {disc}% above its cost price and sold after a discount of {disc}% on the marked price. If its cost price is ₹{cp}, what is the selling price?"
            # Avoid accidental equality of discount and markup by derive explicit discount-on-MP / profit setup instead.
            mp=cp*(100+profit)//100*100//(100-disc)
            sp=mp*(100-disc)//100; ans=sp
            q=f"An article costing ₹{cp} is marked {profit+disc}% above cost price and sold at a discount of {disc}% on the marked price. Find its selling price."
            exp=f"Marked price = {cp}×{100+profit+disc}/100 = {cp*(100+profit+disc)//100}; selling price = marked price×{100-disc}/100 = {ans}."
        elif typ == 1:
            p=RNG.choice([4000,5000,6000,8000,10000]); r=RNG.choice([5,10,12]); t=RNG.choice([2,3])
            num=p*((100+r)**t-100**t)
            if num % (100**t): continue
            ans=num//(100**t)
            q=f"Find the compound interest on ₹{p} at {r}% per annum, compounded annually, for {t} years."
            exp=f"Amount = {p}×(1+{r}/100)^{t} = ₹{p+ans}; compound interest = amount − principal = ₹{ans}."
        elif typ == 2:
            x=RNG.choice([12,15,18,20,24]); y=RNG.choice([8,10,12,15]); t=RNG.choice([4,5,6])
            ans=x*y//__import__('math').gcd(x,y)
            q=f"A and B can complete a work in {x} and {y} days respectively. They work together for {t} days, after which A leaves. How many more days will B take to finish the remaining work?"
            rem_num=x*y-t*(x+y)
            if rem_num<=0: continue
            ans=rem_num//x
            if rem_num%x: continue
            exp=f"Combined one-day work = 1/{x}+1/{y} = {(x+y)}/{x*y}. Remaining work after {t} days = {rem_num}/{x*y}; B alone takes ({rem_num}/{x*y})×{y} = {ans} days."
        elif typ == 3:
            u=RNG.choice([12,15,18,20]); v=RNG.choice([8,10,12,15]); stream=RNG.choice([2,3,4])
            down=u+stream; up=u-stream
            dist=RNG.choice([60,90,120,150])
            ans=dist*2*down*up//(down+up)
            q=f"A boat covers {dist} km downstream and the same distance upstream. Its speed in still water is {u} km/h and stream speed is {stream} km/h. What is its average speed for the entire journey?"
            total_time=dist/down+dist/up
            ans=round((2*dist)/total_time)
            if abs((2*dist)/total_time-ans)>1e-9: continue
            exp=f"Downstream speed = {u}+{stream} = {down}; upstream speed = {u}-{stream} = {up}. Total time = {dist}/{down}+{dist}/{up} hours; average speed = total distance/total time = {ans} km/h."
        elif typ == 4:
            speed=RNG.choice([45,54,60,72]); length=RNG.choice([120,150,180,200]); platform=RNG.choice([180,200,240,300]); sec=RNG.choice([20,25,30])
            ans=(length+platform)*18//(5*sec)
            if (length+platform)*18%(5*sec): continue
            q=f"A train {length} m long crosses a platform {platform} m long in {sec} seconds. Find its speed in km/h."
            exp=f"Total distance = {length}+{platform} = {length+platform} m. Speed = {length+platform}/{sec} m/s = {ans} km/h."
        elif typ == 5:
            total=RNG.choice([40,50,60,80,100]); ratio=RNG.choice([2,3,4]); addv=RNG.choice([5,10,15])
            ans=total*ratio//(ratio+1)
            if total*ratio%(ratio+1): continue
            q=f"A mixture contains milk and water in the ratio {ratio}:1. If {addv} litres of water are added, what was the original quantity of milk when the final mixture contains {total+addv} litres?"
            ans=total*ratio//(ratio+1)
            exp=f"Original mixture = {total} litres. Milk = {total}×{ratio}/{ratio+1} = {ans} litres."
        elif typ == 6:
            a=RNG.choice([12,15,18,20,24]); b=RNG.choice([8,10,12,15,16]); c=RNG.choice([6,8,10,12])
            ans=(a*b*c)//(a*b+b*c+c*a)
            if (a*b*c)%(a*b+b*c+c*a): continue
            q=f"A can complete a work in {a} days, B in {b} days and C in {c} days. How many days will they take working together?"
            exp=f"Combined rate = 1/{a}+1/{b}+1/{c} = {(a*b+b*c+c*a)}/{a*b*c}; time = {ans} days."
        elif typ == 7:
            cp=RNG.choice([600,750,900,1200,1500]); gain=RNG.choice([20,25,30,40]); discount=RNG.choice([10,15,20])
            sp_num=cp*(100+gain)
            if sp_num % 100: continue
            sp=sp_num//100
            if sp*100 % (100-discount): continue
            mp=sp*100//(100-discount); ans=mp
            q=f"After allowing a discount of {discount}% on the marked price, a trader earns {gain}% profit on an article costing ₹{cp}. Find the marked price."
            exp=f"Required selling price = {cp}×{100+gain}/100 = ₹{cp*(100+gain)//100}. Marked price = selling price×100/{100-discount} = ₹{ans}."
        elif typ == 8:
            old=RNG.choice([30,36,40,45,48,50,60]); new=old+RNG.choice([6,9,12,15]); time=RNG.choice([4,5,6,8])
            num=old*new*time
            if num % (new-old): continue
            ans=num//(new-old)
            q=f"A person reduces the time taken for a journey by {time} hours by increasing speed from {old} km/h to {new} km/h. Find the distance travelled."
            exp=f"Let distance be D. D/{old} − D/{new} = {time}; D×({new-old})/({old}×{new}) = {time}; D = {ans} km."
        elif typ == 9:
            n1=RNG.choice([20,24,30,36,40]); n2=RNG.choice([15,18,20,24,30]); avg=RNG.choice([50,60,70,80])
            ans=(n1+n2)*avg
            q=f"The average marks of {n1} students in section A and {n2} students in section B is {avg}. If the average of section A is {avg+5}, find the average marks of section B."
            # Use weighted average and choose values yielding integer.
            ans=((n1+n2)*avg-n1*(avg+5))//n2
            if ((n1+n2)*avg-n1*(avg+5))%n2: continue
            exp=f"Total marks = ({n1}+{n2})×{avg} = {(n1+n2)*avg}. Section A total = {n1}×{avg+5} = {n1*(avg+5)}. Section B average = ({(n1+n2)*avg}-{n1*(avg+5)})/{n2} = {ans}."
        elif typ == 10:
            a=RNG.choice([20,25,30,35,40]); b=RNG.choice([15,20,25,30]); c=RNG.choice([10,15,20])
            ans=(a*b)//__import__('math').gcd(a,b)
            q=f"The ratio of incomes of P and Q is {a}:{b}, while their expenditures are in the ratio {b}:{c}. If P saves ₹{a-b} and Q saves ₹{b-c}, find the difference between their incomes."
            # Keep this as a defined ratio-based linear system.
            k=RNG.choice([10,20,25,40]); ip=a*k; iq=b*k; ep=b*k; eq=c*k
            ans=ip-iq
            q=f"Incomes of P and Q are in the ratio {a}:{b}. If their actual incomes are ₹{ip} and ₹{iq} respectively, what is the difference between their incomes?"
            exp=f"One ratio part = {k}; difference = ({a}-{b})×{k} = ₹{ans}."
        else:
            r=RNG.choice([3,4,5,6]); h=RNG.choice([7,8,9,10,12]); ans=2*r*(r+h)
            q=f"A closed cylindrical container has radius {r} cm and height {h} cm. Find its total surface area (use π = 22/7 and select the nearest integer)."
            ans=round(2*(22/7)*r*(r+h))
            exp=f"Total surface area = 2πr(r+h) = 2×22/7×{r}×({r}+{h}) ≈ {ans} cm²."
        add("Arithmetic · Mains",q,ans,exp)

    # Exact, exam-style approximation and number/algebra questions add variety
    # without turning the bank into elementary one-step arithmetic.
    while len(out) < n:
        x=RNG.choice([144,169,196,225,256,289,324,361,400,441])
        y=RNG.choice([12,15,18,20,24,25,30])
        ans=x+y*y
        q=f"Evaluate √{x} + {y}² − {y}."
        ans=int(x**0.5)+y*y-y
        exp=f"√{x} = {int(x**0.5)}; therefore {int(x**0.5)} + {y*y} − {y} = {ans}."
        add("Approximation and calculation",q,ans,exp)
    return out[:n]

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

def generate_financial_awareness(n):
    """Original questions based on stable facts from official Indian financial institutions."""
    facts = [
        ("Which city houses the Reserve Bank of India's headquarters?", "The RBI's central office is located in which city?", "Mumbai", ["New Delhi", "Kolkata", "Chennai", "Hyderabad"], "The Reserve Bank of India has its central office in Mumbai.", "RBI basics", "https://www.rbi.org.in/"),
        ("On which date did the RBI begin operations?", "When did the Reserve Bank of India commence operations?", "1 April 1935", ["1 April 1947", "1 January 1935", "15 August 1947", "1 January 1949"], "The RBI began operations on 1 April 1935.", "RBI history", "https://www.rbi.org.in/"),
        ("When was the Reserve Bank of India nationalised?", "In which year did the RBI become state-owned?", "1949", ["1935", "1947", "1956", "1969"], "The RBI was nationalised in 1949.", "RBI history", "https://www.rbi.org.in/"),
        ("What is the maximum DICGC deposit insurance cover per depositor per bank?", "Deposits are insured by DICGC up to what amount per depositor per bank?", "₹5 lakh", ["₹1 lakh", "₹2 lakh", "₹10 lakh", "₹20 lakh"], "DICGC cover is up to ₹5 lakh per depositor per bank, including principal and interest, subject to the applicable rules.", "Deposit insurance", "https://www.dicgc.org.in/"),
        ("What does NEFT stand for?", "Which payment system is abbreviated as NEFT?", "National Electronic Funds Transfer", ["National Exchange for Funds and Trade", "National Electronic Finance Transaction", "New Electronic Fund Tracking", "National Exchange Fund Transfer"], "NEFT stands for National Electronic Funds Transfer.", "Payment systems", "https://www.rbi.org.in/"),
        ("What is the full form of RTGS?", "Which payment system uses the abbreviation RTGS?", "Real Time Gross Settlement", ["Rapid Transfer Gateway Service", "Real Transfer General System", "Retail Transaction Guarantee Service", "Real Time Government Securities"], "RTGS means Real Time Gross Settlement.", "Payment systems", "https://www.rbi.org.in/"),
        ("What is the expansion of UPI?", "UPI is short for which payment system?", "Unified Payments Interface", ["Universal Payment Integration", "Unified Processing Instrument", "Unique Payment Interface", "Universal Payments Infrastructure"], "UPI stands for Unified Payments Interface.", "Payment systems", "https://www.npci.org.in/"),
        ("What does IMPS stand for?", "Which service is abbreviated IMPS?", "Immediate Payment Service", ["Integrated Money Processing System", "Instant Merchant Payment Standard", "Indian Mobile Payment Settlement", "Immediate Payment Security"], "IMPS stands for Immediate Payment Service.", "Payment systems", "https://www.npci.org.in/"),
        ("Which organisation operates major retail payment systems such as UPI in India?", "UPI is operated by which Indian organisation?", "National Payments Corporation of India (NPCI)", ["Securities and Exchange Board of India", "Insurance Regulatory and Development Authority of India", "NABARD", "Pension Fund Regulatory and Development Authority"], "NPCI operates UPI and several other retail payment systems.", "NPCI", "https://www.npci.org.in/"),
        ("RuPay is best described as what?", "Which option correctly describes RuPay?", "An Indian domestic card payment network", ["A government bond", "A deposit insurance scheme", "A credit rating agency", "A bank reconciliation code"], "RuPay is India's domestic card payment network developed by NPCI.", "NPCI", "https://www.npci.org.in/"),
        ("How many characters are in an Indian bank IFSC?", "What is the standard length of an IFSC code?", "11 characters", ["8 characters", "9 characters", "10 characters", "12 characters"], "An IFSC is an 11-character alphanumeric code.", "Banking codes", "https://www.rbi.org.in/"),
        ("Which character is the fifth character of an IFSC?", "The fifth position in an IFSC is reserved for which character?", "Zero (0)", ["One (1)", "The letter O", "A dash (-)", "A bank-specific letter"], "The fifth character of an IFSC is zero.", "Banking codes", "https://www.rbi.org.in/"),
        ("How many digits are in an Indian MICR code?", "What is the usual length of a MICR code printed on Indian cheques?", "9 digits", ["6 digits", "8 digits", "10 digits", "11 digits"], "The MICR code used on Indian cheques contains nine digits.", "Banking codes", "https://www.rbi.org.in/"),
        ("What does CRR require banks to maintain?", "Under the Cash Reserve Ratio, what must banks keep with the RBI?", "A prescribed cash balance with the RBI", ["Gold reserves at SEBI", "Government bonds with NPCI", "Foreign currency with NABARD", "Insurance policies with DICGC"], "CRR is the share of a bank's net demand and time liabilities maintained as cash balance with the RBI.", "Monetary policy", "https://www.rbi.org.in/"),
        ("What does SLR refer to?", "Which requirement concerns liquid assets held by a bank itself?", "Statutory Liquidity Ratio", ["Special Lending Rate", "Scheduled Liability Register", "System Liquidity Reserve", "Standard Loan Return"], "SLR is the statutory liquidity requirement met with specified liquid assets.", "Monetary policy", "https://www.rbi.org.in/"),
        ("In basic monetary-policy terms, what is the repo rate?", "The repo rate is the rate at which the RBI generally does what?", "Lends short-term funds to banks against eligible securities", ["Insures household deposits", "Sets stock-exchange listing fees", "Lends directly to every retail borrower", "Guarantees company profits"], "The repo rate is a policy rate linked to RBI lending to banks against eligible collateral.", "Monetary policy", "https://www.rbi.org.in/"),
        ("Which body determines the policy repo rate under India's monetary policy framework?", "Who decides the policy repo rate in India?", "Monetary Policy Committee (MPC)", ["Finance Commission", "Central Vigilance Commission", "NPCI board", "GST Council"], "The RBI's Monetary Policy Committee determines the policy repo rate.", "Monetary policy", "https://www.rbi.org.in/"),
        ("How many members are on India's Monetary Policy Committee?", "What is the total membership of the RBI's MPC?", "Six", ["Four", "Five", "Seven", "Nine"], "The MPC has six members.", "Monetary policy", "https://www.rbi.org.in/"),
        ("What is the full form of KYC?", "KYC stands for which phrase in banking?", "Know Your Customer", ["Keep Your Cash", "Know Your Credit", "Key Yield Certificate", "Keep Your Credentials"], "KYC means Know Your Customer.", "Banking terminology", "https://www.rbi.org.in/"),
        ("What does AML stand for in financial regulation?", "Which phrase is abbreviated AML?", "Anti-Money Laundering", ["Automated Money Ledger", "Annual Market Limit", "Asset Management Loan", "Authorised Merchant Listing"], "AML stands for Anti-Money Laundering.", "Banking terminology", "https://www.rbi.org.in/"),
        ("A term loan is generally classified as an NPA when principal or interest remains overdue for more than how long?", "What overdue period is generally used for classifying a term loan as an NPA?", "90 days", ["30 days", "45 days", "60 days", "180 days"], "For term loans, the general NPA norm is overdue for more than 90 days, subject to applicable RBI rules and exceptions.", "Asset quality", "https://www.rbi.org.in/"),
        ("What does CASA mean in banking?", "Which expansion is correct for CASA deposits?", "Current Account and Savings Account", ["Cash Assets and Secured Advances", "Credit Account and Settlement Arrangement", "Current Assets and Scheduled Advances", "Capital Adequacy and Savings Allocation"], "CASA refers to Current Account and Savings Account deposits.", "Banking terminology", "https://www.rbi.org.in/"),
        ("In which year was NABARD established?", "When was the National Bank for Agriculture and Rural Development established?", "1982", ["1969", "1975", "1990", "1992"], "NABARD was established in 1982.", "Financial institutions", "https://www.nabard.org/"),
        ("NABARD primarily supports which area?", "Which field is central to NABARD's mandate?", "Agriculture and rural development", ["Stock-market regulation", "Life-insurance pricing", "Pension-fund supervision", "Urban property registration"], "NABARD focuses on agriculture and rural development.", "Financial institutions", "https://www.nabard.org/"),
        ("In which year was SIDBI established?", "When was the Small Industries Development Bank of India established?", "1990", ["1982", "1985", "1992", "2000"], "SIDBI was established in 1990.", "Financial institutions", "https://www.sidbi.in/"),
        ("SIDBI primarily supports the development of which segment?", "Which sector is central to SIDBI's development-finance role?", "Micro, small and medium enterprises (MSMEs)", ["Large foreign central banks", "Public universities only", "Life-insurance policyholders only", "State legislatures"], "SIDBI's mandate focuses on the promotion, financing and development of MSMEs.", "Financial institutions", "https://www.sidbi.in/"),
        ("In which year did SEBI receive statutory status?", "When was SEBI established as a statutory body?", "1992", ["1982", "1988", "1990", "2001"], "SEBI became a statutory body in 1992.", "Financial regulators", "https://www.sebi.gov.in/"),
        ("Which regulator oversees India's insurance sector?", "Insurance-sector regulation in India is handled by which body?", "Insurance Regulatory and Development Authority of India (IRDAI)", ["SEBI", "NABARD", "NPCI", "PFRDA"], "IRDAI is the insurance-sector regulator.", "Financial regulators", "https://irdai.gov.in/"),
        ("Which body regulates India's pension sector?", "Pension-fund regulation in India is associated with which authority?", "Pension Fund Regulatory and Development Authority (PFRDA)", ["IRDAI", "NPCI", "DICGC", "SIDBI"], "PFRDA regulates and develops India's pension sector.", "Financial regulators", "https://www.pfrda.org.in/"),
        ("In which year was the Pradhan Mantri Jan-Dhan Yojana launched?", "PMJDY was launched in which year?", "2014", ["2008", "2010", "2012", "2016"], "PMJDY was launched in August 2014 as a financial-inclusion initiative.", "Government schemes", "https://pmjdy.gov.in/"),
        ("The Pradhan Mantri MUDRA Yojana was launched in which year?", "When was PMMY (MUDRA Yojana) launched?", "2015", ["2011", "2013", "2014", "2018"], "PMMY was launched in 2015 to support financing for eligible micro enterprises.", "Government schemes", "https://www.mudra.org.in/"),
        ("Treasury bills are generally classified as what kind of instruments?", "What is the usual maturity category of Treasury bills?", "Short-term government securities", ["Perpetual corporate shares", "Long-term insurance contracts", "Unsecured personal loans", "Equity mutual funds"], "Treasury bills are short-term instruments issued by the government to raise funds.", "Money market", "https://www.rbi.org.in/"),
        ("Government securities are issued by whom?", "Who issues sovereign government securities in India?", "The Government of India or state governments", ["Only private commercial banks", "Only stock exchanges", "Only insurance companies", "Only payment networks"], "Government securities are issued by the central or state government, depending on the instrument.", "Government securities", "https://www.rbi.org.in/"),
        ("When was the RBI Integrated Ombudsman Scheme introduced?", "The RBI Integrated Ombudsman Scheme was launched in which year?", "2021", ["2015", "2017", "2019", "2023"], "The RBI Integrated Ombudsman Scheme was launched in 2021.", "Customer protection", "https://www.rbi.org.in/"),
        ("What is the full form of AePS?", "Which payment service is abbreviated AePS?", "Aadhaar Enabled Payment System", ["Automated Electronic Payment Standard", "Account Entry Processing Service", "Advanced Electronic Protection System", "Aadhaar Exchange Processing Scheme"], "AePS stands for Aadhaar Enabled Payment System.", "Payment systems", "https://www.npci.org.in/"),
        ("What does NACH stand for?", "Which payment system is abbreviated NACH?", "National Automated Clearing House", ["National Account Credit Hub", "New Automated Cash Handling", "National Authorised Cheque House", "Network for Account Clearing and Holding"], "NACH stands for National Automated Clearing House.", "Payment systems", "https://www.npci.org.in/"),
        ("What is the purpose of the Cheque Truncation System (CTS)?", "CTS in cheque processing primarily enables what?", "Electronic processing using cheque images and data", ["Printing new currency notes", "Insuring deposits", "Setting policy interest rates", "Issuing stock-market licences"], "CTS enables cheque processing through electronic images and associated data rather than physical movement of the cheque throughout the process.", "Cheque clearing", "https://www.rbi.org.in/"),
        ("What is the minimum amount generally permitted for an RTGS transaction in India?", "RTGS is generally available for transactions of at least what amount?", "₹2 lakh", ["₹10,000", "₹50,000", "₹1 lakh", "₹5 lakh"], "The minimum RTGS transaction amount is generally ₹2 lakh; there is no RBI-set upper ceiling.", "Payment systems", "https://www.rbi.org.in/"),
        ("What does the term 'financial inclusion' broadly aim to improve?", "Financial inclusion is primarily concerned with what?", "Access to useful and affordable financial services", ["Access to stock trading only", "Eliminating all bank branches", "Replacing all deposits with cash", "Restricting services to large companies"], "Financial inclusion seeks broader access to useful, affordable financial products and services.", "Financial inclusion", "https://pmjdy.gov.in/"),
        ("Which type of account is designed mainly for frequent business transactions?", "Which deposit account is commonly used for frequent business transactions?", "Current account", ["Fixed deposit only", "Recurring deposit only", "Demat account", "Pension account"], "Current accounts are designed for frequent transactions, especially for businesses and institutions.", "Bank accounts", "https://www.rbi.org.in/"),
        ("What is the main role of DICGC?", "Which service does DICGC provide?", "Deposit insurance for eligible bank deposits", ["Regulation of stock exchanges", "Operation of UPI", "Insurance-sector licensing", "Rural agricultural lending"], "DICGC provides deposit insurance subject to its coverage rules.", "Deposit insurance", "https://www.dicgc.org.in/"),
    ]
    out = []
    for i in range(n):
        q1, q2, answer, distractors, explanation, topic, source_url = facts[i % len(facts)]
        question = q1 if (i // len(facts)) % 2 == 0 else q2
        options = list(distractors) + [answer]
        # Rotate the distractors deterministically so the two phrasings are not identical.
        shift = (i // len(facts)) % len(distractors)
        distractors_rotated = distractors[shift:] + distractors[:shift]
        options = distractors_rotated + [answer]
        RNG.shuffle(options)
        item = qobj(topic, question, options, options.index(answer), explanation,
                    {"name": "Official Indian financial institution reference", "url": source_url,
                     "license": "Original question based on public factual information"})
        if item:
            out.append(item)
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
    # Preserve all English Qulture records in the selected awareness pool instead of
    # letting random truncation accidentally discard this explicitly licensed source.
    qulture = [q for q in pools["awareness"]
               if (q.get("source") or {}).get("name") == "Qulture reviewed question dataset"]
    open_trivia_awareness = [q for q in pools["awareness"]
                             if (q.get("source") or {}).get("name") != "Qulture reviewed question dataset"]
    RNG.shuffle(open_trivia_awareness)
    awareness_import_target = TARGET_PER_EXAM_SUBJECT * 2 - 80
    keep_qulture = qulture[:awareness_import_target]
    keep_open_trivia = open_trivia_awareness[:max(0, awareness_import_target - len(keep_qulture))]
    pools["awareness"] = keep_open_trivia + keep_qulture
    RNG.shuffle(pools["awareness"])
    pools["awareness"].extend(generate_financial_awareness(80))
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
    # Change the asset query only when the generated bank changes, preventing stale browser caches.
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()[:10]
    page_path = ROOT / "clerk-mains.html"
    page = page_path.read_text(encoding="utf-8")
    page, replacements = re.subn(
        r'(<script src="./question-bank.generated.js\?v=)[^"]+("></script>)',
        lambda match: match.group(1) + digest + match.group(2),
        page,
        count=1,
    )
    if replacements:
        page_path.write_text(page, encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT), "with cache key", digest)
    for s in SUBJECTS:
        print(f"{s}: {len(pools[s])} unique questions available")
    print("Reminder: the importer is source-licensed, but factual accuracy still needs review before high-stakes use.")

if __name__ == "__main__":
    main()
