# Dashboards — sharing, constraints & invariants

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

