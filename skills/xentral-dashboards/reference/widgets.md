# Dashboards — widgets & data sources

## Widget structure

Each widget declares:
* **`id`** — unique within the dashboard, used in layout references.
* **`type`** — exact class name from the catalogue below.
* **`config`** — type-specific shape (see the catalogue).

The dashboard `layout` references widget ids. There are two dialects.

### `split` — sidebar + main column (the simple form)

```yaml
layout:
  type: split
  main: [greeting, hero, kpi_grid]
  side: [tabs]
```

`main` and `side` are each a vertical list of rows. A row is a widget
id, or an array of ids for an equal-width side-by-side row.

### `grid` — flexible column weights (the general form)

```yaml
layout:
  type: grid
  rows:
    - cols: [5, 7]        # 5:7 two-column row
      cells: [["cockpit"], ["setup_tree", "onboarding_tasks", "kpi_hero"]]
    - cols: [12]          # full-width row
      cells: [["big_table"]]
```

- **`cols`** — the column template: numbers are relative weights
  (`[8,4]` = 2:1, `[4,4,4]` = thirds, `[12]` = full-width). `{px:n}` /
  `{fr:n}` objects give fixed / flexible tracks.
- **`cells[i]`** fills column `i`. **Always write each cell as an
  array of widget ids** — `[["a"], ["b","c"]]`, never a bare `["a", …]`
  mixed with strings. A single-widget column is `["id"]`; a stacked
  column is `["id1", "id2", …]`. (The renderer also tolerates a bare
  string, but the array form is the convention every built-in uses —
  stay consistent so edits don't have to guess the shape.)

Every widget id in `widgets[]` must be referenced exactly once in the
layout, and every id the layout references must exist in `widgets[]` —
an unreferenced widget never renders, a dangling reference is a no-op.

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
`action='list'` to enumerate them per instance. This is the only
place across all dashboard widgets where a raw `entity_key` is
accepted; everywhere else use the named views above. The entity
catalogue is the lowest ERP layer (raw data model), distinct from
the workflow-recipe layer (`xentral_business_skills list_library`)
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

#### Start from the chart library
Before hand-writing a chart, check the **chart library** — a catalogue
of pre-baked, reusable chart cards (`library/charts/`, exposed read-only
at `GET /chart/library` and `/chart/library/{card_id}`). Each card ships
a chart `type`, a `cache_mode` (`live` | `cached` | `snapshot`), a
natural-language `prompt` and a ready `sql_string`, categorised by
domain (`sales`, `customers`, `orders`, `inventory`, `logistics`,
`purchasing`, `finance`) — e.g. `revenue_monthly_trend`,
`top_customers_ytd`, `carrier_mix`. Charts are **not driven by their own
MCP tool**; a library card is the starting payload you drop into a chart
widget here (the `chart.type` + `sql_string`/`prompt` map straight onto
the widget's data source). Clone the closest card and adapt rather than
writing SQL from a blank slate.

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
| `HtmlBox` | Free-form HTML / Markdown card (use sparingly) | `htmlContent` |
| `SetupSystemMap`, `SetupMilestoneRail`, `OnboardingCockpit`, `SetupSunburst`, `SetupProgress` | Onboarding-tab visuals (rarely useful on a normal dashboard) | varies |

> **`HtmlBox` config key is `htmlContent`, not `html`.** A wrong key
> renders a silently *empty* box (no error). The value is either a
> plain HTML string or a `{de, en}` object that the loader localises:
>
> ```yaml
> - id: intro
>   type: HtmlBox
>   config:
>     htmlContent:
>       de: "<h2>Willkommen</h2><p>…</p>"
>       en: "<h2>Welcome</h2><p>…</p>"
> ```

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

