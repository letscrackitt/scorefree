# SCOREFREE

Free, no-login descriptive-writing practice for IBPS PO/MT and SBI PO.

## Current 2026 exam basis

- **IBPS PO/MT-XVI:** Essay + Comprehension, 2 questions, 25 marks, 30 minutes, English.
- **SBI PO 2026:** Emails (1 of 2), Situation Analysis (1 of 2), and either Report Writing or Precis Writing (1 of 2), 30 marks, 30 minutes, English.

## Word-limit policy

The current 2026 IBPS PO/MT-XVI and SBI PO 2026 notifications do **not** publish a universal fixed word limit for these descriptive tasks. SCOREFREE therefore does not label its practice ranges as official.

Where no official fixed limit is published, the question itself shows a clearly labelled **practice target** (for example, 250–300 words for an essay or 80–100 words for a comprehension answer). These ranges are practice guidance only, not bank-issued limits.

For précis, the site follows the SBI training guidance that a précis is normally about one-third of the source passage, while the exact instruction in the question takes priority.

## Practice bank

- 50 IBPS Essay tests
- 50 IBPS Comprehension tests with full original reading passages and questions
- 50 SBI Email tests
- 50 SBI Situation Analysis tests
- 50 SBI Report tests
- 50 SBI Precis tests
- 50 SBI Full Descriptive practice sets

Reported questions are labelled **Reported PYQ**. Original prompts are labelled **Practice**.

## Scoring

SCOREFREE provides a transparent **practice score out of 100** using relevance, structure, language and completeness criteria. It is not an official IBPS/SBI examiner score.


### IBPS comprehension

The IBPS Comprehension bank contains 50 complete practice passages. Each test includes the reading passage, a question, topic guidance, and a clearly labelled practice word target. The practice target is not presented as an official IBPS word limit.


## Clerk Mains objective practice and bulk question bank

- `clerk-mains.html` uses the existing exam-style interface: one question at a time, timer, question palette, Save & Next, Clear Response, Mark for Review, submit confirmation, scoring, and answer explanations.
- The objective bank supports 10 test slots per subject for both IBPS Clerk Mains and SBI Clerk Mains: Quantitative Aptitude, Reasoning, English, and General/Financial Awareness. These are currently **partial practice tests**, not full-length mocks: the bulk builder supplies up to 20 generated/imported questions per test, while the UI retains the section's official question count and timer.
- `question-bank.js` remains the hand-maintained source. `tools/build_question_bank.py` creates `question-bank.generated.js` separately and appends questions without replacing the hand-maintained items.
- The bulk builder uses free/open inputs only: OpenTriviaQA (CC BY-SA 4.0), the Qulture reviewed question dataset (CC BY 4.0), and original deterministic questions generated locally from templates and stable public financial facts. It requires no paid API or API key.
- GitHub Actions runs the builder on a weekly schedule and can also be run manually from the repository's **Actions** tab. The workflow now runs regression tests against the generated quantitative answer keys before publishing the updated static file.
- Read `QUESTION_BANK_ATTRIBUTION.md` for attribution, licensing, and known limitations. Imported public question datasets are not official IBPS/SBI papers, and generated/imported answers should be reviewed before high-stakes use.
- The section interface keeps its own timing and marking configuration. Verify official exam patterns against the latest IBPS/SBI notifications before describing any practice configuration as official.


## Mains question quality benchmarks

- The Clerk Mains page now links to Adda247, Oliveboard, Guidely and Testbook as external references for real-world Mains difficulty and question formats. Their questions are not republished without permission.
- See [MAINS_BENCHMARKS.md](MAINS_BENCHMARKS.md) for the subject-by-subject quality checklist, answer verification requirements, and source/licensing workflow.

## Mains-level Quantitative Aptitude (original questions)

`question-bank.mains-quant.js` fills **IBPS Clerk Mains Quants (35 Q)** and **SBI Clerk Mains Quants (50 Q)**, Tests 1–10, with original questions: quadratic-equation relations, number series (missing and wrong term), four-to-five-question Data Interpretation sets with real tables and charts (table, bar, line, pie and mixture sets), multi-step arithmetic caselets, approximation, and (SBI) data sufficiency and quantity comparison. Every question has five options, one correct key and a step-by-step solution shown in the post-test review.

The file is generated. Edit `tools/build_mains_quant.py`, then run `python tools/build_mains_quant.py`. The builder derives every answer twice (forward from hidden values, then from the printed data) and `tools/test_mains_quant.py` re-checks structure on every CI run. The file loads after `question-bank.generated.js` and replaces the quant tests, so the weekly open-bank refresh cannot mix basic items back into Mains quants.
