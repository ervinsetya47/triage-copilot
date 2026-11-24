# How Kiro Was Used — Bug Bounty Triage Copilot

This project was built spec-first with Kiro, and the evidence is in the
repo itself: the `.kiro/` directory at the repo root (never gitignored)
holds the spec, the steering files, and a hook. Kiro was not a
code-completion add-on here — it was the way the project was planned,
constrained, and verified.

## 1. Spec-driven development (`.kiro/specs/triage-copilot/`)

The build started from a written spec, not from code:

- **`requirements.md`** — seven EARS-style requirements (ingest, scope
  check, known-issue cross-check, public-disclosure cross-check, severity
  suggestion, verdict, draft export), each with acceptance criteria, plus
  an eighth added when the web UI was built. Every feature in the shipped
  tool traces back to one of these requirements.
- **`design.md`** — the architecture (a linear six-stage pipeline),
  component descriptions, the data model, error handling, and the testing
  strategy: the five demo fixtures are the regression suite, and
  `python3 triage.py --demo` is the test run.
- **`tasks.md`** — the implementation plan as a checklist, executed in
  order (scaffold → data files → fixtures → CLI → verification → docs),
  then extended with the web UI, GitHub prep, and this write-up. Every
  item is checked off; nothing was built outside the task list.

## 2. Steering (`.kiro/steering/`)

Three steering files constrained every implementation decision, and they
are the reason the tool looks the way it does:

- **`product.md`** — the triage philosophy the code follows: never
  auto-submit; evidence first (every reason names the check and the entry
  that triggered it); honest severity (a Medium stays a Medium); a dead
  finding is a saved submission fee; deterministic and auditable.
- **`tech.md`** — the stack rule that shaped the whole project: Python 3
  standard library only, no dependencies, no network, no LLM. If it is
  not in the stdlib, it does not belong in the repo. The same file forbids
  hardcoded verdicts and requires paths to resolve relative to the script.
- **`structure.md`** — where everything lives: pipeline code in
  `triage.py` only, rules in `data/*.json`, fixtures in `data/fixtures/`,
  generated drafts in `reports/`.

When a decision came up — for example, how to add the web UI — the
steering files decided it: the server had to run the *same* `triage.py`
engine in-process (stdlib `http.server`, `POST /api/triage`), not a
second implementation, so the CLI and the web app can never disagree.
The refactor that made that possible (`build_report()` extracted from
`write_report()`) was verified by the existing checks: the CLI demo
still exits 0 at 5/5, and the server's report is byte-identical to the
CLI's.

## 3. Hook (`.kiro/hooks/report-draft-check.json`)

One Kiro hook ships with the project: whenever a file in `reports/` is
saved, it runs `python3 triage.py --check-draft <file>` to re-check that
the draft's verdict still matches the pipeline. A hand-edited draft
cannot silently drift away from the verdict that produced it. The hook
is a real Kiro hook (JSON, `onSave` event, `reports/*.md` pattern), not
a description of one.

## 4. What Kiro did not do

Honesty matters here too: the product itself contains no LLM and makes
no network calls — that is deliberate, per the steering files. The
triage verdicts come from explicit keyword rules in `data/*.json` and
`triage.py`, so any verdict can be audited back to the rule that made
it. Kiro's role was the development workflow — spec, steering, hook —
not the runtime analysis.

## Where to look

- Spec: `.kiro/specs/triage-copilot/` (`requirements.md`, `design.md`,
  `tasks.md`)
- Steering: `.kiro/steering/` (`product.md`, `tech.md`, `structure.md`)
- Hook: `.kiro/hooks/report-draft-check.json`
- Engine: `triage.py` · Web UI: `server.py` · Static app: `docs/`
