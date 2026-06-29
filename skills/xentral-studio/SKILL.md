---
name: xentral-studio
description: >
  Build per-tenant Studio apps — your own Mobile or Desktop screens, forms, and
  tables on top of the global Business-Entity catalogue — with the
  `xentral_studio` tool. Covers the app/screen/component model, starting from a
  built-in template instead of a blank app, binding components to real entities
  and KPIs, wiring buttons to screens/dialogs/MCP tools, and the
  create/update/enable workflow. Use when the user needs a custom operational
  screen the standard ERP UI doesn't offer — a warehouse scan view, a
  field-sales order pad, a commission-run desk — not for automated step
  sequences (use xentral_workflows) or content-dependent decisions (use
  xentral_agents).
examples:
  - "Build a mobile warehouse scan app for goods receipt."
  - "Create a desktop commission-settlement screen."
  - "Give field sales a quick order-pad app on their phones."
---

# Xentral Studio

## Purpose

Studio is the **app workbench**. A Studio **App** is a composed surface — your
own screens and components (forms, tables, buttons, KPI tiles) laid *on top of*
the global Business-Entity catalogue, running as a **Mobile** or **Desktop**
app. Apps are persisted per tenant, exactly like Dashboards and Agents.

You build on top — no migration, no code deploy. The ERP core keeps carrying the
load (bookkeeping, inventory, orders, compliance); an app **references** global
entities (Customer, Product, SalesOrder, …) and lays its own screens over them.
You describe *what* the screen shows; Studio handles rendering, the live preview
(QR to a phone) and persistence.

## When to use Studio — vs. workflows and agents

- **Studio** — the user needs a **custom screen / surface** the standard ERP UI
  doesn't offer (scan view, order pad, settlement desk).
- **`xentral_workflows`** — an **automated step sequence** that runs without a
  screen.
- **`xentral_agents`** — a **content-dependent decision** (classify, draft,
  route).

A Studio app can *contain* an agent (the `formagent` / `chatagent` components)
and its buttons can call MCP tools — but Studio itself only renders surfaces and
wires actions. The business logic behind a `tool:<name>` button is a **separate
MCP tool**, not part of the screen JSON.

## The authoring contract

Your job is the app **definition**: the `form.screens[].components[]` tree and
which global entities it binds to. That tree is what renders. Wire buttons with
`props.action` = `screen:<id>` | `dialog:<id>` | `tool:<name>`.

- Exactly **one** screen is `home` (the start page).
- `screen` types appear in the menu; `dialog` types are modal, opened from a
  button, not in the menu.
- **Bindings** (`dataSource` / `kpiKey` / `agent`) must reference a real value
  from the allowed catalogues. An unknown value is **dropped on save** (the
  element falls back to a mock) — it never errors at render, but it also won't
  be live. Bind only to values that exist.
- `slug` is snake_case (`^[a-z][a-z0-9_-]{2,127}$`), unique per tenant, and must
  not collide with a built-in template slug.
- Validation is **advisory, not blocking** — writes are never rejected, same as
  the designer UI.

## Start from a template, not a blank app

Cloning a built-in template is the fastest path and starts you with correct
bindings and a sensible screen layout. Templates: `bestellvorschlag`, `lager`,
`pick`, `aussendienst`, `provisionsabrechnung`. Clone via `create` with a
`template_id`; you get a tenant-owned copy you can freely edit. Build a blank app
only when no template is close.

## The workflow (every task)

1. `action: help` — the live manual: full app/screen/component schema, the
   component-type catalogue, valid `linked_entities`. Read before authoring.
   Pass `locale='de'` for German.
2. `action: list_library` — built-in templates; `get_library` (`template_id`)
   pulls one template's full payload.
3. `action: list_entities` — the global Business-Entity catalogue an app may
   reference via `linked_entities`.
4. `action: list` / `get` (`slug`) — the tenant's existing apps.
5. **Create:** `create` — either clone a template (`template_id`) or build a
   custom app (`slug` + `name` + `form`, `platform`, `linked_entities`, …). New
   apps start as drafts (`enabled=false`).
6. **Edit:** `update` (`slug`) — patch semantics, only passed fields overwrite.
7. **Ship:** `set_enabled` (`slug` + `enabled`) — drafts are invisible to the
   team until enabled. `delete` (`slug`) hard-deletes a custom app.

## Editing the OPEN app (focus = studio_app)

When the focus block shows `entity_type=studio_app`, the user is in the Studio
IDE on that `slug`. Edit it in place with the granular actions instead of
re-sending the whole `form` — the IDE re-hydrates automatically (no reload
hint to the user):

- `compose_ui` (`slug` + `request`) — natural-language screen authoring. Pass
  ONE complete instruction in the user's language; a validated composer
  rewrites the screens and drops any hallucinated component/binding. This is
  the preferred way to change the UI.
- `write_file` / `delete_file` (`slug` + `path`, `+ content`, `lang`) — edit one
  Python code file of the app.
- `upsert_tool` / `delete_tool` (`slug` + `tool_name`, `+ tool_description`,
  `params`, `entrypoint`) — create/update/remove one MCP tool callable from a
  button via `tool:<name>`. `entrypoint` is the path of an existing code file.

A button that calls new logic = `write_file` (the logic) + `upsert_tool` (wire
it) + `compose_ui` (the button with `action: tool:<name>`), in one turn.

## Which reference to read

- **Component catalogue** — every component type (layout, text, input, data,
  agents, action), its `props`, the binding rules, and button actions →
  [reference/components.md](reference/components.md)
- **App anatomy, design patterns & guardrails** — the app/screen JSON shape, a
  minimal worked example, mobile-vs-desktop, the "designing good UIs" patterns,
  and the guardrails →
  [reference/authoring-and-recipes.md](reference/authoring-and-recipes.md)

## Don'ts

- Don't bind `dataSource` / `kpiKey` / `agent` to a value outside the allowed
  catalogue — it's silently dropped and the element goes mock.
- Don't try to implement the logic behind a `tool:<name>` button in the screen
  JSON — that's a separate MCP tool.
- Don't reuse a built-in template slug or a non-snake_case slug.
- Don't pile every field onto one screen — one job per screen, one primary
  button (see the design patterns).
- Don't ship an app the team can't see — remember `set_enabled`.
- Don't hand-write the full `form` JSON to change the OPEN app — use
  `compose_ui`; it validates and the IDE re-hydrates on its own.
