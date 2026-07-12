---
name: xentral-dashboards
description: >
  Build and edit per-instance dashboards — pages of widgets visualizing live
  business and operations data — with the xentral_dashboards tool. Covers built-in vs
  custom dashboards, starting from the dashboard library instead of a blank
  page, the widget catalog, wiring widgets to KPIs, chart vs value widgets, and
  layout. Use when the user wants an overview page ("how is the business doing
  right now?"), a CEO/operations cockpit, or to add/arrange widgets — not for
  analysing a single record or defining new metrics (use xentral-kpi for that).
examples:
  - "Set up a CEO cockpit with revenue, open receivables and overdue orders."
  - "Build a logistics dashboard for shipping and open parcels."
---

# Dashboards

## Purpose

Dashboards are **per-instance pages of widgets that visualize the
operator's live ERP and operations data**. They are the answer
to "how is the business doing right now?" — not the place to
analyse a single record, not the place to run ad-hoc SQL, not the
place to define new metrics from scratch.

Two kinds coexist:

* **Built-in dashboards** — curated, shipped with the platform.
  Each instance gets them automatically. Useful as starting points
  and reference layouts.
* **Custom dashboards** — created by the operator (often with
  agent help). Lives only inside the instance. Composed from the
  same widget catalog as the built-ins.

## When to invoke

* The operator asks "how do I see X?" — first check if X is in
  a built-in dashboard; only build custom if no built-in covers it.
* The operator wants a board for a team / role / context ("a
  dunning dashboard for the finance team", "a daily-stand-up
  board with last 24 h activity").
* The operator wants to enable a built-in that's currently hidden
  for their instance.
* A built-in needs reordering / hiding for this instance.

Do **not** invoke when:

* The user wants to *act* on a record (refund this order, send
  this invoice). Dashboards are read-only.
* The user wants a one-off report — render and download instead;
  don't permanentize ad-hoc questions.
* The user wants a financial closing / P&L — Dashboards aggregate
  operational data; accounting close lives elsewhere.

## Concepts & terminology

| Term | Meaning |
|---|---|
| Dashboard | A page composed of one or more widgets. Has a slug, title, visibility flag, layout. |
| Slug | Stable identifier inside the instance. Used in URLs and as a config key. |
| Widget | A single visualization — KPI tile, table, chart, list. Drawn from the platform's widget catalog. |
| Catalog | The set of available widget types. Shared platform-wide. |
| Built-in | Catalog-shipped dashboard, exists for every instance. Instance can hide it but not delete. |
| Custom | Operator-created dashboard. Instance owns it fully. |
| `enabled` | Whether a built-in dashboard is visible for this instance. Defaults to true at platform level; operator can flip per dashboard. |
| `dataSource` (chart widget) | Where the widget gets its data: `preset` (built-in dummy dataset for layout tests), `report` (existing Xentral analytics report), `prompt` (Co-Pilot generates SQL from a free-text description). |
| `cacheMode` (chart widget) | How the widget refreshes: `live` (every render hits Xentral) or `cached` (TTL via `cacheTtlSeconds`). Only meaningful for `dataSource != preset`. |
| Hub collection | The "Agent Hub — generated" collection in Xentral analytics. Auto-created on the first prompt widget per instance. All Co-Pilot-generated reports land there. |
| `reportId` | Xentral report id stored per widget. Cleaned up automatically when the widget is removed (lifecycle hook). |

## Pre-flight checks

Before creating or modifying a dashboard:

1. **Read `business_model.profile`** — `business_model` and
   `automation` tell you which widgets make sense. A B2B
   distributor with low automation cares about open orders and
   overdue invoices; a B2C webshop cares about today's
   conversion and stock-outs.
2. **Check built-ins first** — does the request already exist?
3. **Check enabled state for built-ins** — if it exists but is
   hidden, just re-enable.
4. **Verify the integrations** the requested widgets need are
   live (e.g. a "Shopify orders today" widget needs Shopify
   wired). Skip widgets whose sources aren't configured rather
   than render an empty box.

## Naming a dashboard

The title is a short **noun phrase, 1–3 words**, in the instance locale —
the same house style as the built-in dashboards (`Tagesgeschäft`, `Einkauf`,
`Lager & Versand`, `Finanzen`, `CEO-Cockpit`). Keep it **≤ 20 characters** —
it must fit on one line in the sidebar; anything longer is truncated with an
ellipsis and stops being scannable.

- **Do not** append the company/customer name, and do not add an em-dash
  prefix or suffix. Good: `Lager & Dispo`. Bad: `Lager & Dispo — {company}`,
  `CEO-Cockpit — {company}`, `Einkauf & Frühwarnung — Was geht mir aus?`.
- When you create from a built-in template, pass its **canonical title
  verbatim** — don't decorate it. "Speaking name" means a clear role word,
  not a personalized sentence.
- The dashboard already lives inside one instance; the company name is
  implied and only adds noise to every tile in the sidebar.

## Common pitfalls

| Pitfall | Why it breaks |
|---|---|
| Recreating a built-in as a custom | Maintenance burden doubles; updates to the built-in don't carry over. Re-enable instead. |
| Decorating the title with the company name or an em-dash prefix/suffix | `CEO-Cockpit — {company}` is noise — the instance already implies the company. Use the bare canonical title (see Naming a dashboard). |
| Cramming 15 widgets on one page | Auto-refresh becomes a load problem; the user loses focus. 5–8 widgets per dashboard. |
| Naming dashboards generically ("Dashboard 1") | Six months later nobody knows what it is. Each dashboard answers one named question. |
| Putting heavy chart widgets in the first row | They render last; the user sees the page jump. Lead with KPI tiles, charts below. |
| Different time periods on widgets that compare to each other | "Revenue today" next to "AOV last 30 days" doesn't compute. Synchronize period across a board. |
| Inventing currencies | Stick to the instance's ERP currency; don't auto-convert. |
| Treating dashboard as the source of truth | It's a view. If a number looks wrong, the data source is wrong, not the dashboard. |

## Out of scope

* Inventing new widget *types* at runtime. New types are code
  changes in the catalog.
* SQL or query editing inside a dashboard outside the Co-Pilot flow
  (`dataSource=prompt`). The Co-Pilot is the only sanctioned
  ad-hoc SQL surface.
* Direct editing of reports inside the "Agent Hub — generated"
  collection. The widget config is the source of truth, not the
  Xentral report.
* Cross-instance rollups. Each instance is its own world.
* Acting on the data (issuing refunds from a table widget,
  paying from a KPI tile). Dashboards link to the action pages;
  they don't perform actions.

## Detailed references — read on demand

Load only the file you need:

- **Widget structure, the full widget catalogue, chart data sources**:
  [reference/widgets.md](reference/widgets.md)
- **Public share links + constraints & invariants**:
  [reference/sharing-and-constraints.md](reference/sharing-and-constraints.md)
- **Recipes (common end-to-end flows)**:
  [reference/recipes.md](reference/recipes.md)
