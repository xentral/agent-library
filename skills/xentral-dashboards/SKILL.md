---
name: xentral-dashboards
description: >
  Build and edit per-tenant dashboards — pages of widgets visualizing live ERP
  and operations data — with the xentral_dashboards tool. Covers built-in vs
  custom dashboards, starting from the dashboard library instead of a blank
  page, the widget catalog, wiring widgets to KPIs, chart vs value widgets, and
  layout. Use when the user wants an overview page ("how is the business doing
  right now?"), a CEO/operations cockpit, or to add/arrange widgets — not for
  analysing a single record or defining new metrics (use xentral-kpi for that).
---

<!-- Sourced from backend/dashboards/agent_guide/en.md — keep in sync. -->

# Dashboards

## Purpose

Dashboards are **per-tenant pages of widgets that visualize the
operator's live ERP and operations data**. They are the answer
to "how is the business doing right now?" — not the place to
analyse a single record, not the place to run ad-hoc SQL, not the
place to define new metrics from scratch.

Two kinds coexist:

* **Built-in dashboards** — curated, shipped with the platform.
  Each tenant gets them automatically. Useful as starting points
  and reference layouts.
* **Custom dashboards** — created by the operator (often with
  agent help). Lives only inside the tenant. Composed from the
  same widget catalog as the built-ins.

## When to invoke

* The operator asks "how do I see X?" — first check if X is in
  a built-in dashboard; only build custom if no built-in covers it.
* The operator wants a board for a team / role / context ("a
  dunning dashboard for the finance team", "a daily-stand-up
  board with last 24 h activity").
* The operator wants to enable a built-in that's currently hidden
  for their tenant.
* A built-in needs reordering / hiding for this tenant.

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
| Slug | Stable identifier inside the tenant. Used in URLs and as a config key. |
| Widget | A single visualization — KPI tile, table, chart, list. Drawn from the platform's widget catalog. |
| Catalog | The set of available widget types. Shared platform-wide. |
| Built-in | Catalog-shipped dashboard, exists for every tenant. Tenant can hide it but not delete. |
| Custom | Operator-created dashboard. Tenant owns it fully. |
| `enabled` | Whether a built-in dashboard is visible for this tenant. Defaults to true at platform level; operator can flip per dashboard. |
| `dataSource` (chart widget) | Where the widget gets its data: `preset` (built-in dummy dataset for layout tests), `report` (existing Xentral analytics report), `prompt` (Co-Pilot generates SQL from a free-text description). |
| `cacheMode` (chart widget) | How the widget refreshes: `live` (every render hits Xentral) or `cached` (TTL via `cacheTtlSeconds`). Only meaningful for `dataSource != preset`. |
| Hub collection | The "Agent Hub — generated" collection in Xentral analytics. Auto-created on the first prompt widget per tenant. All Co-Pilot-generated reports land there. |
| `reportId` | Xentral report id stored per widget. Cleaned up automatically when the widget is removed (lifecycle hook). |

## Widget structure

Each widget declares:
* **`id`** — unique within the dashboard, used in layout references.
* **`type`** — exact class name from the catalogue below.
* **`config`** — type-specific shape (see the catalogue).

The dashboard `layout` references widget ids:

```yaml
layout:
  type: split
  main: [greeting, hero, kpi_grid]
  side: [tabs]
```

## Widget catalogue

The platform exposes a fixed set of widget types — agents do **not**
invent new types. The names below are the values that go into the
widget's `type` field verbatim (case-sensitive).

### Headers & overviews
| `type` | Purpose | Core config keys |
|---|---|---|
| `GreetingCard` | Hello-line + optional subtitle at the top of a page | `subtitle: {de, en}` |
| `HeroStats` | 2–4 prominent KPI tiles (the "today" strip) | `title_key`, `kpis: [kpi_id, …]` |
| `KpiGrid` | Secondary KPI grid (smaller tiles, more of them) | `title_key`, `kpis: [kpi_id, …]` |
| `AttentionBlock` | Curated alert / call-out (e.g. "23 inquiries waiting") | `kind` (e.g. `customer_service`) |

### Tables — the workhorse for embedding ERP data
| `type` | Purpose | Core config keys |
|---|---|---|
| `TableTabs` | Tabbed table area; each tab embeds a workspace list view | `tabs: [{id, label_key, view, …}]` |

`TableTabs` is the only way to put an ERP record list on a dashboard.
Each tab's `view` is a built-in renderer; the available values are:

- `inbox` (with optional `scope`: `customer_service` / `finance` / `procurement`)
- `sales_orders`, `return_orders`, `purchase_orders`
- `customers`, `products`, `suppliers`
- `sales_invoices`, `supplier_invoices`, `sales_credit_notes`
- `payments`, `goods_receipt`
- `entity` — generic renderer driven by `entity_key` (see next paragraph)
- `analytics_report` — embed a Xentral analytics report by `report_id`

**Embedding an arbitrary BusinessEntity (e.g. Kostenstellen) — the
one explicit consumption path from the foundation layer:** use
`view: 'entity', entity_key: '<key>'`. The valid `entity_key` values
come live from Xentral's metadata — call `xentral_entities` with
`action='list'` to enumerate them per tenant. This is the only
place across all dashboard widgets where a raw `entity_key` is
accepted; everywhere else use the named views above. The entity
catalogue is the lowest ERP layer (raw data model), distinct from
the workflow-recipe layer (`xentral_business_blocks list_library`)
— drop down to entities only when the customer's process needs
customising beyond the standard.

```yaml
- id: tabs
  type: TableTabs
  config:
    tabs:
      - { id: customers,    label_key: workspace.customers, view: customers }
      - { id: products,     label_key: workspace.products,  view: products }
      - { id: cost_centers, label_text: "Kostenstellen",    view: entity, entity_key: cost_center }
      - { id: cs_inbox,     label_key: workspace.inbox,     view: inbox, scope: customer_service }
```

Optional per-tab fields: `default_status_filter` (string passed to the
view as initial filter), `count_kpi` (KPI id whose current value is
shown as a badge on the tab strip), `label_text` (overrides
`label_key` with a literal string).

### Charts
All chart widgets share the same data-source machinery (see next
section). Types: `LineChart`, `BarChart`, `AreaChart`, `DonutChart`,
`StackedBarChart`, `HorizontalBarChart`, `GaugeChart`, `FunnelChart`,
`RadarChart`, `TreemapChart`, `HeatmapChart`, `WaterfallChart`,
`ScatterChart`. Pick the one that matches the data shape; if in doubt
`LineChart` (time series) or `BarChart` (categorical) are the safe
defaults.

### Interactive — let the user trigger an agent from the dashboard
| `type` | Purpose | Core config keys |
|---|---|---|
| `Agent` | Embed a chat / form / button-trigger surface for one or more custom-agent slots | `agents: [{agent_name, agent_type, label?}]`, optional `chat`, `form`, `button` |

The shape rendered (chat / form / button) is derived from the
referenced agent slots' cadence. Button-shape supports multiple agent
slots in a row; chat and form are always single.

### Other
| `type` | Purpose | Core config keys |
|---|---|---|
| `HtmlBox` | Free-form HTML / Markdown card (use sparingly) | `html` |
| `SetupSystemMap`, `SetupMilestoneRail`, `OnboardingCockpit`, `SetupSunburst`, `SetupProgress` | Onboarding-tab visuals (rarely useful on a normal dashboard) | varies |

A custom dashboard is just an ordered list of widget instances with
their `config` and a `layout` block referencing them by id.

## Data source for chart widgets

Chart widgets (LineChart, BarChart, DonutChart, …) support three
data sources. Under the hood **all three end up as PostgreSQL
against the Xentral analytics engine** — the only difference is who
wrote the SQL:

1. **`preset`** — built-in dummy dataset from the repo (no SQL,
   static demo data). Good for layout tests and onboarding
   screenshots. No real numbers.

2. **`report`** — the user picks an existing analytics report from
   the Xentral catalog (e.g. "Net revenue per project"). The SQL was
   hand-written there — the hub only stores the `reportId` and pulls
   the result via the analytics API. Recommended when your team
   already maintains reports and you want to surface them 1:1 on a
   dashboard.

3. **`prompt`** — user describes what the chart should show in plain
   text. Co-Pilot generates PostgreSQL (with schema awareness via
   `/api/v1/analytics/documentation`); on "Übernehmen" a new report
   is automatically created in the "Agent Hub — generated"
   collection and linked to the widget. **The generated SQL can be
   edited before saving** (the "SQL einsehen" disclosure in the
   widget editor) — or rewritten from scratch by hand. When the
   widget is later deleted, the report is removed via the lifecycle
   cleanup hook.

Rule of thumb: `report` for a curated catalog of vetted reports,
`prompt` for ad-hoc visualisations an operator can phrase themselves.

Per widget the **refresh mode** (applies to `report` and `prompt`,
ignored for `preset`):

| `cacheMode` | Behaviour | When |
|---|---|---|
| `live` | Every render goes straight to Xentral | Day-fresh KPIs, small/quick queries (< 400 ms) |
| `cached` | Cached with a configurable lifetime (default 5 min) | Default for everything else — pick the TTL to match the refresh expectation |

**Per-widget TTL** (only `cached` mode): `cacheTtlSeconds` in the
widget config — e.g. `60` (1 min), `3600` (1 h), `86400` (24 h).
Sentinel `-1` = until next midnight UTC ("daily reset"); every
widget on that anchor flips to fresh data at the same instant. Heavy
reports and frozen periods just use `cached` with a long TTL (e.g.
`-1` for daily, `604800` for weekly). The Co-Pilot picks an
appropriate TTL automatically when the prompt names a cadence
(`daily` / `hourly` / `weekly` / `monthly`).

On "Testdaten anfordern" the execution time is measured and a cache
recommendation is set automatically (`< 400 ms` → live, otherwise
`cached` with a matching TTL). Semantic keywords in the prompt
override (`aktuell/heute/offen` → live, `letztes Jahr/Q3/Vorperiode`
→ cached with a long TTL).

## Public access (share link)

A dashboard can expose a public, login-free URL per tenant — useful
for a "daily numbers" board on a team-room display where you don't
want to hand out accounts. Enable it in the editor under "Öffentlicher
Link" → the backend mints a one-time `share_id` (12 URL-safe chars,
72 bits of entropy) → URL `/public/dashboard/{share_id}` is live
immediately.

### What renders publicly

| Widget type | Behaviour in the public view |
|---|---|
| `HeroStats`, `KpiGrid` | **Cached KPI values only** — the last persisted `current` value from the store. No live resolve against Xentral. |
| Charts (`LineChart`, `BarChart`, …) | **Always cached** (Redis read-through), regardless of the widget's `cacheMode`. A `live` widget is treated as `cached` in the public view. |
| `TableTabs` | Widget renders, but the embedded workspace lists need an authenticated endpoint — they stay empty in the public view. |
| `Agent` (slot with `cadence=form`) | **Rendered** — fields + submit. A submission queues a job exactly like the standalone `/f/{share_id}` link does. |
| `Agent` (slot with `cadence=chat`) | **Not rendered** — no streaming/run backend without auth. Use a separate chat-slot share for public chat (see Agents guide). |
| `Agent` (slot with `cadence=button`) | **Not rendered** — trigger buttons require a user context. |

Why cache-only: a public link can be hit by anyone; if the public
view triggered live queries, a single shared link could overload the
ERP. The guarantee is **zero** Xentral roundtrips on a public
dashboard fetch.

### Token

The link alone is valid. Optionally a **token** can be set as a
second gate (`?token=…`, max 128 chars, constant-time comparison).
The token is **optional** here — unlike PDF shares, where it is
mandatory.

All failures — unknown `share_id`, wrong token, deactivated share —
map to an identical `404` so a share's existence stays opaque to
anonymous callers.

### Rate limits

The public dashboard itself is read-only and served from the widget
cache — no dedicated rate limit. **Embedded form widgets use the
form-public limiter:** 12 submissions / 60 s per `share_id`,
in-process sliding window (see the Agents guide). Running a link
with an embedded form on a public display therefore has a
conservative write gate.

The limiter is **per process** — in a multi-worker setup the effective
limit multiplies by the worker count. A Redis-backed limiter is open
work.

### Rotation

Rotate the `share_id` when the audience changes. The old URL becomes
invalid immediately; token and `is_active` are preserved. Deactivating
without deleting also works — the public endpoint then returns `404`
until reactivated.

## Constraints & invariants

1. **Widgets pull data through approved sources only.** No raw
   SQL injection from a config field. The catalog is the safety
   surface — operators (and agents) compose from it, they don't
   extend it at runtime.

2. **Read-only.** Dashboards never write to the ERP. Even a "mark
   as paid" link in a widget routes to the relevant action page;
   it doesn't happen inline on the dashboard.

3. **Tenant-scoped.** No cross-tenant dashboards. Even sister
   companies see only their own data. Built-ins are tenant-instanced
   so visibility flags are per tenant.

4. **`slug` is stable.** Once a dashboard exists and is bookmarked,
   renaming the slug breaks links. Rename only the title.

5. **Performance is a constraint.** A dashboard auto-refreshes;
   queries that take 10 seconds will hammer the ERP. The catalog
   marks expensive widgets — agents should warn the operator before
   placing many of them on one page. **For Co-Pilot widgets with
   high execution time, always recommend `cached` with a long TTL**
   (e.g. `-1` for daily or `604800` for weekly), not `live`.

6. **Co-Pilot reports belong to widgets.** Reports in the "Agent
   Hub — generated" collection are 1:1 bound to widgets. Deleting
   the widget deletes the corresponding Xentral report automatically
   (lifecycle cleanup on dashboard save). Never edit these reports
   directly in Xentral — the widget config (prompt + SQL) is the
   source of truth.

7. **The public view is cache-only.** A public dashboard link never
   triggers a live Xentral roundtrip. KPI tiles use the persisted
   `current` value; chart widgets go through the read-through cache,
   regardless of `cacheMode`. Chat and button slot widgets are
   omitted in the public view — only form slots are rendered.

## Pre-flight checks

Before creating or modifying a dashboard:

1. **Read `business_plan.profile`** — `business_model` and
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

## Common pitfalls

| Pitfall | Why it breaks |
|---|---|
| Recreating a built-in as a custom | Maintenance burden doubles; updates to the built-in don't carry over. Re-enable instead. |
| Cramming 15 widgets on one page | Auto-refresh becomes a load problem; the user loses focus. 5–8 widgets per dashboard. |
| Naming dashboards generically ("Dashboard 1") | Six months later nobody knows what it is. Each dashboard answers one named question. |
| Putting heavy chart widgets in the first row | They render last; the user sees the page jump. Lead with KPI tiles, charts below. |
| Different time periods on widgets that compare to each other | "Revenue today" next to "AOV last 30 days" doesn't compute. Synchronize period across a board. |
| Inventing currencies | Stick to the tenant's ERP currency; don't auto-convert. |
| Treating dashboard as the source of truth | It's a view. If a number looks wrong, the data source is wrong, not the dashboard. |

## Recipes (common flows)

1. **First-time dashboards setup.**
   - Read `business_plan.profile`.
   - List built-ins matched to the profile (e.g. for `b2b` +
     `wholesale` → "Open orders", "Customer credit risk",
     "Supplier deliveries").
   - Walk the operator through, enable the relevant ones, hide
     the rest.

2. **Custom dashboard for a specific role.**
   - Ask the operator: "what would this person check first in
     the morning?" — three to five concrete questions.
   - For each question, propose one widget from the catalog.
   - Place KPI tiles top, tables / charts below.
   - Pick a stable, descriptive slug.

3. **Audit existing dashboards.**
   - List custom dashboards.
   - For each, sample-render and check: any widget data sources
     broken (404/500), any zero-utility tile (always 0, always
     N/A).
   - Propose removing or fixing.

4. **Hide an unused built-in.**
   - List enabled built-ins.
   - For each, count views in the last 90 days (if you have
     telemetry) — propose hiding ones nobody looks at.

5. **Create a Co-Pilot chart from a prompt.**
   - User describes the question ("Revenue per month last year").
   - In the widget editor set `dataSource=prompt`, type the prompt,
     "Vorschlag generieren" → SQL + chart-type suggestion arrives.
   - Optional "Testdaten prüfen" for a sanity check.
   - On "Übernehmen" the report is auto-created in the "Agent Hub
     — generated" collection and linked to the widget.
   - Accept the cache-mode recommendation, or override deliberately.

6. **Nightly refresh for all data widgets on a dashboard.**
   - Via cron / agent schedule, call the MCP action
     `xentral_dashboards.refresh_all_widgets` with the dashboard
     slug.
   - Returns a summary `{refreshed_count, skipped_count,
     failed_count, …}`. `skipped` contains widgets without a
     `reportId` (presets, unsaved prompts) — expected, not an error.

## Out of scope

* Inventing new widget *types* at runtime. New types are code
  changes in the catalog.
* SQL or query editing inside a dashboard outside the Co-Pilot flow
  (`dataSource=prompt`). The Co-Pilot is the only sanctioned
  ad-hoc SQL surface.
* Direct editing of reports inside the "Agent Hub — generated"
  collection. The widget config is the source of truth, not the
  Xentral report.
* Cross-tenant rollups. Each tenant is its own world.
* Acting on the data (issuing refunds from a table widget,
  paying from a KPI tile). Dashboards link to the action pages;
  they don't perform actions.
