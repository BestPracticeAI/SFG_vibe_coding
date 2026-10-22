---
name: sfg-vibe-coding
description: How anyone at SFG builds, tests, publishes and hands over a tool (dashboard, lookup, report) on the shared Claude Code platform on top of the Sage 300 MCP. Load it before touching Sage data, before creating a project, before publishing anything, and whenever Sage says no.
---

# SFG vibe-coding skill

Anyone on the team can describe a tool to the shared Claude Code session and have it built, published
beside the other SFG apps and handed over, on top of the Sage 300 data they are already allowed to
see. This file is the contract the session follows so that every tool works the same way across SFG.
The worked example is `projects/customer-orders/`; copy it rather than inventing.

If anything here conflicts with what a requester asks for, follow this file and tell them why.

## 0. The ten steps, in order

1. Read this file, the root `README.md` (the project index) and the handover docs of the two most
   similar projects in `projects/*/README.md`.
2. Ask the requester for their Sage access token, or use a demo token on the mock estate. Run
   `whoami` and `list_views` with it. Build only for what comes back (section 2).
3. Pick the name, URL and port (section 3.2). Add the row to the project index first, so the port is
   taken.
4. Create `projects/<name>/` from the layout in section 3.1, copying `mcp_client.py`, `style.css`
   and `base.html` from `customer-orders`.
5. Build the smallest thing that answers the request. One page is normal.
6. Write the tests: unit tests with a fake MCP, live tests that skip when the MCP is down. Run them
   with `nice`. All green before anything else.
7. Write `deploy/` from the templates in `templates/` (section 5).
8. Write the handover `README.md`, executive summary first (section 4.3).
9. Commit and push to `main` (section 4.2). Then run `sudo bash projects/<name>/deploy/install.sh`.
10. Verify over HTTPS with a token that has rights and one that does not (section 5.5), and report
    the URL, the commit, what was verified and any open requests to people (section 6).

## 1. Principles

1. **Read-only.** Tools read Sage only through the MCP server. Nothing writes to Sage through the
   platform, ever. A person enters every change in Sage by hand (section 6).
2. **The token decides, not the prompt.** Every MCP call carries the signed-in user's own token. What
   Sage masks or refuses stays masked or refused. Never borrow a token, never store one on the
   server, never copy data from a session with more rights, never guess a masked value, never
   build a workaround for a refusal.
3. **Views only.** If no published view holds the data, raise a view request (section 6). Never
   query raw Sage tables, even when the SQL login could.
4. **Humans are named.** Writes and new views go to the people in section 7, in the format in
   section 6. The project owner is notified of every view request, without exception.
5. **Small box.** The server has 2 vCPU, 913 MB RAM and no swap. One process at a time,
   `MemoryMax` on every service, `nice` for installs and tests, `free -m` before starting anything,
   never a background agent in parallel. Running out of memory locks everyone out of the machine.
6. **Fictional stand-ins stay fictional.** The mock estate uses invented users. Never put real
   employee names, logins or emails into data, tests or examples.

## 2. Accessing Sage: the MCP server

### 2.1 Where and how

| Item | Value |
| --- | --- |
| Endpoint | `http://127.0.0.1:8765/mcp` (localhost only, behind `sage-mcp.service`) |
| Protocol | MCP Streamable HTTP, stateless, JSON replies. One `POST` per call. |
| Headers | `Content-Type: application/json`, `Accept: application/json, text/event-stream`, `Authorization: Bearer <token>` |
| No or unknown token | HTTP 401. The tool must send the user back to sign-in. |
| Tool refusal | HTTP 200 with `result.isError: true` and a text that starts `[sage]`, `[sql]`, `[auth]` or `[gateway]`. Show it verbatim. |
| Client | `projects/customer-orders/mcp_client.py`, standard library only. Copy it; do not add an SDK. |

