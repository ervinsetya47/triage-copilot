# Bug Bounty Triage Copilot

A CLI copilot for a solo bug bounty hunter. It triages a candidate finding
*before* you spend a submission fee: scope, known issues, public
disclosures, severity — then one verdict (REPORTABLE / NOT REPORTABLE) and,
if the finding is alive, an Immunefi-format report draft.

**The copilot never auto-submits anything.** Every check is an explicit rule
in a JSON data file, so any verdict can be audited back to the rule that
made it. A dead finding is a saved submission fee.

Built with Kiro for the Kiroween 2026 hackathon. The `.kiro/` directory
holds the spec (requirements, design, tasks), steering files, and a hook —
they are the record of how Kiro was used to build this project.

**Kiroween 2026 — category: Frankenstein.** The copilot stitches existing
data and tools — program scopes, published known issues, public audit
disclosures — into a new triage workflow.

## Requirements

- Python 3.10+ — standard library only, no dependencies to install.

## Run

Triage one finding:

```bash
python3 triage.py data/fixtures/charm-fake-pool.json
```

Run the demo (all 5 fixtures, with an expected-vs-actual summary):

```bash
python3 triage.py --demo
```

The demo exits `0` only if all five fixtures match their expected verdicts.

## Web app

The same pipeline runs in the browser — no install, no server. Files live in
`docs/` so the app can be published with GitHub Pages straight from the repo
(Settings → Pages → Deploy from branch → `main` → `/docs`):

- `docs/index.html` — pick a demo fixture or paste your own finding JSON, run
  triage, copy or download the generated report draft.
- `docs/triage.js` — faithful JS port of `triage.py` (same six steps, same
  verdict logic, same report markdown).
- `docs/data.js` — generated from `data/*.json`; regenerate after editing any
  rule with `python3 tools/build_web_data.py`.

Verify the web port agrees with the CLI:

```bash
python3 triage.py --demo        # CLI: 5/5 fixtures
node tools/check_web.js         # web: 5/5 fixtures + reports byte-identical to reports/
```

### Local server (same Python engine)

`server.py` serves a one-page UI and runs the real `triage.py` pipeline
server-side — no separate implementation:

```bash
python3 server.py               # open http://127.0.0.1:8000
```

Pick a demo fixture or fill the form (title, program, target,
description, PoC notes) → verdict + severity + numbered reasons →
report draft with a download button. `POST /api/triage` returns the
verdict payload and the report markdown; `GET /api/demo` re-runs the
5/5 self-check. The server never writes files. `PORT` and `HOST`
environment variables override the bind address (default
`127.0.0.1:8000`) for hosting.

## Hosting the app URL

Devpost requires a working app URL. Nothing is deployed yet — these are
the free options, in recommended order:

1. **GitHub Pages** (recommended) — serves the static app in `docs/`:
   repo Settings → Pages → Deploy from branch → `main` → `/docs`. No
   server, no cost, no sleep.
2. **Render (free tier)** — Web Service from the repo, start command
   `python3 server.py`. Render sets `$PORT` and the server reads it; set
   `HOST=0.0.0.0` in the service environment. Free tier sleeps when idle.
3. **Fly.io (free allowance)** — `fly launch` with the included
   `Dockerfile` (Python 3.12-slim, `python3 server.py`). Set
   `HOST=0.0.0.0`; Fly.io assigns `$PORT`.

## How it works

```
finding.json ──► [1 Ingest] ──► [2 Scope] ──► [3 Known Issues]
      ──► [4 Disclosures] ──► [5 Severity] ──► [6 Verdict]
      ──► [7 Draft Export] ──► reports/<id>.md
```

1. **Ingest** — parses the finding JSON (`id`, `title`, `program`,
   `target`, `description`, `poc_notes`).
2. **Scope check** — target against `data/scopes.json` (Charm, Base
   Everest, Relay).
3. **Known-issue cross-check** — signature keywords against
   `data/known_issues.json` (KI-24, KI-56, Cantina U19 §3.3.1, PeckShield
   PVE-001, Sherlock H-1 / #155).
4. **Public-disclosure cross-check** — same mechanism against
   `data/disclosures.json`.
5. **Severity suggestion** — rule-based: drain/theft → Critical-class,
   single-tx delay → Medium, griefing with no attacker gain → Medium at
   most, intended design → Informational.
6. **Verdict** — REPORTABLE only if in scope, no KI match, no disclosure
   match, and severity above Informational; otherwise NOT REPORTABLE with
   numbered reasons.
7. **Draft export** — REPORTABLE findings get an Immunefi-format draft
   (`reports/<id>.md`); dead findings get a short triage note marked
   NOT REPORTABLE.

## Demo fixtures

| Fixture | Program | Expected verdict |
|---|---|---|
| `charm-fake-pool` | Charm | REPORTABLE, Critical-class |
| `everest-finding2` | Base Everest | NOT REPORTABLE (intended design + disclosed) |
| `everest-finding3` | Base Everest | NOT REPORTABLE (publicly disclosed) |
| `everest-mempool` | Base Everest | REPORTABLE, Medium |
| `relay-executor` | Relay | REPORTABLE, S3/L2 (High-class) |

Expected verdicts live in `data/fixtures/expected.json` and are used only
by the `--demo` summary check — the pipeline never branches on a fixture
id.

## Repo layout

See `.kiro/steering/structure.md`. In short: `triage.py` is the whole CLI,
`data/*.json` holds every rule, `data/fixtures/` holds the five demo
findings, `reports/` holds generated drafts, and `.kiro/` holds the spec,
steering, and hook files.

## Kiro hook

`.kiro/hooks/report-draft-check.json` runs
`python3 triage.py --check-draft <file>` whenever a file in `reports/` is
saved, re-checking that the draft's verdict still matches the pipeline.
