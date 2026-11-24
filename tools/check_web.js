#!/usr/bin/env node
/* Self-check for the web port: run the browser triage logic (docs/triage.js)
 * over the same 5 fixtures with the same rules (docs/data.js) and compare
 * verdict + severity against data/fixtures/expected.json — the same check
 * `python3 triage.py --demo` performs for the CLI. Exit 0 iff 5/5 match.
 *
 * Usage: node tools/check_web.js
 */
const { triage, buildReport, runDemo } = require("../docs/triage.js");
const data = require("../docs/data.js");
const fs = require("fs");
const path = require("path");

const rows = runDemo(data);
console.log("Web self-check — expected vs actual");
console.log("fixture              expected         actual           severity                      result");
console.log("-".repeat(100));
let allOk = true;
for (const r of rows) {
  const expV = (r.expected && r.expected.verdict) || "?";
  console.log(
    `${r.id.padEnd(20)} ${expV.padEnd(16)} ${String(r.verdict).padEnd(16)} ${String(r.severity).padEnd(28)} ${r.ok ? "OK" : "MISMATCH"}`
  );
  if (!r.ok) allOk = false;
}
console.log(`\n${rows.filter((r) => r.ok).length}/${rows.length} fixtures match.`);

// Also check the generated report markdown matches the CLI's reports/ files.
const reportsDir = path.join(__dirname, "..", "reports");
let reportsOk = true;
for (const fid of ["charm-fake-pool", "everest-finding2", "everest-finding3", "everest-mempool", "relay-executor"]) {
  const result = triage(data.fixtures[fid], data);
  const webReport = buildReport(result);
  const cliReport = fs.readFileSync(path.join(reportsDir, `${fid}.md`), "utf-8");
  const match = webReport === cliReport;
  console.log(`report ${fid}.md: ${match ? "identical to CLI" : "DIFFERS from CLI"}`);
  if (!match) reportsOk = false;
}

if (!allOk || !reportsOk) process.exit(1);
console.log("\nWeb port verified: same verdicts, same severity, same reports as the CLI.");