`mcp_client.call_tool(token, name, arguments)` returns the tool's data and raises `AuthError`
(401/403), `ToolError` (Sage or SQL said no, message included) or `Unavailable` (server down or a
non-tool reply). Handle all three on every page: `AuthError` signs the user out, `ToolError` is
shown verbatim with who to ask, `Unavailable` is a 503 page, never a crash.

### 2.2 The tools

Always prefer a named tool over `query`. `explain: true` on any tool returns the SQL it would run
and the permission checks it applies, without running it; use it when a result looks wrong.

| Tool | Arguments | Returns |
| --- | --- | --- |
| `whoami` | none | token id and label, SQL login and its grants, Sage user, and per company: `open`, `groups`, `cost_visible` or the `reason` it cannot be opened |
| `list_companies` | none | companies this principal can open, with the reason when not |
| `list_views` | `company` | the published views: owning Sage program, columns, whether this principal may SELECT, masked columns |
| `query` | `company`, `sql`, `limit`, `explain` | one SELECT against published views only, as this principal; last resort |
| `posting_journals` | `company`, `period`, `date_from`, `date_to`, `doc_type`, `customer`, `order_no`, `limit` | O/E posting journal lines (invoiced sales raw data) |
| `sales_master` | `company`, `order_number`, `customer`, `status`, `quotes`, `entered_by`, `limit` | order and quote lines with booked value and the quote/order cross-link |
| `customer_order_history` | `company`, `customer`, `include_quotes` | per-order summary for a customer: invoiced totals next to Sage's order totals |
| `item_costs` | `company`, `item`, `location`, `limit` | quantity on hand and average, most recent and standard cost per location |
| `users` | `company`, `user_id` | Sage users: id, Windows login, authentication method, account status |

Companies on the estate: `QUIK`, `USBP`, `USBTST` are built; the others answer with a `[sql]` reason.

### 2.3 Privileges: what a token can do

A token resolves to two layers, and the MCP applies both on every call:

1. **SQL login** (layer 1): which databases and objects the gateway may read on the caller's behalf.
2. **Windows login and Sage user** (layer 2): which companies the user may open, which Sage security
   group they hold per program, and therefore which columns are masked (costs, for example).

Consequences for a tool you build:

- Call `whoami` at sign-in and keep the companies that are `open`. Offer only those in the UI, and
  show the others as "no access" with Sage's reason, so the user knows it is Sage, not the app.
- Expect masked columns. A result carries `masked_columns`; announce them on the page ("Columns
  masked by Sage for your role: …"). Do not drop them silently and do not compute around them.
- A disabled, locked or unknown Sage user is refused at sign-in. Show the reason.
- Rights differ per company. The same user can be refused in QUIK and allowed in USBP.
- The MCP answers for the token, so the tool needs no permission logic of its own. Do not add any.

### 2.4 Getting a token

- The requester asks the Sage administrator (section 7) for a personal token. On the mock estate the
  administrator mints it on the server with
  `python3 -m sage_mcp.tokens mint --login <sql_login> --as '<DOMAIN\login>' --label "<who>" --expires-days 30`
  from `/home/ec2-user/mock-sage-300`, hands the value over privately, and the store keeps only its
  hash. `python3 -m sage_mcp.tokens list` and `revoke <token_id>` manage them.
- Demo tokens exist for demos and tests only: `sage-mock-<role>` with roles `controller`,
  `integrator`, `salesmanager`, `shopfloor`, `finance`, `intern`, `stockroom`, `leftco` (disabled),
  `jdoe` (no Sage user), `vpsales`, `powerbi`. They reproduce the privilege cases a tool must handle.
- The tool stores the token only in the user's browser cookie (`HttpOnly`, `Secure`, `SameSite=Lax`,
  path limited to the app, eight hours). Never in a file, a database, a log or the repo.

### 2.5 Claude artifacts: the "SFG Sage 300" connector

