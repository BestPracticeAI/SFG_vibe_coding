# Customer Orders

## Executive summary

- **What:** a one-page lookup of a customer's orders (and optionally quotes) with invoiced totals and
  what Sage still has to invoice, built from the `customer_order_history` recipe of the Sage 300 MCP.
- **For whom:** anyone with a Sage access token; sales first. Each person sees exactly what their own
  Sage rights allow, nothing more.
- **Where:** https://44.218.227.134/customer-orders/ (service `sfg-customer-orders`, port 8102),
  listed in the knowledge base navigation as "Customer orders".
- **Data:** read-only, through the MCP server at `127.0.0.1:8765` with the signed-in user's token. The
  app has no database and no credentials of its own.
- **Status:** built and tested (unit + live integration); deployed by `deploy/install.sh`. No open
  requests to Sage. Owner: [project owner, see the skill file].

## How it works

1. **Sign in** with a Sage access token. The app calls the MCP `whoami` tool with it; if the MCP
   server rejects the token (unknown, revoked, expired) or Sage rejects the user (account disabled,
   no Sage user) the message is shown and nothing is stored. An accepted token is kept in an
   `HttpOnly`, `Secure`, `SameSite=Lax` cookie for 8 hours, scoped to `/customer-orders`.
2. **The access strip** shows every company from `whoami`: open or refused (with Sage's reason on
   hover) and whether cost columns are visible for that role.
3. **Look up** a customer number in a company you may open. The app calls
   `customer_order_history(company, customer, include_quotes)` and renders the summary (orders,
   complete orders, invoiced before and with tax, first and last order) and every column the recipe
   returns.
4. **When Sage says no** (for example a company the user has no authorizations in), the MCP message
   is shown verbatim under "Sage said no", together with who to ask, as the skill file requires. The
   app never retries with another token.

```
browser ──HTTPS──▶ nginx /customer-orders ──▶ gunicorn app.py (Flask)
                                                   │  JSON-RPC tools/call, Authorization: Bearer <user token>
                                                   ▼
                                       sage_mcp.server (127.0.0.1:8765)
                                                   │  SQL grants + Sage 300 security per token
                                                   ▼
                                       Sage 300 views (mock estate, SQLite)
```

Files: `app.py` (routes and rendering), `mcp_client.py` (40 lines of JSON-RPC over HTTP, no SDK),
`templates/`, `static/style.css` (the house tokens), `tests/test_app.py`, `deploy/`.

## Privilege behaviour, as tested on the mock estate

| Token (demo) | What the dashboard shows |
| --- | --- |
| `sage-mock-controller` | USBP · open · costs visible; CUT001 in USBP: 6 orders, 100,516.36 before tax, 101,572.88 with tax |
| `sage-mock-intern` | QUIK · open · costs masked (OE group IEINTERN lacks Item Cost Inquiry); lookups work, cost columns would be null |
| `sage-mock-stockroom` | QUIK · no access; a QUIK lookup shows "Sage said no: [sage] Sage user INVOFF1 has no authorizations in company QUIK …"; USBP works |
| `sage-mock-leftco` | sign-in refused: "[sage] Sage user LEFTCO: 'Account is disabled' is ticked" |
| unknown token | sign-in refused by the MCP server (HTTP 401) |

The recipe behind the lookup has no cost columns, so masking shows up in the access strip rather than
in the table; any tool that returns masked columns is announced above the table.

## Run, test, deploy

```
cd projects/customer-orders
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
MCP_URL=http://127.0.0.1:8765/mcp APP_PREFIX=/customer-orders .venv/bin/python app.py     # dev server on 8102
.venv/bin/python -m pytest -q tests                                                      # live tests skip when MCP is down
sudo bash deploy/install.sh                                                              # services, nginx location, index entry
```

`deploy/install.sh` is idempotent: it installs and starts `sage-mcp.service` and
`sfg-customer-orders.service` (both with `MemoryMax`), inserts the nginx location before the catch-all,
adds "Customer orders" to the knowledge base navigation, and checks the health URL. Environment:
`MCP_URL` (default `http://127.0.0.1:8765/mcp`), `APP_PREFIX` (default `/customer-orders`), `PORT`
(dev server only).

Resource note: the box has 913 MB and no swap. The dashboard runs one gunicorn worker (about 45 MB) and
the MCP server about 70 MB; both units carry `MemoryMax` so a leak cannot take the machine down.

## Open requests and next steps

- None open. The lookup needed no new view and no write to Sage.
- Possible next step: order lines for one order from `sales_master` (cost columns masked per role).
  That tool exists; it is a UI change only.
- Before the demo: fill in the names in the skill file, section 7, and the owner above.

## Contacts

The roles in `.claude/skills/sfg-vibe-coding/SKILL.md`, section 7: Sage administrator (access, cost
rights, writes), Sage champion (views), project owner (notified of every view request), platform
champion (tokens, deployment).

## Changelog

- 2026-10-22: first version. Built, tested and published by the shared session following the skill file.

## Artifact twin (added 22 October 2026)

The same lookup also exists as a Claude artifact, `artifact-page.html` in this folder, published at
https://claude.ai/artifact/9DK4Vk4zdDKDKx6ZjRSJxd. It has no server of its own: the page declares the
`mcp` capability for the connector named `SFG Sage 300` (tools `whoami` and `customer_order_history`),
so claude.ai attaches each viewer's own sign-in and the MCP answers with that person's rights. There is no
token to paste. Without a reachable connector the page offers a demo snapshot of the mock estate with the
five demo roles; `#demo` on the link opens straight onto it. Skill file section 2.5 describes the pattern.
