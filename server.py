#!/usr/bin/env python3
"""Bug Bounty Triage Copilot — web UI around the same triage engine.

Serves one page (form fields or a demo fixture) and runs the real
``triage.py`` pipeline server-side. Python 3 standard library only —
no pip dependencies, no network calls, no LLM.

Run:
    python3 server.py            # http://127.0.0.1:8000

Endpoints:
    GET  /                     the web UI (single page)
    GET  /api/fixtures         list of the 5 demo fixtures (id, title, program)
    GET  /api/fixtures/<id>    one fixture as JSON
    GET  /api/demo             run all 5 fixtures, return the summary table
    POST /api/triage           {"id","title","program","target","description",
                               "poc_notes"} -> verdict + report markdown

The server never writes files and never submits anything; it only
answers with JSON. For a public URL, deploy the static app in docs/
(GitHub Pages) or host this server — see README.md.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import triage  # noqa: E402  (same repo, stdlib-only engine)

# Bind address/port are overridable for hosting (e.g. Render sets $PORT).
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
MAX_BODY = 1_000_000  # 1 MB

DATA = triage.load_data()

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bug Bounty Triage Copilot — web</title>
<style>
  :root { --bg:#0f1115; --panel:#171a21; --line:#2a2f3a; --text:#e8eaf0; --muted:#9aa3b2;
          --green:#3fb950; --red:#f85149; --accent:#58a6ff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
  main { max-width:880px; margin:0 auto; padding:32px 20px 64px; }
  h1 { font-size:28px; margin:0 0 4px; }
  h2 { font-size:18px; margin:28px 0 8px; }
  p.sub { color:var(--muted); margin:0 0 20px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px 18px; }
  .fixtures { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 12px; }
  button { background:#21262d; color:var(--text); border:1px solid var(--line); border-radius:8px;
           padding:8px 14px; font-size:14px; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); color:#04122b; border-color:var(--accent); font-weight:600; }
  label { display:block; font-size:14px; color:var(--muted); margin:10px 0 4px; }
  input, select, textarea { width:100%; background:#0d1017; color:var(--text);
             border:1px solid var(--line); border-radius:8px; padding:10px 12px;
             font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
  textarea { min-height:110px; font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; }
  pre { background:#0d1017; border:1px solid var(--line); border-radius:8px; padding:12px;
        white-space:pre-wrap; word-break:break-word; font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; }
  .verdict { font-size:20px; font-weight:700; padding:10px 14px; border-radius:8px; display:inline-block; }
  .verdict.ok { background:rgba(63,185,80,.15); color:var(--green); border:1px solid var(--green); }
  .verdict.no { background:rgba(248,81,73,.12); color:var(--red); border:1px solid var(--red); }
  .muted { color:var(--muted); font-size:14px; }
  .steps { margin:12px 0 0; padding-left:20px; }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:12px; }
  .hidden { display:none; }
  .err { color:var(--red); }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }
  footer { margin-top:36px; color:var(--muted); font-size:13px; }
  code { background:#0d1017; padding:1px 6px; border-radius:5px; font-size:13px; }
</style>
</head>
<body>
<main>
  <h1>🛡️ Bug Bounty Triage Copilot</h1>
  <p class="sub">Check a finding <em>before</em> you pay the submission fee. Same engine as the
  CLI (<code>python3 triage.py</code>) — scope, known issues, public disclosures, severity,
  one verdict, and a report draft if the finding is alive. Deterministic, rule-based,
  no LLM, no network. <strong>The copilot never auto-submits anything.</strong></p>

  <h2>1 · Pick a demo finding — or write your own</h2>
  <div class="panel">
    <div class="fixtures" id="fixtures"></div>
    <label for="fid">Finding id</label>
    <input id="fid" value="charm-fake-pool">
    <label for="title">Title</label>
    <input id="title">
    <label for="program">Program</label>
    <select id="program"><option>Charm</option><option>Base Everest</option><option>Relay</option></select>
    <label for="target">Target (in-scope asset)</label>
    <input id="target">
    <label for="desc">Description</label>
    <textarea id="desc"></textarea>
    <label for="poc">PoC notes</label>
    <textarea id="poc"></textarea>
    <div class="row">
      <button class="primary" id="run">Run triage</button>
      <button id="demo">Run all 5 demo fixtures</button>
      <span class="muted" id="hint"></span>
    </div>
  </div>

  <div id="result" class="hidden">
    <h2>2 · Verdict</h2>
    <div class="panel">
      <span id="verdict" class="verdict"></span>
      <span id="severity" class="muted" style="margin-left:10px"></span>
      <ol class="steps" id="reasons"></ol>
      <p class="muted" id="checks"></p>
    </div>

    <h2>3 · Report draft</h2>
    <div class="panel">
      <pre id="report"></pre>
      <div class="row">
        <button id="copy">Copy report</button>
        <button id="download">Download .md</button>
      </div>
    </div>
  </div>

  <div id="demoOut" class="hidden">
    <h2>Demo self-check — expected vs actual</h2>
    <div class="panel"><table>
      <thead><tr><th>Fixture</th><th>Expected</th><th>Actual</th><th>Severity</th><th></th></tr></thead>
      <tbody id="demoRows"></tbody>
    </table>
    <p id="demoSummary" class="muted"></p></div>
  </div>

  <footer>
    Powered by <code>triage.py</code> — the same deterministic pipeline as the CLI.
    Rules live in <code>data/scopes.json</code>, <code>data/known_issues.json</code> and
    <code>data/disclosures.json</code>. Kiroween 2026, category Frankenstein.
  </footer>
</main>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  const fields = ["fid", "title", "program", "target", "desc", "poc"];
  let lastReport = "", lastId = "finding";

  function findingFromForm() {
    return {
      id: $("fid").value.trim(),
      title: $("title").value.trim(),
      program: $("program").value,
      target: $("target").value.trim(),
      description: $("desc").value.trim(),
      poc_notes: $("poc").value.trim(),
    };
  }
  function fillForm(f) {
    $("fid").value = f.id || "";
    $("title").value = f.title || "";
    $("program").value = f.program || "Charm";
    $("target").value = f.target || "";
    $("desc").value = f.description || "";
    $("poc").value = f.poc_notes || "";
  }
  async function api(path, opts) {
    const r = await fetch(path, opts);
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  function showResult(r) {
    const v = $("verdict");
    v.textContent = "Verdict: " + r.verdict;
    v.className = "verdict " + (r.verdict === "REPORTABLE" ? "ok" : "no");
    $("severity").textContent = "Suggested severity: " + r.severity;
    $("reasons").innerHTML = "";
    r.reasons.forEach((reason) => {
      const li = document.createElement("li");
      li.textContent = reason;
      $("reasons").appendChild(li);
    });
    const ki = r.known_issues.map((k) => k.id).join(", ") || "none";
    const dis = r.disclosures.map((d) => d.id).join(", ") || "none";
    $("checks").textContent =
      "Scope: " + (r.in_scope ? "in scope" : "out of scope") + " — " + r.scope_reason +
      " · Known issues: " + ki + " · Disclosures: " + dis + ".";
    lastReport = r.report;
    lastId = r.finding.id;
    $("report").textContent = lastReport;
    $("result").classList.remove("hidden");
    $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Fixture buttons + default finding.
  api("/api/fixtures").then((list) => {
    list.forEach((f) => {
      const b = document.createElement("button");
      b.textContent = f.id;
      b.onclick = async () => {
        try { fillForm(await api("/api/fixtures/" + encodeURIComponent(f.id))); $("hint").textContent = ""; }
        catch (e) { $("hint").textContent = e.message; $("hint").className = "err"; }
      };
      $("fixtures").appendChild(b);
    });
    return api("/api/fixtures/charm-fake-pool");
  }).then(fillForm).catch((e) => { $("hint").textContent = e.message; $("hint").className = "err"; });

  $("run").onclick = async () => {
    try {
      const r = await api("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(findingFromForm()),
      });
      $("hint").textContent = "";
      showResult(r);
    } catch (e) { $("hint").textContent = e.message; $("hint").className = "err"; }
  };

  $("demo").onclick = async () => {
    try {
      const d = await api("/api/demo");
      $("demoRows").innerHTML = "";
      d.rows.forEach((r) => {
        const tr = document.createElement("tr");
        [r.id, r.expected, r.actual, r.severity, r.ok ? "✅ OK" : "❌ MISMATCH"].forEach((t) => {
          const td = document.createElement("td");
          td.textContent = t;
          tr.appendChild(td);
        });
        $("demoRows").appendChild(tr);
      });
      $("demoSummary").textContent = d.matched + "/" + d.rows.length + " fixtures match their expected verdicts.";
      $("demoOut").classList.remove("hidden");
      $("demoOut").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) { $("hint").textContent = e.message; $("hint").className = "err"; }
  };

  $("copy").onclick = async () => {
    try { await navigator.clipboard.writeText(lastReport); $("copy").textContent = "Copied ✓"; }
    catch (e) { alert("Copy failed — select the text manually."); }
    setTimeout(() => { $("copy").textContent = "Copy report"; }, 2000);
  };
  $("download").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lastReport], { type: "text/markdown" }));
    a.download = lastId + ".md";
    a.click();
    URL.revokeObjectURL(a.href);
  };
})();
</script>
</body>
</html>
"""


