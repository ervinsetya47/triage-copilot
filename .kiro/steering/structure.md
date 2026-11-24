# Structure Guidance — Bug Bounty Triage Copilot

## Repo layout

```
triage-copilot/
├── triage.py                  # CLI entry point (Python 3 stdlib only)
├── server.py                  # Web UI (stdlib http.server, port 8000)
├── README.md                  # Install / run instructions
├── DEMO_SCRIPT.md             # 2–3 minute demo walkthrough
├── KIRO_USE_WRITEUP.md        # Devpost write-up: how Kiro was used
├── LICENSE                    # MIT
├── Dockerfile                 # Minimal image for hosting server.py
├── docs/                      # Static web app (GitHub Pages): index.html, triage.js, data.js
├── tools/                     # build_web_data.py, check_web.js
├── .kiro/
│   ├── specs/triage-copilot/
│   │   ├── requirements.md    # EARS-style requirements
│   │   ├── design.md          # Architecture & data model
│   │   └── tasks.md           # Implementation task list
│   ├── steering/
│   │   ├── product.md         # Product guidance
│   │   ├── tech.md            # Tech guidance
│   │   └── structure.md       # This file
│   └── hooks/
│       └── report-draft-check.json   # Hook: re-check verdict on report save
├── data/
│   ├── scopes.json            # Program scopes (Charm, Base Everest, Relay)
│   ├── known_issues.json      # Published Known Issues
│   ├── disclosures.json       # Public disclosures
│   └── fixtures/
│       ├── expected.json      # Expected verdicts (demo check only)
│       ├── charm-fake-pool.json
│       ├── everest-finding2.json
│       ├── everest-finding3.json
│       ├── everest-mempool.json
│       └── relay-executor.json
└── reports/                   # Generated drafts (one .md per finding)
```

## Where things live

- **Pipeline code:** `triage.py` only. One function per stage.
- **Rules and data:** `data/*.json`. Edit data to change behaviour, not code.
- **Fixtures:** `data/fixtures/`. Exactly five, matching the real findings
  they encode. Add a new fixture + expected verdict to extend the demo.
- **Generated output:** `reports/`. Never hand-edit a generated draft
  without re-running the copilot — the hook in `.kiro/hooks/` re-checks
  the verdict on save.
- **Web UI:** `server.py` serves one page and runs the same `triage.py`
  engine in-process (`POST /api/triage`). The static app in `docs/` is a
  JS port for GitHub Pages; `tools/check_web.js` keeps the port in
  agreement with the CLI.
- **Kiro surfaces:** `.kiro/` holds the spec, steering, and hook files.
  They are the record of how Kiro was used to build this project.