A tool can also be a published Claude artifact (an HTML page) instead of a Flask app. Then no token is
pasted into the page: the page declares the `mcp` capability with the connector display name
`SFG Sage 300` and the tools it calls, and claude.ai attaches each viewer's own sign-in. The MCP server
fronts this with OAuth 2.1 + PKCE (`sage_mcp/oauth.py`): discovery at
`https://44.218.227.134/.well-known/oauth-authorization-server`, dynamic client registration, and a
sign-in page at `/mcp-login` where the person proves who they are with their Sage access token (on a
real estate: the company identity provider). The opaque token the connector receives resolves to that
person's Sage rights on every call, so the same two layers apply.

- Server URL to give claude.ai: `https://44.218.227.134/mcp`. Each viewer adds the connector once
  (Settings → Connectors → Add custom connector, name exactly `SFG Sage 300`), or an org admin adds it
  for everyone. Only viewers inside the organisation can use it from a page.
- The page branches on the error code, never on message text: `tool_error` is "Sage said no."; the
  connector states (`needs_reauth`, `server_not_connected`, `approval_required`, …) get their own copy.
- Reference page: https://claude.ai/artifact/9DK4Vk4zdDKDKx6ZjRSJxd (the customer-orders twin).

## 3. Build standards

### 3.1 Project layout

```
projects/<name>/
  app.py              Flask app; Blueprint with url_prefix from APP_PREFIX (default /<name>)
  mcp_client.py       copied unchanged from customer-orders
  requirements.txt    flask>=3.1,<4; gunicorn>=23,<24; pytest>=8,<9 (add only what you use)
  templates/          base.html (copied), signin.html (copied), your pages
  static/style.css    copied unchanged; app-specific rules go below the tokens
  tests/test_app.py   unit tests with a fake call_tool, live tests that skip when MCP is down
  deploy/             sfg-<name>.service, nginx-location.conf, install.sh (from templates/)
  README.md           the handover document (section 4.3)
  .gitignore          .venv/ __pycache__/ *.pyc .pytest_cache/ *.env
```

Routes every tool has: `GET /healthz` (plain `ok`), `POST /signin`, `POST /signout`, `GET /` which
shows `signin.html` without a cookie. Pages read the token from the cookie and pass it to every call.

### 3.2 Naming, ports and URLs

| Thing | Rule | Example |
| --- | --- | --- |
| Project name | lowercase, hyphenated noun phrase, what it shows | `customer-orders` |
| Folder | `projects/<name>/` | `projects/customer-orders/` |
| URL | `https://44.218.227.134/<name>/` | `/customer-orders/` |
| Service | `sfg-<name>.service` | `sfg-customer-orders` |
| Port | next free from 8102 in the root README table; reserved: 8000 knowledge base, 8765 MCP | `8102` |
| App title | `SFG <App name>` in the top bar | `SFG Customer Orders` |

### 3.3 Stack

Python 3.9 (the system interpreter on the box), Flask, gunicorn with one worker and four threads,
one `.venv` per project (`python3 -m venv .venv && nice .venv/bin/pip install -r requirements.txt`),
no database of its own, no secrets in the repo, no JavaScript frameworks, no build step. Keep the
resident size under about 60 MB; the service unit caps it at 192 MB.

### 3.4 The house look

- Top bar: the SFG wordmark as text, `SFG <App name>`, in the display face Fraunces, with a small
  uppercase caption "read-only via Sage MCP". No raster logo exists; do not invent one.
- Tokens from `static/style.css` (accent `#0f4c81`, body face Public Sans, light and dark). Do not
  restyle them; add rules for your own components below them.
- Who is signed in, top right, with a sign-out button.
- Footer on every page: "data read through the Sage 300 MCP with your own token; nothing is written
  to Sage", a link to the handover doc on GitHub, and the signed-in label.
- An access strip near the top: one chip per company, `open · costs visible`, `open · costs masked`
  or `no access`, with Sage's reason as the tooltip.
