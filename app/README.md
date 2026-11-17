# app: the application

What the reviewer opens in the browser, and the same checks for AI agents. Start it with `python app/review_server.py` and open http://127.0.0.1:8520.

| File | What it does |
|---|---|
| `review_server.py` | the application's server: it serves the page and answers everything the page asks for (packages, review, confirmations, decisions, rules, BOQs, projects) |
| `review/` | the page itself, in plain HTML, CSS and JavaScript; `review/views/` holds one file per screen: `packages.js`, `review.js` (problems, readings, answer), `rules.js`, `add.js` (add a package), `booster.js` (booster sizing), `standby.js` (standby test) |
| `mcp_server.py` | the same checks as six read-only tools an AI agent can call (MCP); `.mcp.json` in the root tells an agent how to start it |
| `pump_demo.py` | reads an uploaded pump package page by page, and does the booster sizing and the standby test |
| `ai.py` | the only place the application asks an AI: turning a rule typed in words into a rule, and listing what a BOQ line asks; every answer is labelled AI |

The checks themselves are not here but in `checks/`. This folder shows them and keeps what the reviewer decides.
