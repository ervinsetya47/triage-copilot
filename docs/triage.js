/* Bug Bounty Triage Copilot — browser port of triage.py.
 *
 * Faithful port of the Python CLI pipeline: same rule files (see data.js,
 * generated from data/*.json), same six steps, same verdict logic, same
 * report markdown. No network, no LLM — everything runs in the browser.
 * If you change a rule in triage.py, regenerate data.js and mirror the
 * logic change here, then re-run the node self-check (see README).
 */

const REQUIRED_FIELDS = ["id", "title", "program", "target", "description", "poc_notes"];

const FIXTURE_IDS = [
  "charm-fake-pool",
  "everest-finding2",
  "everest-finding3",
  "everest-mempool",
  "relay-executor",
];

function haystack(finding) {
  return ["title", "description", "poc_notes"]
    .map((k) => String(finding[k] ?? ""))
    .join(" ")
    .toLowerCase();
}

function checkScope(finding, scopes) {
  const program = finding.program;
  if (!(program in scopes)) {
    return [false, `unknown program '${program}' — no scope entry`];
  }
  const entry = scopes[program];
  const text = (finding.target + " " + finding.description).toLowerCase();
  for (const target of entry.in_scope || []) {
    if (text.includes(target.toLowerCase())) {
      return [true, `target matches in-scope asset '${target}' (${program})`];
    }
  }
  return [false, `target '${finding.target}' is not in scope for ${program}`];
}

function matchEntries(finding, entries) {
  const text = haystack(finding);
  return entries.filter((e) =>
    e.keywords.some((kw) => text.includes(kw.toLowerCase()))
  );
}

function suggestSeverity(finding) {
  const text = haystack(finding);
  const program = finding.program;
  // Program-specific scale first (Relay S3/L2), then generic impact rules.
  if (program === "Relay" && text.includes("s3/l2")) {
    return "S3/L2 (High-class)";
  }
  if (["drain", "steal", "theft", "attacker gains", "sweep"].some((kw) => text.includes(kw))) {
    return "Critical-class";
  }
  if (["intended design", "documented intended"].some((kw) => text.includes(kw))) {
    return "Informational / not reportable";
  }
  if (["delay", "parked", "censor", "underpriced"].some((kw) => text.includes(kw))) {
    return "Medium";
  }
  if (["grief", "lock", "burn"].some((kw) => text.includes(kw))) {
    return "Medium at most";
  }
  return "Medium";
}

function validateFinding(finding) {
  if (!finding || typeof finding !== "object") {
    return "finding must be a JSON object";
  }
  const missing = REQUIRED_FIELDS.filter((f) => !(f in finding));
  if (missing.length) {
    return `missing required field(s): ${missing.join(", ")}`;
  }
  return null;
}

function triage(finding, data) {
  const steps = [];
  steps.push(`[1/6] Ingest: ${finding.id} — ${finding.title}`);

  const [inScope, scopeReason] = checkScope(finding, data.scopes);
  steps.push(`[2/6] Scope check: ${inScope ? "IN SCOPE" : "OUT OF SCOPE"} — ${scopeReason}`);

  const kis = matchEntries(finding, data.knownIssues);
  steps.push(
    kis.length
      ? "[3/6] Known-issue check: MATCH — " + kis.map((k) => `${k.id}: ${k.title}`).join("; ")
      : "[3/6] Known-issue check: no match"
  );

  const dis = matchEntries(finding, data.disclosures);
  steps.push(
    dis.length
      ? "[4/6] Disclosure check: MATCH — " + dis.map((d) => `${d.id} (${d.source})`).join("; ")
      : "[4/6] Disclosure check: no match"
  );

  const severity = suggestSeverity(finding);
  steps.push(`[5/6] Severity suggestion: ${severity}`);

  const reasons = [];
  if (!inScope) reasons.push(`Out of scope: ${scopeReason}.`);
  for (const k of kis) reasons.push(`Known issue: ${k.id} — ${k.title}.`);
  for (const d of dis) reasons.push(`Publicly disclosed: ${d.id} — ${d.title} (${d.source}).`);
  if (severity.startsWith("Informational")) {
    reasons.push("Intended design: severity is Informational, not reportable.");
  }

  const verdict = reasons.length ? "NOT REPORTABLE" : "REPORTABLE";
  if (verdict === "REPORTABLE") {
    reasons.push(
      `In scope, no known-issue match, no public-disclosure match; suggested severity ${severity}.`
    );
  }
  steps.push(`[6/6] Verdict: ${verdict}`);
  reasons.forEach((r, i) => steps.push(`      ${i + 1}. ${r}`));

  return {
    finding,
    inScope,
    scopeReason,
    knownIssues: kis,
    disclosures: dis,
    severity,
    verdict,
    reasons,
    steps,
  };
}

function buildReport(result) {
  const f = result.finding;
  if (result.verdict === "REPORTABLE") {
    return (
      `# ${f.title}\n\n` +
      `**Program:** ${f.program}  \n` +
      `**Target:** ${f.target}  \n` +
      `**Severity:** ${result.severity}  \n` +
      `**Verdict:** REPORTABLE (triage copilot)\n\n` +
      `## Description\n\n${f.description}\n\n` +
      `## Impact\n\n${result.severity} impact. ${f.description}\n\n` +
      `## Proof of Concept\n\n${f.poc_notes}\n\n` +
      `## Recommendation\n\n` +
      `Validate the affected target and restrict the vulnerable operation to authorized, validated inputs. Re-run the triage copilot after any fix to confirm the finding is closed.\n\n` +
      `---\n` +
      `*Draft generated by the Bug Bounty Triage Copilot. Review before submitting — the copilot never auto-submits.*\n`
    );
  }
  const lines = result.reasons.map((r, i) => `${i + 1}. ${r}`).join("\n");
  return (
    `# TRIAGE NOTE — NOT REPORTABLE: ${f.title}\n\n` +
    `**Program:** ${f.program}  \n` +
    `**Target:** ${f.target}  \n` +
    `**Suggested severity:** ${result.severity}  \n` +
    `**Verdict:** NOT REPORTABLE\n\n` +
    `## Why this finding is dead\n\n${lines}\n\n` +
    `## Finding summary (for the record)\n\n` +
    `${f.description}\n\n` +
    `**PoC notes:** ${f.poc_notes}\n\n` +
    `---\n` +
    `*Triage note generated by the Bug Bounty Triage Copilot. Do not submit this finding — the submission fee would be wasted.*\n`
  );
}

function runDemo(data) {
  return FIXTURE_IDS.map((fid) => {
    const fixture = data.fixtures[fid];
    if (!fixture) {
      return { id: fid, expected: data.expected[fid] || {}, verdict: "ERROR", severity: "—", ok: false, error: "MISSING" };
    }
    const result = triage(fixture, data);
    const exp = data.expected[fid] || {};
    const ok = result.verdict === exp.verdict && result.severity === exp.severity;
    return { id: fid, expected: exp, verdict: result.verdict, severity: result.severity, ok };
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    REQUIRED_FIELDS,
    FIXTURE_IDS,
    haystack,
    checkScope,
    matchEntries,
    suggestSeverity,
    validateFinding,
    triage,
    buildReport,
    runDemo,
  };
}
