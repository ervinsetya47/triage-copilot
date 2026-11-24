#!/usr/bin/env python3
"""Bug Bounty Triage Copilot — deterministic, rule-based triage CLI.

Usage:
    python3 triage.py <finding.json>   triage one finding, write reports/<id>.md
    python3 triage.py --demo           run all 5 fixtures, exit 0 iff all match
    python3 triage.py --check-draft <reports/<id>.md>
                                       hook: re-check a saved draft's verdict

Python 3 stdlib only. No network, no LLM. Every check is an explicit rule
in data/*.json, so any verdict can be audited back to the rule that made it.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
REPORTS = BASE / "reports"

REQUIRED_FIELDS = ["id", "title", "program", "target", "description", "poc_notes"]

FIXTURE_IDS = [
    "charm-fake-pool",
    "everest-finding2",
    "everest-finding3",
    "everest-mempool",
    "relay-executor",
]


# ---------------------------------------------------------------- data loading

def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        die(f"data file missing: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")


def die(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def load_data():
    return {
        "scopes": load_json(DATA / "scopes.json")["programs"],
        "known_issues": load_json(DATA / "known_issues.json")["known_issues"],
        "disclosures": load_json(DATA / "disclosures.json")["disclosures"],
    }


# ---------------------------------------------------------------- pipeline

def load_finding(path):
    try:
        with open(path, encoding="utf-8") as f:
            finding = json.load(f)
    except FileNotFoundError:
        die(f"finding file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(finding, dict):
        die(f"{path}: finding must be a JSON object")
    missing = [f for f in REQUIRED_FIELDS if f not in finding]
    if missing:
        die(f"{path}: missing required field(s): {', '.join(missing)}")
    return finding


def haystack(finding):
    return " ".join(
        str(finding[k]) for k in ("title", "description", "poc_notes")
    ).lower()


def check_scope(finding, scopes):
    program = finding["program"]
    if program not in scopes:
        return False, f"unknown program '{program}' — no scope entry"
    entry = scopes[program]
    text = (finding["target"] + " " + finding["description"]).lower()
    for target in entry.get("in_scope", []):
        if target.lower() in text:
            return True, f"target matches in-scope asset '{target}' ({program})"
    return False, f"target '{finding['target']}' is not in scope for {program}"


def match_entries(finding, entries):
    text = haystack(finding)
    return [e for e in entries if any(kw.lower() in text for kw in e["keywords"])]


def suggest_severity(finding):
    text = haystack(finding)
    program = finding["program"]
    # Program-specific scale first (Relay S3/L2), then generic impact rules.
    if program == "Relay" and "s3/l2" in text:
        return "S3/L2 (High-class)"
    if any(kw in text for kw in ("drain", "steal", "theft", "attacker gains", "sweep")):
        return "Critical-class"
    if any(kw in text for kw in ("intended design", "documented intended")):
        return "Informational / not reportable"
    if any(kw in text for kw in ("delay", "parked", "censor", "underpriced")):
        return "Medium"
    if any(kw in text for kw in ("grief", "lock", "burn")):
        return "Medium at most"
    return "Medium"


def triage(finding, data, verbose=True):
    """Run the full pipeline; return a verdict dict. Prints step lines."""
    if verbose:
        print(f"[1/6] Ingest: {finding['id']} — {finding['title']}")

    in_scope, scope_reason = check_scope(finding, data["scopes"])
    if verbose:
        print(f"[2/6] Scope check: {'IN SCOPE' if in_scope else 'OUT OF SCOPE'} — {scope_reason}")

    kis = match_entries(finding, data["known_issues"])
    if verbose:
        if kis:
            print("[3/6] Known-issue check: MATCH — " + "; ".join(
                f"{k['id']}: {k['title']}" for k in kis))
        else:
            print("[3/6] Known-issue check: no match")

    dis = match_entries(finding, data["disclosures"])
    if verbose:
        if dis:
            print("[4/6] Disclosure check: MATCH — " + "; ".join(
                f"{d['id']} ({d['source']})" for d in dis))
        else:
            print("[4/6] Disclosure check: no match")

    severity = suggest_severity(finding)
    if verbose:
        print(f"[5/6] Severity suggestion: {severity}")

    reasons = []
    if not in_scope:
        reasons.append(f"Out of scope: {scope_reason}.")
    for k in kis:
        reasons.append(f"Known issue: {k['id']} — {k['title']}.")
    for d in dis:
        reasons.append(f"Publicly disclosed: {d['id']} — {d['title']} ({d['source']}).")
    if severity.startswith("Informational"):
        reasons.append("Intended design: severity is Informational, not reportable.")

    verdict = "NOT REPORTABLE" if reasons else "REPORTABLE"
    if verdict == "REPORTABLE":
        reasons.append(
            f"In scope, no known-issue match, no public-disclosure match; "
            f"suggested severity {severity}."
        )
    if verbose:
        print(f"[6/6] Verdict: {verdict}")
        for i, reason in enumerate(reasons, 1):
            print(f"      {i}. {reason}")

    return {
        "finding": finding,
        "in_scope": in_scope,
        "scope_reason": scope_reason,
        "known_issues": kis,
        "disclosures": dis,
        "severity": severity,
        "verdict": verdict,
        "reasons": reasons,
    }


# ---------------------------------------------------------------- report export

def build_report(result):
    """Build the report markdown for a triage result. Pure function —
    the web server reuses it so the CLI and the web UI draft byte-identical
    reports from the same pipeline."""
    finding = result["finding"]
    if result["verdict"] == "REPORTABLE":
        return (
            f"# {finding['title']}\n\n"
            f"**Program:** {finding['program']}  \n"
            f"**Target:** {finding['target']}  \n"
            f"**Severity:** {result['severity']}  \n"
            f"**Verdict:** REPORTABLE (triage copilot)\n\n"
            f"## Description\n\n{finding['description']}\n\n"
            f"## Impact\n\n{result['severity']} impact. "
            f"{finding['description']}\n\n"
            f"## Proof of Concept\n\n{finding['poc_notes']}\n\n"
            f"## Recommendation\n\n"
            f"Validate the affected target and restrict the vulnerable "
            f"operation to authorized, validated inputs. Re-run the "
            f"triage copilot after any fix to confirm the finding is closed.\n\n"
            f"---\n"
            f"*Draft generated by the Bug Bounty Triage Copilot. "
            f"Review before submitting — the copilot never auto-submits.*\n"
        )
    lines = "\n".join(
        f"{i}. {r}" for i, r in enumerate(result["reasons"], 1)
    )
    return (
        f"# TRIAGE NOTE — NOT REPORTABLE: {finding['title']}\n\n"
        f"**Program:** {finding['program']}  \n"
        f"**Target:** {finding['target']}  \n"
        f"**Suggested severity:** {result['severity']}  \n"
        f"**Verdict:** NOT REPORTABLE\n\n"
        f"## Why this finding is dead\n\n{lines}\n\n"
        f"## Finding summary (for the record)\n\n"
        f"{finding['description']}\n\n"
        f"**PoC notes:** {finding['poc_notes']}\n\n"
        f"---\n"
        f"*Triage note generated by the Bug Bounty Triage Copilot. "
        f"Do not submit this finding — the submission fee would be wasted.*\n"
    )


def write_report(result):
    finding = result["finding"]
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"{finding['id']}.md"
    path.write_text(build_report(result), encoding="utf-8")
    print(f"Report written: {path}")
    return path


# ---------------------------------------------------------------- demo & hooks

def run_demo(data):
    expected = load_json(DATA / "fixtures" / "expected.json")
    rows = []
    for fid in FIXTURE_IDS:
        fixture = DATA / "fixtures" / f"{fid}.json"
        if not fixture.exists():
            rows.append((fid, expected.get(fid, {}).get("verdict", "?"), "ERROR", "MISSING"))
            continue
        finding = load_finding(fixture)
        result = triage(finding, data, verbose=False)
        exp = expected.get(fid, {})
        match = (
            result["verdict"] == exp.get("verdict")
            and result["severity"] == exp.get("severity")
        )
        rows.append((fid, exp.get("verdict", "?"), result["verdict"],
                     result["severity"], "OK" if match else "MISMATCH"))
        write_report(result)

    print("\nDemo summary — expected vs actual")
    print(f"{'fixture':<20} {'expected':<16} {'actual':<16} {'severity':<28} result")
    print("-" * 95)
    all_ok = True
    for fid, exp_v, act_v, sev, status in rows:
        print(f"{fid:<20} {exp_v:<16} {act_v:<16} {sev:<28} {status}")
        if status != "OK":
            all_ok = False
    print(f"\n{sum(1 for r in rows if r[-1] == 'OK')}/{len(rows)} fixtures match.")
    return 0 if all_ok else 1


def check_draft(draft_path):
    """Hook entry point: re-run triage for the finding behind a saved draft
    and confirm the draft's verdict line still matches the pipeline."""
    draft = Path(draft_path)
    if not draft.exists():
        die(f"draft not found: {draft_path}")
    fid = draft.stem
    fixture = DATA / "fixtures" / f"{fid}.json"
    if not fixture.exists():
        print(f"check-draft: no fixture for '{fid}'; nothing to re-check.")
        return 0
    data = load_data()
    result = triage(load_finding(fixture), data, verbose=False)
    text = draft.read_text(encoding="utf-8")
    verdict_in_draft = "NOT REPORTABLE" if "NOT REPORTABLE" in text else "REPORTABLE"
    if verdict_in_draft != result["verdict"]:
        print(
            f"check-draft: MISMATCH — draft says {verdict_in_draft}, "
            f"pipeline says {result['verdict']}. Regenerate the draft."
        )
        return 1
    print(f"check-draft: OK — draft verdict matches pipeline ({result['verdict']}).")
    return 0


# ---------------------------------------------------------------- main

def main(argv):
    if len(argv) == 2 and argv[1] == "--demo":
        return run_demo(load_data())
    if len(argv) == 3 and argv[1] == "--check-draft":
        return check_draft(argv[2])
    if len(argv) == 2 and not argv[1].startswith("-"):
        finding = load_finding(argv[1])
        result = triage(finding, load_data())
        write_report(result)
        return 0
    print(
        "usage:\n"
        "  python3 triage.py <finding.json>   triage one finding\n"
        "  python3 triage.py --demo           run all 5 demo fixtures\n"
        "  python3 triage.py --check-draft <reports/<id>.md>\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
