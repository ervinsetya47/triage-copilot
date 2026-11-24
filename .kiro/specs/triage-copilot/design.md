# Design Document — Bug Bounty Triage Copilot

## Overview

The Triage Copilot is a single-file Python 3 CLI (`triage.py`, stdlib only)
that runs a deterministic, rule-based triage pipeline over a candidate bug
bounty finding. There is no network access, no LLM call, and no external
dependency. Every rule lives in a JSON data file under `data/`, so any
verdict can be traced back to the exact rule that produced it.

The user runs one command per finding, or `--demo` to run the five bundled
fixtures and verify the pipeline against the expected verdicts in
`data/fixtures/expected.json`.

## Architecture

The CLI is a linear pipeline. Each stage prints one clear step line, runs
its check, and appends its result to the finding's verdict record. Stages
never short-circuit: even a finding that fails the scope check still runs
the remaining checks, so the hunter sees the full picture (e.g. a finding
can be both out of scope *and* publicly disclosed).

```
finding.json ──► [1 Ingest] ──► [2 Scope] ──► [3 Known Issues]
      ──► [4 Disclosures] ──► [5 Severity] ──► [6 Verdict]
      ──► [7 Draft Export] ──► reports/<id>.md
                                  │
                                  └─► --demo: summary table + exit code
```

Data files are loaded once at startup from `data/` (resolved relative to
the script's own directory, so the CLI works from any working directory).

## Components

### Ingest (`load_finding`)

Reads and validates the finding JSON. Required fields: `id`, `title`,
`program`, `target`, `description`, `poc_notes`. Missing fields or invalid
JSON produce a fatal error with the field name and a non-zero exit; no
report is written.

### Scope Checker (`check_scope`)

Loads `data/scopes.json`. Each program entry lists `in_scope` targets
(substring-matched, case-insensitive, against the finding's `target` and
`description`) and `out_of_scope` notes. Result: `in-scope` or
`out-of-scope` with a human-readable reason. Unknown program → out of
scope with reason "unknown program".

### Known-Issue Checker (`check_known_issues`)

Loads `data/known_issues.json`. Each entry has an `id`, a `title`, and a
`keywords` list of signature phrases. A match is a case-insensitive
substring hit of any keyword in the finding's title, description, or
PoC notes. Returns the list of matched entries. Any match makes the
finding NOT REPORTABLE.

### Disclosure Checker (`check_disclosures`)

Loads `data/disclosures.json`. Same matching mechanism as the known-issue
checker, but the entries are public disclosures (audit reports, Sherlock /
Cantina findings) with a `source` field. Any match makes the finding
NOT REPORTABLE.

### Severity Suggester (`suggest_severity`)

Rule-based, evaluated in order of impact severity:

1. Drain / theft of user funds (keywords: `drain`, `steal`, `theft`,
   `attacker gains`, `sweep`) → **Critical-class**.
2. Program-specific scale: if the finding's program is Relay and the
   description indicates a sweep of another order's funds with a stated
   S3/L2 assessment → **S3/L2 (High-class)**.
3. Single-transaction delay / censorship (keywords: `delay`,
   `parked`, `censor`, `underpriced`) → **Medium**.
4. Griefing / lock with no attacker gain (keywords: `grief`,
   `lock`, `burn` with no gain) → **Medium at most**.
5. Intended design (keywords: `intended design`, `documented`) →
   **Informational / not reportable**.
6. Default → **Medium** (conservative; the hunter adjusts).

Severity never overrides a NOT REPORTABLE verdict from the earlier checks;
it only informs the draft.

### Report Drafter (`write_report`)

Writes `reports/<finding-id>.md`. For REPORTABLE findings the draft has
Immunefi-format sections: Title, Severity, Description, Impact, Proof of
Concept, Recommendation. For NOT REPORTABLE findings it writes a short
triage note clearly headed NOT REPORTABLE with the numbered reasons.

### Demo Runner (`run_demo`)

Runs the pipeline over the five fixtures in `data/fixtures/`, prints a
summary table of expected vs actual verdicts (from
`data/fixtures/expected.json`), and exits 0 only if all five match.

### Web Server (`server.py`)

Python 3 stdlib `http.server` wrapper around the same engine — no
separate implementation. `GET /` serves one page (finding form + fixture
buttons). `POST /api/triage` validates the finding, runs `triage()` and
`build_report()` in-process, and returns the verdict payload plus the
report markdown (byte-identical to the CLI's `reports/<id>.md`).
`GET /api/fixtures` and `GET /api/demo` expose the fixtures and the 5/5
self-check. The server never writes files and never submits anything.
The static app in `docs/` (GitHub Pages) is a JS port of the same
pipeline; `tools/check_web.js` verifies the port agrees with the CLI.

## Data Model

### Finding

```json
{
  "id": "charm-fake-pool",
  "title": "Fake Uniswap V3 pool drains Alpha Vault via unchecked callback",
  "program": "Charm",
  "target": "AlphaProVaultFactory / AlphaProVault",
  "description": "...",
  "poc_notes": "..."
}
```

### Verdict (in-memory)

| Field | Meaning |
|---|---|
| `scope` | `"in-scope"` / `"out-of-scope"` + reason |
| `known_issues` | list of matched KI entries (empty = clean) |
| `disclosures` | list of matched disclosure entries (empty = clean) |
| `severity` | suggested severity string |
| `verdict` | `"REPORTABLE"` / `"NOT REPORTABLE"` |
| `reasons` | numbered list of strings justifying the verdict |

### Report

Markdown file at `reports/<finding-id>.md`, either an Immunefi-format
draft (reportable) or a triage note (not reportable).

## Error Handling

- Invalid JSON / missing field in the finding → error to stderr, exit 2,
  no report written.
- Missing `data/*.json` file → error to stderr, exit 2.
- Missing fixture in `--demo` → that row is reported as ERROR in the
  summary table and the demo exits 1.
- Report write failure (e.g. unwritable `reports/`) → error to stderr,
  exit 2.
- The pipeline never raises an unhandled exception for a well-formed
  finding; a failed check is a result, not a crash.

## Testing Strategy

- **Demo fixtures as regression tests:** the five fixtures in
  `data/fixtures/` encode real, verified findings from the hunter's own
  work (Charm fake pool, Base Everest Findings 2 and 3, Everest mempool,
  Relay executor). `data/fixtures/expected.json` holds their expected
  verdicts. `python3 triage.py --demo` is the test suite: exit 0 means
  all five match.
- **Manual spot checks:** run the CLI on a single fixture and inspect the
  generated `reports/<id>.md` for correct sections and reasons.
- **No hardcoded verdicts:** the demo check reads expected verdicts only
  from `expected.json`; the pipeline itself never branches on a fixture
  id. A regression test that passes by hardcoding would be caught by
  adding a sixth fixture, which the pipeline must classify by its rules.
