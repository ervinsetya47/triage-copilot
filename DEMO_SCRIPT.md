# Demo Script — Bug Bounty Triage Copilot (2–3 minutes)

Run everything from the repo root: `cd ~/workspace/kiroween/triage-copilot`

## Beat 1 — The problem (~30s)

> "Every bug bounty report costs a submission fee. But half the findings a
> hunter writes up are already dead — out of scope, listed as a known
> issue, or publicly disclosed in an audit report months ago. You only find
> out after you paid. The Triage Copilot checks that *before* you spend
> anything: scope, known issues, public disclosures, severity — one
> verdict, and a report draft if the finding is alive. Deterministic,
> rule-based, no LLM, no network. A dead finding is a saved fee."

Show the repo layout briefly:

```bash
ls triage.py data data/fixtures reports .kiro/specs/triage-copilot
```

## Beat 2 — A live finding: the Charm fake pool (~40s)

Ingest the Charm fake-pool finding and watch the pipeline run:

```bash
python3 triage.py data/fixtures/charm-fake-pool.json
```

Point at the step lines as they print:

- `[2/6] Scope check: IN SCOPE` — AlphaProVaultFactory is in the Charm scope.
- `[3/6] Known-issue check: no match`
- `[4/6] Disclosure check: no match`
- `[5/6] Severity suggestion: Critical-class` — drain of user funds.
- `[6/6] Verdict: REPORTABLE`

Then show the generated Immunefi-format draft:

```bash
cat reports/charm-fake-pool.md
```

> "Title, Severity, Description, Impact, Proof of Concept,
> Recommendation — ready to paste into the submission form. The copilot
> never submits; the human does."

## Beat 3 — A dead finding: Everest Finding 2 (~40s)

Same command, a finding that looks strong — a PoC that passed 4/4 — but
is already dead:

```bash
python3 triage.py data/fixtures/everest-finding2.json
```

Point at the step lines:

- `[3/6] Known-issue check: MATCH — Cantina-U19-3.3.1`
- `[4/6] Disclosure check: MATCH — Cantina-U19-3.3.1`
- `[5/6] Severity suggestion: Informational / not reportable`
- `[6/6] Verdict: NOT REPORTABLE` with three numbered reasons.

Show the triage note:

```bash
cat reports/everest-finding2.md
```

> "Four passing PoC runs, zero dollars wasted. The copilot killed it in
> two seconds because the issue was already reported as Informational in
> the Cantina audit — and it's intended design on top of that."

## Beat 4 — The 5/5 summary (~30s)

Run the full demo and show the summary table:

```bash
python3 triage.py --demo
```

Expected output:

```
fixture              expected         actual           severity
charm-fake-pool      REPORTABLE       REPORTABLE       Critical-class
everest-finding2     NOT REPORTABLE   NOT REPORTABLE   Informational / not reportable
everest-finding3     NOT REPORTABLE   NOT REPORTABLE   Medium at most
everest-mempool      REPORTABLE       REPORTABLE       Medium
relay-executor       REPORTABLE       REPORTABLE       S3/L2 (High-class)

5/5 fixtures match.
```

> "Five real findings from real hunts — Charm, Base Everest, Relay — all
> five verdicts correct, and none of them hardcoded: the verdicts come
> from the pipeline rules, the expected values live in a separate JSON
> file used only for the check. Exit code 0 means the suite is green."

## Close (~10s)

> "Triage Copilot: evidence first, honest severity, and a dead finding is
> a saved submission fee."
