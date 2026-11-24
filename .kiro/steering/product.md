# Product Guidance — Bug Bounty Triage Copilot

## What this is

A CLI copilot for a solo bug bounty hunter. It triages a candidate finding
*before* the hunter spends a submission fee: scope, known issues, public
disclosures, severity — then a single verdict and, if the finding is alive,
an Immunefi-format report draft.

## Who it serves

One person: a solo hunter who works in short bursts, submits to Immunefi
programs (Charm, Base Everest, Relay, …), and pays a fee per report. The
hunter's time and money are the scarce resources; the copilot's job is to
protect both.

## Triage philosophy

1. **Never auto-submit.** The copilot drafts; the human submits. No
   submission, no API call to any bounty platform, ever.
2. **Evidence first.** A verdict without a cited reason is worthless. Every
   reason names the check and the entry that triggered it (KI id, audit
   report, disclosure source).
3. **Honest severity.** The copilot suggests a severity class from impact
   keywords; it never inflates. A Medium is a Medium, even if the hunter
   wishes it were a Critical.
4. **A dead finding is a saved submission fee.** NOT REPORTABLE is a
   success, not a failure. Killing a finding in ten seconds is the whole
   point — the hunter keeps the fee and the triage time.
5. **Deterministic and auditable.** All checks are explicit rules in JSON
   data files. No LLM, no network, no hidden judgment. If a verdict is
   wrong, the hunter can point at the exact rule and fix it.
6. **Scope is literal.** Only the program's named in-scope assets count.
   An interpretation is not scope.

## Out of scope for this product

- Automated submission to Immunefi or any platform.
- Live fetching of program scopes, audit reports, or prices.
- LLM-based analysis of findings.
- Anything that spends money.