def result_payload(result):
    return {
        "finding": result["finding"],
        "in_scope": result["in_scope"],
        "scope_reason": result["scope_reason"],
        "known_issues": [
            {"id": k["id"], "title": k["title"]} for k in result["known_issues"]
        ],
        "disclosures": [
            {"id": d["id"], "title": d["title"], "source": d["source"]}
            for d in result["disclosures"]
        ],
        "severity": result["severity"],
        "verdict": result["verdict"],
        "reasons": result["reasons"],
        "report": triage.build_report(result),
    }


def validate_finding(body):
    if not isinstance(body, dict):
        return None, "finding must be a JSON object"
    missing = [f for f in triage.REQUIRED_FIELDS if f not in body]
    if missing:
        return None, f"missing required field(s): {', '.join(missing)}"
    bad = [f for f in triage.REQUIRED_FIELDS if not isinstance(body[f], str)]
    if bad:
        return None, f"field(s) must be strings: {', '.join(bad)}"
    return body, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep stdout clean
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_page(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.send_page()
        if parsed.path == "/api/fixtures":
            return self.send_json([
                {"id": fid, "title": self._fixture(fid)["title"],
                 "program": self._fixture(fid)["program"]}
                for fid in triage.FIXTURE_IDS
            ])
        if parsed.path.startswith("/api/fixtures/"):
            fid = unquote(parsed.path[len("/api/fixtures/"):])
            if fid not in triage.FIXTURE_IDS:
                return self.send_json({"error": f"unknown fixture '{fid}'"}, 404)
            return self.send_json(self._fixture(fid))
        if parsed.path == "/api/demo":
            return self.send_json(self._demo())
        return self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/triage":
            return self.send_json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_json({"error": "request body too large"}, 413)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            return self.send_json({"error": f"invalid JSON: {exc}"}, 400)
        finding, err = validate_finding(body)
        if err:
            return self.send_json({"error": err}, 400)
        result = triage.triage(finding, DATA, verbose=False)
        return self.send_json(result_payload(result))

    @staticmethod
    def _fixture(fid):
        return triage.load_finding(triage.DATA / "fixtures" / f"{fid}.json")

    def _demo(self):
        expected = triage.load_json(triage.DATA / "fixtures" / "expected.json")
        rows, matched = [], 0
        for fid in triage.FIXTURE_IDS:
            result = triage.triage(self._fixture(fid), DATA, verbose=False)
            exp = expected.get(fid, {})
            ok = (result["verdict"] == exp.get("verdict")
                  and result["severity"] == exp.get("severity"))
            matched += 1 if ok else 0
            rows.append({
                "id": fid, "expected": exp.get("verdict", "?"),
                "actual": result["verdict"], "severity": result["severity"],
                "ok": ok,
            })
        return {"rows": rows, "matched": matched, "all_ok": matched == len(rows)}


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Bug Bounty Triage Copilot — web UI at http://{HOST}:{PORT}/")
    print("Same engine as the CLI (triage.py). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
