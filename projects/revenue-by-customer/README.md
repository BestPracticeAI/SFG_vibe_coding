# Revenue by Customer

## Executive summary

- **What:** invoiced revenue per customer for a company and date range, ranked, with invoice count,
  cost, margin and margin % where the viewer's Sage rights allow, from the `posting_journals` tool
  of the Sage 300 MCP (view `vOEPostingJournals`, the rows behind the invoiced-sales report).
- **For whom:** anyone with the `SFG Sage 300` connector in claude.ai; sales and finance first. Cost
  and margin appear only for Sage Order Entry groups that tick Item Cost Inquiry; everyone else gets
  complete revenue and a "masked by Sage" marker with Sage's reason. This is the alternative the
  workshop deck's refusal case describes: the intern's margin dashboard, minus the margin.
- **Where:** https://claude.ai/artifact/VPqqedbThTcummZw874rzZ, a Claude artifact. No server, port or
  service of its own; `#demo` on the link opens the mock-estate snapshot without a connector.
- **Data:** read-only, through the MCP server with each viewer's own connector sign-in. The page holds
  no credentials, no database and no copy of Sage data beyond the demo snapshot.
- **Status:** built; demo mode exercised; the live connector path uses payload shapes observed from one
  real call per tool on the mock MCP, but no call has yet gone through a claude.ai connector. No open
  requests to Sage. Owner: [project owner, see the skill file].

## How it works

1. **Sign-in is the connector.** On load the page asks `claude.use("mcp")`; `null` gives the "no
   connector" state with the demo snapshot. Otherwise it calls `whoami` through the connector named
   `SFG Sage 300` and draws the access strip: every company open or refused, and whether O/E costs
   (hence margin) are visible for the viewer's role.
2. **Look up** a company and an optional document-date range. The page calls
   `posting_journals(company, date_from?, date_to?, limit 2000)`, which already excludes shipments,
   and sums the lines per customer: invoices and debit notes positive, credit notes negative.
   Four tiles (revenue, invoices and notes, customers, margin), a ranked bar chart of the top ten
   drawn on a canvas from the theme tokens, and the full table follow. If the tool reports
   `truncated`, the note under the table says the totals are incomplete and to narrow the dates.
3. **Masking is shown in place.** When `masked_columns` contains `CostFC`, the margin tile reads
   "masked by Sage" and the cost, margin and margin % columns are marked; revenue stays complete.
   The **Why?** button repeats the call with `explain: true` and lists the `MASK` rows of Sage's
   trace, for example `OEAUDD.EXTCOSTS — Sage: OE group IEINTERN lacks "Item Cost Inquiry"`.
4. **When Sage says no** the tool error is shown verbatim under "Sage said no", with who to ask.
   Two refusals exist on the mock estate: no authorizations in the company at all, and a company
   that opens but has no Order Entry security group, so the journals view is not readable.
   Connector failures are branched on their error code, never on message text.

```
viewer's browser ──▶ claude.ai artifact (page.html)
                         │  claude.use("mcp").callTool("SFG Sage 300", tool, input)
                         ▼
                 claude.ai attaches the viewer's connector sign-in (OAuth; the page never sees it)
                         │  Bearer <opaque token> ──▶ https://44.218.227.134/mcp
                         ▼
                 sage_mcp.server: token → SQL login + Sage user → Sage 300 views (mock estate)
```

Files: `page.html` is the whole tool. It is published with the capability manifest
`{"mcp": {"servers": [{"server": "SFG Sage 300", "tools": ["whoami", "posting_journals"]}]}}`.

## Privilege behaviour, as exercised on the mock estate

| Role (demo token) | What the page shows |
| --- | --- |
| `sage-mock-salesmanager` | QUIK: 48,752.00 revenue over 36 lines, 10 customers, margin 61.4%; USBTST open; USBP "no access" and refused on lookup |
| `sage-mock-controller` | every built company open with margin; USBP: CUT001 100,516.36 over 6 invoices |
| `sage-mock-intern` | QUIK open; revenue complete; cost, margin and margin % masked; Why? prints `MASK OEAUDD.EXTCOSTS` |
| `sage-mock-stockroom` | QUIK refused (no authorizations); USBP opens but "[sage] Sage user INVOFF1 has no OE security group in company USBP …", so the journals are refused |
| `sage-mock-leftco` | refused at sign-in: "[sage] Sage user LEFTCO: 'Account is disabled' is ticked" |

## Run, test, change

- **Run:** open the link signed in to claude.ai with the connector added (Settings → Connectors → Add
  custom connector, name `SFG Sage 300`, URL `https://44.218.227.134/mcp`, then sign in on the
  server's page). Without it, `#demo` opens the snapshot.
- **Test:** the five roles above in demo mode, then the same five through the connector once it is
  on the viewer's account. There is no automated test; the box has no browser or Node runtime.
- **Change:** edit `page.html`, republish to the same artifact URL from the shared session, commit.
  Keep the manifest minimal; a new tool means a new manifest entry and a new viewer consent.
- **Retire:** unpublish the artifact and remove the row from the project index.

## Open requests

None. A margin version for roles without Item Cost Inquiry is not a page change: it is an access
request to the Sage administrator named in the skill file.
