# Requirements Document — Bug Bounty Triage Copilot

## Introduction

A solo bug bounty hunter wastes submission fees and triage hours on findings
that are already dead: out of scope, listed as a known issue, publicly
disclosed before the competition, or intended design. The Bug Bounty Triage
Copilot is a CLI-first tool that ingests a candidate finding as JSON and runs
a deterministic, auditable triage pipeline before the hunter spends a cent:

1. **Scope check** — is the target in the program's stated scope?
2. **Known-issue cross-check** — does the finding match a published Known
   Issue (KI) in the program's docs or audit reports?
3. **Public-disclosure cross-check** — was the same issue publicly disclosed
   before the competition (audit report, Sherlock/Cantina finding)?
4. **Severity suggestion** — rule-based severity class from impact keywords.
5. **Verdict** — REPORTABLE or NOT REPORTABLE, with numbered reasons.
6. **Report draft** — an Immunefi-format Markdown draft for reportable
   findings, or a short triage note for dead ones.

The copilot never auto-submits anything. Every check is an explicit rule in
a JSON data file, so the hunter can audit exactly why a verdict was reached.
It uses Python 3 standard library only and makes no network or LLM calls.

## Requirements

### Requirement 1: Ingest a finding

**User Story:** As a bug bounty hunter, I want to feed a candidate finding
into the copilot as a JSON file, so that I can triage it without retyping it
into a web form.

#### Acceptance Criteria

1. WHEN the user runs `python3 triage.py <finding.json>` with a file
   containing `id`, `title`, `program`, `target`, `description`, and
   `poc_notes`, THEN the copilot SHALL parse the file and begin the pipeline.
2. WHEN the finding JSON is missing a required field or is not valid JSON,
   THEN the copilot SHALL print a clear error naming the problem and exit
   with a non-zero status without writing a report.
3. WHEN the user runs `python3 triage.py --demo`, THEN the copilot SHALL
   run the pipeline over all five fixtures in `data/fixtures/` and print a
   summary table.

### Requirement 2: Scope check

**User Story:** As a hunter, I want the copilot to check whether my finding's
target is in the program's stated scope, so that I do not submit an
out-of-scope report.

#### Acceptance Criteria

1. WHEN a finding's `target` matches an in-scope target in
   `data/scopes.json` for its `program`, THEN the scope check SHALL pass
   with the reason "target is in scope".
2. WHEN a finding's `target` matches an out-of-scope entry or no in-scope
   target for its `program`, THEN the scope check SHALL fail with a reason
   naming the program and the mismatch.
3. WHEN a finding names a program that has no entry in `data/scopes.json`,
   THEN the scope check SHALL report "unknown program" and the finding
   SHALL be treated as out of scope.

### Requirement 3: Known-issue cross-check

**User Story:** As a hunter, I want the copilot to cross-check my finding
against the program's published Known Issues, so that I do not submit a
finding the program already lists as known.

#### Acceptance Criteria

1. WHEN the finding's title, description, or PoC notes contain the
   signature keywords of a known issue in `data/known_issues.json`, THEN
   the cross-check SHALL flag that known issue by its ID and title.
2. WHEN no known-issue signature matches, THEN the cross-check SHALL
   report "no known-issue match".
3. WHEN a known-issue match is found, THEN the finding SHALL be marked
   NOT REPORTABLE with the known issue cited as a numbered reason.

### Requirement 4: Public-disclosure cross-check

**User Story:** As a hunter, I want the copilot to cross-check my finding
against publicly disclosed issues, so that I do not submit a finding that
was already disclosed in a public audit or contest report.

#### Acceptance Criteria

1. WHEN the finding's title, description, or PoC notes contain the
   signature keywords of a disclosure in `data/disclosures.json`, THEN
   the cross-check SHALL flag that disclosure by its source and title.
2. WHEN no disclosure signature matches, THEN the cross-check SHALL
   report "no public-disclosure match".
3. WHEN a disclosure match is found, THEN the finding SHALL be marked
   NOT REPORTABLE with the disclosure cited as a numbered reason.

### Requirement 5: Severity suggestion

**User Story:** As a hunter, I want the copilot to suggest a severity class
from the finding's impact, so that I can sanity-check my own severity
before writing the report.

#### Acceptance Criteria

1. WHEN the finding describes theft or draining of user funds, THEN the
   severity suggestion SHALL be Critical-class.
2. WHEN the finding describes griefing or locking of funds with no attacker
   gain, THEN the severity suggestion SHALL be Medium at most.
3. WHEN the finding describes a single-transaction delay or censorship,
   THEN the severity suggestion SHALL be Medium.
4. WHEN the finding is intended design, THEN the severity suggestion SHALL
   be Informational / not reportable.
5. WHEN the finding matches a program-specific severity scale (e.g. Relay
   S3/L2), THEN the suggestion SHALL include that program-specific class.

### Requirement 6: Verdict

**User Story:** As a hunter, I want a single clear verdict — REPORTABLE or
NOT REPORTABLE — with numbered reasons, so that I can decide in seconds
whether to spend the submission fee.

#### Acceptance Criteria

1. WHEN every check passes (in scope, no known-issue match, no disclosure
   match, severity above Informational), THEN the verdict SHALL be
   REPORTABLE.
2. WHEN any check fails (out of scope, known-issue match, disclosure match,
   or intended design), THEN the verdict SHALL be NOT REPORTABLE.
3. WHEN a verdict is produced, THEN the copilot SHALL print the verdict
   with numbered reasons covering each check that contributed to it.
4. WHEN the copilot runs in `--demo` mode, THEN it SHALL compare each
   fixture's actual verdict against `data/fixtures/expected.json` and exit
   0 only if all five match, otherwise exit 1.

### Requirement 7: Immunefi-format draft export

**User Story:** As a hunter, I want a reportable finding exported as an
Immunefi-format Markdown draft, so that I can paste it into the submission
form with minimal editing.

#### Acceptance Criteria

1. WHEN the verdict is REPORTABLE, THEN the copilot SHALL write
   `reports/<finding-id>.md` containing Title, Severity, Description,
   Impact, Proof of Concept, and Recommendation sections.
2. WHEN the verdict is NOT REPORTABLE, THEN the copilot SHALL write
   `reports/<finding-id>.md` as a short triage note clearly marked
   NOT REPORTABLE with the numbered reasons.
3. WHEN a report is written, THEN the copilot SHALL print the path of the
   file it wrote.

### Requirement 8: Web UI

**User Story:** As a hunter, I want the same pipeline in a browser page,
so that I can triage a finding without the terminal and share a working
app URL.

#### Acceptance Criteria

1. WHEN the user runs `python3 server.py`, THEN the web UI SHALL be served
   at `http://127.0.0.1:8000` with no dependencies to install.
2. WHEN the user picks a demo fixture or fills the finding form and runs
   triage, THEN the page SHALL show the verdict, the suggested severity,
   the numbered reasons, and the generated report draft with a download
   button.
3. WHEN the server triages a finding, THEN it SHALL run the same
   `triage.py` pipeline (not a separate implementation) and return
   report markdown byte-identical to the CLI's `reports/<id>.md`.
4. WHEN the user runs the demo self-check from the page, THEN it SHALL
   report the same 5/5 expected-vs-actual summary as `python3 triage.py
   --demo`.
