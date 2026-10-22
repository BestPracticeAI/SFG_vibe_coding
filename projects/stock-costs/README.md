# Stock and Cost Check

## Executive summary

- **What:** a one-page stock and cost check per item and location: quantity on hand, on sales and
  purchase orders, committed and available, with average, most recent, standard and total cost, from
  the `item_costs` tool of the Sage 300 MCP (view `IcCostsList`).
- **For whom:** anyone with the `SFG Sage 300` connector in claude.ai; inventory, purchasing and sales
  first. Cost columns appear only for Sage Inventory Control groups that tick Cost Inquiry; everyone
  else sees the quantities and a "masked by Sage" marker with Sage's reason.
- **Where:** https://claude.ai/artifact/5AzX3Z5KENp26qec9Ma8Ks, a Claude artifact. No server, port or
  service of its own; `#demo` on the link opens the mock-estate snapshot without a connector.
- **Data:** read-only, through the MCP server with each viewer's own connector sign-in. The page holds
  no credentials, no database and no copy of Sage data beyond the demo snapshot.
- **Status:** built; demo mode exercised; the live connector path uses payload shapes observed from one
  real call per tool on the mock MCP, but no call has yet gone through a claude.ai connector. No open
  requests to Sage. Owner: [project owner, see the skill file].

## How it works

1. **Sign-in is the connector.** On load the page asks `claude.use("mcp")`. When that is `null`
   (outside the organisation, or a view without connectors) it shows the "no connector" state and
   offers the demo snapshot. Otherwise it calls `whoami` through the connector named `SFG Sage 300`
   and draws the access strip: every company open or refused (Sage's reason on hover) and whether
   I/C costs are visible for the viewer's role.
2. **Look up** a company, an item number prefix (blank for all) and a location (blank for all). The
   page calls `item_costs(company, item?, location?, limit 500)` and renders four tiles (items,
   quantity on hand, on sales orders, stock value) and every column the tool returns. Results are
   cached for one minute per viewer; the note under the table says when they were fetched.
3. **Masking is shown in place.** `masked_columns` from the tool mark the cost headers and cells;
   the stock value tile reads "masked by Sage"; nothing is computed around the gap. The **Why?**
   button repeats the call with `explain: true` and lists the `MASK` rows of Sage's trace, for
   example `ICILOC.TOTALCOST — Sage: IC group IEINTERN lacks "Cost Inquiry"`.
4. **When Sage says no** (a company the viewer has no authorizations in) the tool error is shown
   verbatim under "Sage said no", with who to ask, as the skill file requires. Connector failures
   are branched on their error code: reconnect, add the connector, needs approval, blocked by
   policy, unreachable (one retry), never on message text.

```
viewer's browser ──▶ claude.ai artifact (page.html)
                         │  claude.use("mcp").callTool("SFG Sage 300", tool, input)
                         ▼
                 claude.ai attaches the viewer's connector sign-in (OAuth; the page never sees it)
                         │  Bearer <opaque token> ──▶ https://44.218.227.134/mcp
                         ▼
                 sage_mcp.server: token → SQL login + Sage user → Sage 300 views (mock estate)
```

Files: `page.html` is the whole tool (HTML, CSS tokens of the house look, one script). It is
published with the capability manifest
`{"mcp": {"servers": [{"server": "SFG Sage 300", "tools": ["whoami", "item_costs"]}]}}`.

## Privilege behaviour, as exercised on the mock estate

| Role (demo token) | What the page shows |
| --- | --- |
| `sage-mock-salesmanager` | QUIK and USBTST open, costs visible; USBP "no access"; a USBP lookup shows "Sage said no: [sage] Sage user INSALES1 has no authorizations in company USBP …" |
| `sage-mock-controller` | every built company open, costs visible |
| `sage-mock-intern` | QUIK open; AvgCost, RecentCost, StdCost and TotalCost masked; stock value "masked by Sage"; Why? prints the three `MASK` rows for ICILOC |
| `sage-mock-stockroom` | USBP open with costs (I/C group has Cost Inquiry); QUIK and USBTST refused |
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

None. The lot-trace half of use case 2 waits for a new view (see the workshop deck); this page does
not attempt it.