- Numbers formatted with thousands separators and two decimals; dates as Sage gives them.

### 3.5 When Sage says no

Show the MCP message verbatim in a notice headed "Sage said no." and, under it, who to ask: access
and cost rights go to the Sage administrator, missing data goes to the Sage champion as a view
request with the project owner notified. Never hide a refusal behind a generic error, never retry
with another token, never fill the gap with a guess.

### 3.6 Tests

- `pytest` in the project venv, run with `nice`. Unit tests replace `app.call_tool` with a fake and
  cover: signed-out page, healthz, bad token at sign-in, happy path with the cookie, a verbatim
  refusal with who to ask, masked columns announced, an expired token signing out, MCP down giving a
  503.
- Live tests run against `MCP_URL` and skip when the port does not answer. They use at least one
  token with rights and one without (`sage-mock-controller`, `sage-mock-stockroom` or
  `sage-mock-intern`) and assert real numbers from the mock estate.
- The suite passes before the first commit and before every deploy.

### 3.7 The artifact track (no server of its own)

A tool that only reads and shows can be one HTML page published as a Claude artifact instead of a
Flask app. Choose it when the box has no room for another service, when the audience lives in
claude.ai anyway, or when the ask is "a page" rather than "an app". Sections 3.1 to 3.3 and 3.6 do not
apply; 3.4 and 3.5 do. The three live examples: `projects/customer-orders/artifact-page.html`,
`projects/stock-costs/page.html`, `projects/revenue-by-customer/page.html`.

- **Layout:** `projects/<name>/page.html` (the whole tool: title, style with the house tokens, one
  script) and `README.md` (section 4.3). No port, no unit, no nginx, no venv.
- **Access:** `const mcp = await claude.use("mcp")`; `null` means this view cannot reach connectors,
  so render that state and offer the demo snapshot. Every read is `mcp.callTool("SFG Sage 300", tool,
  input)` with the viewer's own sign-in; the page never sees a token. Call `whoami` first and draw
  the access strip from it. Publish with the smallest manifest that names the tools the page calls:
  `{"mcp": {"servers": [{"server": "SFG Sage 300", "tools": ["whoami", "<tool>"]}]}}`.
- **Before publishing,** observe one real call per tool on the mock MCP (`python3 -I mcpcall.py
  <demo token> <tool> '<json>'` or the equivalent) so the page reads the real `columns`, `rows`,
  `masked_columns`, `summary` and `trace` shapes. Never guess a payload.
- **States, branched on the error code and never on message text:** `tool_error` is "Sage said no."
  with the message verbatim (3.5); `needs_reauth` and `server_not_connected` tell the viewer to
  reconnect or add the connector in Settings → Connectors; `approval_required` offers one button
  that repeats the call once; `not_in_manifest` and `blocked_by_policy` say the page may not use
  the connector for this viewer; `server_unavailable` and a retryable `upstream_error` retry once
  after a short random delay, then show "did not answer". Masked columns are marked in place and a
  **Why?** button repeats the call with `explain: true` and lists the `MASK` rows of the trace.
- **Demo snapshot:** the page carries a small snapshot of the mock estate (rows observed from the
  MCP, fictional roles) for views without a connector, marked as such, and `#demo` on the link
  opens straight onto it. Remove the snapshot on a real estate.
- **Change and retire:** edit `page.html`, republish to the same artifact URL from the shared
  session, commit. Unpublish and remove the index row to retire. Sharing is set from the page's
  Share menu; until shared, only the publisher can open it.
- **Register it:** a row in the root README index with the artifact URL and "none (Claude artifact)"
  for port and service, and the handover README. The knowledge base menu lists only the apps on
  the box.

## 4. GitHub structure and handover

### 4.1 The repository

```
BestPracticeAI/SFG_vibe_coding  (private, branch main)
  README.md                                  the company project index: one row per tool, ports
  .gitignore                                 venvs, caches, .env and *.env
  .claude/skills/sfg-vibe-coding/SKILL.md    this file; templates/ beside it
  projects/<name>/                           one folder per tool, self-contained
```

