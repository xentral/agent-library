# Xentral Agent OS for Claude Code

Connect your Xentral ERP to **Claude Code** and let it do the work for you —
create document templates, build automations, set up dashboards and KPIs, and
get guided through your initial setup. Installing takes two commands.

---

## 1. Prerequisite

Install **Claude Code** if you haven't already:
<https://docs.claude.com/en/docs/claude-code/overview>

## 2. Install (two commands)

In Claude Code, run:

```
/plugin marketplace add xentral/agent-library
/plugin install xentral-connector@xentral
```

That's it. You now have the Xentral connector and all skills.

## 3. Sign in (once)

The first time you ask Claude to do something in Xentral, a browser window opens
to sign in to your Xentral account. Approve it once — the login is remembered and
refreshed automatically. You won't be asked again.

## 4. What you can do

Just ask in plain language (your own language works). Examples:

- *"Create an invoice PDF template in our corporate design."*
- *"Build a workflow that sends a dunning reminder for invoices overdue by 14 days."*
- *"Set up a CEO cockpit dashboard with revenue, open receivables and overdue orders."*
- *"Track a new KPI: open returns awaiting refund."*
- *"Help me set up my new Xentral tenant from scratch."*

Claude already knows how to use the Xentral tools — you don't need to learn any
commands or syntax. Describe the outcome you want.

## 5. Keeping it up to date

Updates are **automatic** — Claude Code checks for new versions on start.

To update manually at any time:

```
/plugin marketplace update xentral
/plugin update xentral-connector@xentral
```

You can turn auto-update on/off under `/plugin` → **Marketplaces**.

## 6. Troubleshooting

- **The Xentral tools don't show up** — run `/plugin` and confirm
  `xentral-connector` is installed and enabled, then restart Claude Code.
- **Sign-in didn't open / failed** — run `/mcp`, pick the `xentral` server and
  start authentication again.
- **Wrong company / instance** — you can re-authenticate via `/mcp`; pick the
  correct Xentral instance when prompted.
- **An update didn't arrive** — run the two manual update commands above.
- **Still stuck?** Contact Xentral support.

---

<sub>Maintainers: this repo is also the source for the in-product library and the
plugin. See [CONTRIBUTING.md](CONTRIBUTING.md).</sub>
