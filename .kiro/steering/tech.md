# Tech Guidance — Bug Bounty Triage Copilot

## Stack

- **Python 3** (3.10+), standard library only. No external dependencies,
  no `pip install`, no virtualenv. If it is not in the stdlib, it does not
  belong in this repo.
- **CLI-first.** One entry point, `triage.py`, runnable as
  `python3 triage.py <finding.json>` or `python3 triage.py --demo`.
- **Web UI.** `server.py` (stdlib `http.server`, port 8000) serves one
  page and runs the same `triage.py` engine in-process via
  `POST /api/triage`. The static app in `docs/` is a JS port for GitHub
  Pages; `tools/check_web.js` keeps the port in agreement with the CLI.
- **JSON fixtures.** All rules and data live in `data/*.json`:
  `scopes.json`, `known_issues.json`, `disclosures.json`, and the fixtures
  in `data/fixtures/`. Data is data; the code only interprets it.
- **Markdown report output.** Generated drafts go to `reports/<id>.md`
  in Immunefi format (Title, Severity, Description, Impact, Proof of
  Concept, Recommendation).

## Rules

- **Deterministic, rule-based checks only.** Severity and verdicts come
  from explicit keyword rules in the code and explicit entries in the JSON
  data files. No LLM calls, no network calls, no randomness.
- **No hardcoded verdicts.** The pipeline must never branch on a fixture
  id. Expected verdicts live only in `data/fixtures/expected.json` and are
  used solely by the `--demo` summary check.
- **Fail loudly, fail early.** Invalid JSON, missing required fields, or a
  missing data file is a clear stderr error and a non-zero exit — never a
  silent default.
- **Paths resolve relative to the script**, not the working directory, so
  the CLI works when invoked from anywhere.
- **Keep it tight.** One file for the CLI. Small, readable functions, one
  per pipeline stage. If a function grows past ~40 lines, split it.