The checkout on the server is `/opt/sfg-vibe-coding`; services run from there. The mock Sage estate
and the MCP server live outside the repo in `/home/ec2-user/mock-sage-300`.

### 4.2 Commits

- Work on `main`. One commit per change, message in the imperative, first line says what and the
  body says why. Finish with the attribution lines the session is given.
- Never commit a token, an `.env`, a venv, a cache or data exported from Sage.
- Push with HTTPS; the server's credential helper supplies the deploy token. Confirm the push
  landed (`git status -sb` shows `main...origin/main` with nothing ahead).
- Every row in the project index links to the project's handover README.

### 4.3 The handover document, `projects/<name>/README.md`

Executive summary first, five lines a manager can read in a minute:

1. What it does and for whom.
2. Where it runs (URL) and who owns it.
3. Which Sage data it reads (tools and views) and that it writes nothing.
4. Status: built and tested, deployed, open requests to people.
5. How to sign in.

Then the full description for the next developer: how it works (sign-in, the pages, what each call
does), a small ASCII diagram browser → nginx → gunicorn → sage_mcp → views, the privilege table
(what each demo role sees), how to run, test and deploy, resource use, open requests and next steps,
contacts (section 7), and a dated changelog.

## 5. Deploy beside the other apps

Everything a deploy needs is in `projects/<name>/deploy/`, generated from `templates/` in this skill
folder with `<name>`, `<App name>` and `<port>` filled in. A person runs the install script with
sudo; it must be idempotent, so running it twice changes nothing. A tool on the artifact track (3.7)
skips this section except 5.3: its deploy is the publish, and its index row names the artifact URL.

### 5.1 The service unit, `deploy/sfg-<name>.service`

From `templates/sfg-app.service`: runs as `ec2-user` from `/opt/sfg-vibe-coding/projects/<name>`,
`After=` and `Wants=sage-mcp.service`, environment `MCP_URL` and `APP_PREFIX`, gunicorn bound to
`127.0.0.1:<port>`, `Restart=always`, `MemoryMax=192M`, `Nice=5`, `ProtectSystem=strict`,
`ReadOnlyPaths=/opt/sfg-vibe-coding`, `PrivateTmp`, `NoNewPrivileges`. The MCP unit itself is
platform-level and already installed (`sage-mcp.service`, `MemoryMax=256M`); do not ship another.

### 5.2 nginx, `deploy/nginx-location.conf`

