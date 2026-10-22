# SFG vibe-coding platform

Apps that anyone on the team builds, with the shared Claude Code session, on top of the Sage 300 data
they already have access to. Every app reads Sage through the MCP server with the user's own token,
writes nothing to Sage, and is published beside the others under `https://44.218.227.134/<name>/`.

**How to build one:** open the shared session in this repository, load the skill
`.claude/skills/sfg-vibe-coding/SKILL.md` (it loads itself when the session starts here), and describe
what you need. The skill file holds the rules: read-only, the token decides, views only, named people
for writes and new views, the house look, how to publish and how to hand over.

## Project index

The company index of everything built on the platform. Each row has a handover document with an
executive summary at the top. Ports are assigned here; take the next free one.

| Project | What it does | URL | Port | Service | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| [customer-orders](projects/customer-orders/README.md) | Look up a customer's orders and quotes, invoiced totals and what is still to invoice, in any company the user may open | https://44.218.227.134/customer-orders/ | 8102 | `sfg-customer-orders` | [project owner] | built and tested; deployed by `deploy/install.sh` |

Reserved: 8765 is the Sage MCP server (`sage-mcp.service`); 8000 is the knowledge base.

## Layout

```
.claude/skills/sfg-vibe-coding/SKILL.md   the contract every session follows
projects/<name>/                           one folder per app: code, tests, deploy/, README.md (handover)
```

The Sage 300 estate behind the MCP server is a SQLite replica of the real estate with fictional users
(`/home/ec2-user/mock-sage-300` on the box, with its own README); the MCP server is `sage_mcp/` there.
