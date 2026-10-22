---
name: sfg-vibe-coding
description: How anyone at SFG builds, publishes and hands over an app on the shared Claude Code platform, on top of the Sage 300 MCP. Load it before touching Sage data, before publishing anything, and whenever Sage says no.
---

# SFG vibe-coding skill

The shared platform lets anyone on the team build small apps on top of the Sage 300 data they already
have access to. This file is the contract every session follows. It is deliberately short; the worked
example is `projects/customer-orders/`.

## 1. Principles

1. **Read-only.** Apps read Sage only through the MCP server (`http://127.0.0.1:8765/mcp`). Nothing
   writes to Sage through the platform. A person enters every change (section 6).
2. **The token decides, not the prompt.** Every MCP call carries the requesting user's own token.
   What Sage masks or refuses stays masked or refused. Never borrow a token, never copy data out of
   another session, never guess a masked value, never build a workaround for a refusal.
3. **Views only.** If no published view holds the data, raise a view request (section 6). Never query
   raw tables, even when the SQL login could.
4. **Humans are named.** Requests go to the people in section 7, in the format given there. The
   project owner is notified of every view request, without exception.
5. **Small box.** The server has 2 vCPU, 913 MB RAM and no swap. One process at a time, `MemoryMax`
   on every service, `nice` for installs and tests, `free -m` before starting anything.

## 2. Before building

- Read this file, then the handover docs of the neighbouring projects in `projects/*/README.md`.
- Read the Sage documentation: `/home/ec2-user/mock-sage-300/README.md` (views, the two permission
  layers, the demo roles) and the view notes under `sql/`.
- Check what the requester may see **with their token**: call `whoami` (companies open or refused,
  `cost_visible`) and `list_views` (readable views, masked columns). Build for what comes back.
- Check the MCP tools on offer (`list_views`, `query`, `posting_journals`, `sales_master`,
  `customer_order_history`, `item_costs`, `users`) before writing SQL of your own.

## 3. Build standards

- **Stack:** Python 3.12, Flask, gunicorn (1 worker, 4 threads), one `.venv` per project, the
  standard-library HTTP client to MCP (copy `projects/customer-orders/mcp_client.py`), no database
  of its own, no secrets in the repo.
- **Naming:** project = lowercase-hyphen noun phrase (`customer-orders`). Repo path
  `projects/<name>/`, URL `https://44.218.227.134/<name>/`, service `sfg-<name>`, port from the
  table in the root `README.md` (next free from 8102).
- **Look (the house standard):** the SFG wordmark as text in the top bar, `SFG <App name>`, in the
  display face Fraunces with a small uppercase caption; palette and type tokens copied from
  `projects/customer-orders/static/style.css` (accent `#0f4c81`, body Public Sans). No raster logo
  exists in the knowledge base. Do not invent one; do not restyle the tokens.
- **Every page footer:** app name, "read-only via Sage MCP", link to the handover doc, and who is
  signed in.
- **When Sage says no:** show the MCP message verbatim and name who to ask (section 7). Never hide a
  refusal behind a generic error, and never fall back to a token with more rights.
- **Tests:** pytest. Unit tests with a fake MCP; integration tests against the live MCP that skip
  when it is not reachable. The suite must pass before publishing.

## 4. Publish (deploy beside the other apps)

- Ship `deploy/sfg-<name>.service` (`MemoryMax`, `ProtectSystem=strict`), `deploy/nginx-location.conf`
  and an idempotent `deploy/install.sh` that a person runs with sudo.
- nginx: a `location /<name>` proxying to `127.0.0.1:<port>`, inserted before the catch-all in
  `/etc/nginx/conf.d/hello.conf`; keep the copy `/opt/sfg-kb/nginx-kb.conf` in sync.
- Index: add the app to the knowledge base navigation (`/opt/sfg-kb/templates/base.html`) and to the
  project table in the root `README.md`. That table is the company index of projects.
- Verify after deploy: `https://44.218.227.134/<name>/healthz` and one signed-in page with a demo
  token that has rights and one that does not.

## 5. Save to GitHub and hand over

- Repository `BestPracticeAI/SFG_vibe_coding`, branch `main`, one commit per change, message says
  what and why. `.gitignore` the venv, caches, tokens and `.env` files.
- Handover doc `projects/<name>/README.md`: an executive summary first (what, for whom, where, which
  data, status, open requests, in five lines), then the full description: how it works, the privilege
  behaviour, how to run, test and deploy, the open requests, and who to contact.

## 6. Two requests that always go through a person

### Write to Sage

- **Goes to:** the Sage administrator (section 7), copy to the requester.
- **They receive:** company and screen, record key (order number, customer number, item), the field
  with its current and new value, business reason, requester and app name, link to the evidence query.
- **They enter:** the change by hand in the normal Sage screen under their own login, then reply with
  the audit or posting reference.
- **Notified:** requester and project owner get the reply; the app records it in its changelog.
- **Subject line:** `Sage change request · <app> · <company> · <record>`.

### New view

- **Goes to:** the Sage champion (section 7). The project owner is notified on every request and
  again on completion, without exception.
- **They receive:** proposed view name (`vSfg<Subject>`), columns and source tables, grain (one row
  per what) and filters, a sample row, which Sage groups may see cost columns, business reason,
  requesting app.
- **They create:** the view in the read-only schema, document it in the views list, grant it to the
  SQL login, and confirm it is live.
- **Then:** the session rebuilds the page on the new view and updates the handover doc.
- **Subject line:** `View request · <app> · <proposed view name>`.

## 7. People

Fill in the names before the demo. Until then the roles are stand-ins; do not invent names.

| Role | Name | Contact | Ask them for |
| --- | --- | --- | --- |
| Sage administrator | [name] | [email] | writes to Sage, access and cost rights, tokens |
| Sage champion | [name] | [email] | new views and view changes |
| Project owner | [name] | [email] | priorities; notified of every view request |
| Platform champion | [name] | [email] | the shared session, deployment, this skill file |

How to contact them: one request per email, the subject line from section 6, the template filled in
full, and the MCP output attached as evidence. On the mock estate the demo tokens are
`sage-mock-<role>` (controller, integrator, salesmanager, shopfloor, finance, intern, stockroom,
leftco, jdoe, vpsales, powerbi); see `/home/ec2-user/mock-sage-300/README.md`.