One `location /<name>` block proxying to `127.0.0.1:<port>` with `Host`, `X-Forwarded-For` and
`X-Forwarded-Proto` set. The install script inserts it into `/etc/nginx/conf.d/hello.conf` before
the **last** `location / {` (the HTTPS server's catch-all; the first one is the port-80 redirect),
copies the file to `/opt/sfg-kb/nginx-kb.conf` to keep it in sync, runs `nginx -t` and reloads.

### 5.3 The index entries

- Knowledge base navigation: the install script adds `('/<name>/','<App name>')` to the tuple list
  in `/opt/sfg-kb/templates/base.html`, right before `('/sources','Sources')`, and restarts
  `sfg-kb.service`. That is what makes the tool appear in the SFG menu.
- Project index: the row in the root `README.md` (section 3.2), committed with the project.

### 5.4 `deploy/install.sh`

From `templates/install.sh`: refuses to run without sudo, prints `free -m`, stops a development
copy on the port by PID, installs the unit, `daemon-reload`, `enable --now`, restart, the nginx
insert from 5.2, the nav entry from 5.3, then curls `http://127.0.0.1:<port>/<name>/healthz` and
the HTTPS URL, and prints `free -m` again. Keep `set -euo pipefail`.

### 5.5 Verify, then report

- `https://44.218.227.134/<name>/healthz` answers `ok`.
- One signed-in page with a token that has rights shows real numbers.
- One with a token that lacks rights shows the refusal verbatim with who to ask.
- A disabled or unknown token is refused at sign-in.
- `systemctl is-active sfg-<name>` says `active`, `free -m` still shows headroom.

Report the URL, the commit, the five checks and any open requests. A tool is not done while a
check is missing.

### 5.6 Change, roll back, retire

- Change: edit, test, commit, push, `sudo systemctl restart sfg-<name>`. The unit reads the checkout.
- Roll back: `git revert` the commit, push, restart. Never edit files on the server outside git.
- Retire: `sudo systemctl disable --now sfg-<name>`, remove the nginx location and the nav entry,
  mark the index row "retired" with the date; keep the folder and the handover doc.

## 6. Two requests that always go through a person

### Write to Sage

- **Goes to:** the Sage administrator (section 7), copy to the requester.
- **They receive:** company and screen, record key (order number, customer number, item), the field
  with its current and new value, business reason, requester and tool name, link to the evidence
  query (`explain: true` output or the page).
- **They enter:** the change by hand in the normal Sage screen under their own login, then reply
  with the audit or posting reference.
- **Notified:** requester and project owner get the reply; the tool records it in its changelog.
- **Subject line:** `Sage change request · <tool> · <company> · <record>`.

### New view

- **Goes to:** the Sage champion (section 7). The project owner is notified on every request and
  again on completion, without exception.
- **They receive:** proposed view name (`vSfg<Subject>`), columns and source tables, grain (one row
  per what) and filters, a sample row, which Sage groups may see cost columns, business reason,
  requesting tool.
- **They create:** the view in the read-only schema, document it in the views list, grant it to the
  SQL login, and confirm it is live.
- **Then:** the session rebuilds the page on the new view (`list_views` shows it) and updates the
  handover doc and changelog.
- **Subject line:** `View request · <tool> · <proposed view name>`.

Until the person replies, the tool ships without that feature and the handover doc lists the request
under "open requests". Do not block the rest of the tool on it.

## 7. People

Fill in the names before the demo. Until then the roles are stand-ins; do not invent names.

| Role | Name | Contact | Ask them for |
| --- | --- | --- | --- |
| Sage administrator | [name] | [email] | writes to Sage, access and cost rights, personal tokens |
| Sage champion | [name] | [email] | new views and view changes |
| Project owner | [name] | [email] | priorities; notified of every view request |
| Platform champion | [name] | [email] | the shared session, the server, deployment, this skill file |

How to contact them: one request per email, the subject line from section 6, the template filled in
full, and the MCP output attached as evidence. Reference docs on the box:
`/home/ec2-user/mock-sage-300/README.md` (the estate, the two permission layers, the demo roles)
and its `sql/` notes (what each view holds).

## 8. Definition of done

The session says a tool is done only when every line is true:

- [ ] Built on `whoami`/`list_views` output for the requester's token; no raw tables; no writes.
- [ ] Refusals and masked columns are shown verbatim with who to ask.
- [ ] Tests pass (unit and live), run with `nice`, and are in the repo.
- [ ] House look, footer, access strip, `healthz`, sign-in and sign-out present.
- [ ] `deploy/` from the templates, install script run, service active with `MemoryMax`.
- [ ] nginx location in the HTTPS block, knowledge base nav entry, project index row with port.
- [ ] Handover README with the executive summary first; changelog dated.
- [ ] Committed and pushed to `main`; push confirmed.
- [ ] Verified over HTTPS with a token that has rights and one that does not.
- [ ] Open requests to people listed, with the project owner notified of any view request.

On the artifact track (3.7) the test, deploy, nginx and HTTPS lines become: one real call per tool
observed before publishing; the smallest manifest; every connector state and the demo snapshot
exercised in a browser; the artifact published and its URL in the index row; `page.html` and the
handover README committed and pushed.
