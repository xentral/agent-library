# Profile enums, section catalogue, recipes & pitfalls

## Profile dimensions (strict enums)

The profile is the contract other agents key off. Read the live enum list before
calling `profile_set` — invalid values are rejected.

| Field | Type | Values | Controls |
|---|---|---|---|
| `business_model` | single | b2c · b2b · d2c · marketplace · manufacturer · wholesale · mixed | invoice phrasing, payment-term defaults |
| `sales_channels` | multi | ecommerce · marketplaces · pos · field_sales · wholesale · distributors | expected integrations |
| `fulfillment` | single | in_house · 3pl · dropshipping · mixed | shipping-doc layout, returns flow |
| `automation` | single | low · mid · high | how aggressively agents auto-act vs. ask for confirmation |
| `size` | single | small (2–10 Mio) · mid (10–50) · upper (50–100) · enterprise | feature/plan suggestions |
| `complexity` | single | simple · medium · complex | how detailed agent explanations should be |

## Section catalogue

Each section is a stable slug + markdown payload. Fill on demand — an empty
section legitimately means "not relevant yet".

- **`profile`** — the 6-dimension classification above. **Strict enums; set only
  via `profile_set`, never `write`.** Every agent reads this first.
- **`mission`** — one paragraph, max ~280 chars: what the business does, for
  whom. Skip if generic.
- **`target_market`** — whom they sell to: industries, segments, geographies,
  buying-center. Richer = better tone/content from agents.
- **`value_proposition`** — why customers pick this tenant. Honest ("lowest
  price" is fine if true).
- **`offering`** — high-level product/service categories, bundles,
  configurable-vs-catalog. Not the SKU list (that's the ERP).
- **`channels`** — where the offering meets the market: webshop, marketplaces,
  distributors, field sales, partners.
- **`operations`** — how work flows: intake → fulfillment → invoicing →
  support. Bullet flow, not prose.
- **`team`** — roles + approximate headcount.
- **`pain_points`** — self-reported. The single most useful section for agent
  prioritization.
- **`goals`** — what the operator wants this quarter/year. Short bullets.
- **`tech_stack`** — Xentral plus Shopify, DATEV, WMS, CRM, BI, … Drives which
  integrations matter.
- **`tone`** — formal / neutral / warm. Read by every customer-facing agent
  before drafting text.

## Constraints & invariants

1. **`profile` is write-only via `profile_set`** — the plain `write` path skips
   enum validation.
2. **Read before replace** — precede every `write(mode='replace')` with a `read`
   of the same slug in the same turn.
3. **`apply_template` is destructive only with `overwrite=true`** — default
   `false`; flip only after explicit user consent.
4. **Per-tenant, never shared** — no cross-tenant copying, even between sister
   companies.
5. **The model is *living*** — after any strategic conversation, propose updates
   to the relevant sections.

## Pre-flight: what every business-logic agent should read first

`profile` (enum values) · `target_market` (audience) · `tone` (phrasing). A
short read prevents B2C-style copy for a B2B distributor.

## Recipes

### First-time setup
1. `apply_template(template='ai_first', overwrite=false)` — seed all sections.
2. `profile_set(business_model=…, sales_channels=[…], …)` — classify the tenant.
3. Walk each skeleton section with the user in one short confirm/correct pass.

### Strategic update ("we acquired a competitor in Austria")
1. `read(slug='target_market')` and `read(slug='operations')`.
2. Propose deltas to the user.
3. `write(slug='target_market', mode='replace', …)` and keep `operations` in
   sync; optionally update `tech_stack` / `team`.

### Quick fact add ("we launched a French webshop")
1. `read(slug='channels')`.
2. `write(slug='channels', mode='append', markdown='- French webshop …, launched 2026-03')`.

### Context probe before another agent
- `read(slug='profile')` → check `business_model` + `automation` for the
  auto-approve threshold; `read(slug='tone')` → pick the phrasing register.

## Pitfalls

| Pitfall | Why it breaks |
|---|---|
| Free-text into `profile` via `write` | Bypasses enum validation; breaks every downstream agent. Use `profile_set`. |
| Filling all sections eagerly | Empty signals "not relevant yet"; fill on demand. |
| Treating `apply_template` as idempotent | With `overwrite=true` it overwrites. Default `false`. |
| Copying marketing-site content | The model must reflect *actual* operations, not aspirations. |
| Using a section as a chat log | Distill what the user said; don't paste the conversation. |

## Out of scope

Task/project progress → `xentral_operations_tasks`. Day-to-day decisions → Jobs.
Financials / budgets / P&L → out of system. Per-customer notes → CRM.
