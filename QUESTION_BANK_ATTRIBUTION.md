# ScoreFree question-bank data provenance and licences

The bulk builder in `tools/build_question_bank.py` is designed to use no paid APIs or API keys.

## Sources

- **OpenTriviaQA** — https://github.com/uberspot/OpenTriviaQA — CC BY-SA 4.0. The importer reads text question files from the public repository when available. Attribution is retained in question metadata where imported. Adapted bank output containing this material is distributed under CC BY-SA 4.0.
- **Qulture reviewed question dataset** — https://www.qulture-app.com/open-data/qulture-reviewed-questions.json — CC BY 4.0. The importer selects English-language records, keeps the original question/choices/answer/explanation text, adds a fifth “None of the above” option, and records the source URL and record ID in question metadata.
- **ScoreFree deterministic practice generators** — original practice items generated locally by `tools/build_question_bank.py` for arithmetic, reasoning patterns and English grammar. No external question text or AI API is used for these items.

## Important limitations

- Open datasets are not specifically curated for IBPS/SBI bank exams. Imported general-trivia questions are classified as General/Financial Awareness only as general-awareness practice, not as official banking-current-affairs coverage.
- The pipeline checks structure and duplicate question text, but it cannot guarantee that every imported source answer is factually correct. Review before treating any question as authoritative.
- Current affairs should be dated and verified against primary sources before publication. The pipeline does not silently fabricate current-affairs updates.
- When OpenTriviaQA content is included, the combined adapted bank should be kept available under CC BY-SA 4.0, with attribution and a link to the licence: https://creativecommons.org/licenses/by-sa/4.0/.
- Qulture attribution: Qulture (2026), “Qulture General Knowledge Question Dataset”, https://doi.org/10.5281/zenodo.22108528, CC BY 4.0. Changes: English-language records are selected and a fifth option is added.
