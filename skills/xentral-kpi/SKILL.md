---
name: xentral-kpi
description: >
  Register, update, and read tenant business metrics with the xentral_kpi tool.
  Covers the central KPI store (counts, sums, ratios, durations with DE/EN
  labels, units, groupings, and full value history), starting from the KPI
  library, push vs derived (SQL/prompt) KPIs, recording values without
  duplicating a number across the product, and how dashboard cards read from
  the store. Use when the user wants to track a new business metric, record a
  computed value, or ask for the current value/history of a KPI.
---

# KPI

## Purpose

The KPI store is the **central KPI store for a tenant**. It holds named
business metrics — counts, sums, ratios, durations — together with
their human-readable labels (DE/EN), units, optional groupings, and a
full history of every value ever written. KPI cards across the
product read from the KPI store so the same number never lives in two places.

## When to call

* The operator wants to **register a new KPI** ("track open returns
  count from now on") — call ``init`` once with metadata.
* An agent computed a fresh value for a KPI that already exists —
  call ``set_value`` to record it. The previous value is archived to
  history automatically.
* The operator asks "what's the current value of X?" — call ``get``
  on the specific key, or ``list`` to see all KPIs.
* A KPI is no longer being tracked and should disappear from the
  default dashboard view — call ``set_active`` with ``active=false``.
  KPIs are never deleted; deactivated ones stay queryable.

**Do not** call:

* To compute the value itself — the KPI store keeps values, it doesn't
  calculate them. Run the query / count / aggregation elsewhere,
  then write the result.
* To answer "what changed in the data?" — the KPI store is the surface,
  not the source. The change happened in the ERP / job / external
  system; the KPI store just reflects it.
* For ad-hoc one-off numbers — only register a KPI you plan to
  update repeatedly.

## Concepts & vocabulary

| Term | Meaning |
|---|---|
| KPI | A named, tenant-scoped business metric. Has a stable ``key``, multilingual labels, a unit, and a value type. |
| ``key`` | Stable snake_case identifier. Used in URLs and as the lookup id from KPI cards. Never rename — it would break consumers. |
| ``labels`` | ``{"de": "…", "en": "…"}`` map. ``en`` is required. |
| ``unit`` | Display unit string: ``count``, ``EUR``, ``%``, ``days``, etc. Free-form. |
| ``value_type`` | Format hint for renderers: ``number``, ``currency``, ``percent``, ``duration``. |
| ``group`` | Optional grouping label (e.g. ``customer_service``, ``finance``). |
| ``active`` | Visibility flag. Inactive KPIs are filtered out of default lists but stay readable by key. |
| ``current.value`` | The latest value written. |
| ``current.previous_value`` | Previous-period value for Co-Pilot KPIs with trend (``value_source != push`` + ``output_shape=value_with_trend``). Enables Δ% display in the KPI card. |
| ``current.as_of`` | The business timestamp the value refers to (defaults to write time). |
| ``current.updated_at`` | The write timestamp itself. |
| ``value_source`` | Where the value comes from: ``push`` (manual / agent), ``live`` (Co-Pilot SQL, every read hits the ERP) or ``cached`` (cached, TTL via ``cache_ttl_seconds``). Default ``push``. |
| ``report_id`` | Linked Xentral analytics report (only for non-``push`` sources). Cleaned up automatically on delete. |
| ``prompt`` / ``sql_string`` | Audit fields on Co-Pilot KPIs: the original natural-language prompt + the SQL it generated. |
| ``track_history`` | Bool, only meaningful on derived KPIs. Default ``false`` (no timeline). When ``true`` the live resolver appends a row on every **value change** — push KPIs ignore the flag because they already write history on every ``set_value``. |
| history | Append-only log of values written, sharded by ``YYYY-MM``. Push KPIs: every ``set_value`` call. Derived KPIs: only when ``track_history=true`` AND the newly resolved value differs from the last entry (dedup against spammy reads). Otherwise empty — the value is computed at read time from the report with no timeline. |

## Lifecycle

```
[doesn't exist] --init--> [active] <--set_active--> [inactive]
                              |
                              +-- set_value (push)     → archives old, writes new
                              +-- get / list (derived) → value resolved from report
```

1. ``init`` registers a KPI with ``value_source`` (default ``push``).
   Calling ``init`` again on the same key is an error.
2. **Push KPI** (``value_source=push``): ``set_value`` writes new
   values; the previous value rolls into the monthly history shard.
   Classic flow for anything computed externally (agent, cron job,
   human).
3. **Derived KPI** (``value_source`` in ``live`` / ``cached``):
   ``set_value`` is blocked (returns 400). The value is resolved on
   ``get`` / ``list`` by querying the linked Xentral report —
   transparent via the shared cache layer.

   Under both modes it's **always PostgreSQL against the Xentral
   analytics engine** — the Co-Pilot builds the SQL from the prompt
   ("number of open orders"); the user can edit it before saving
   (the "SQL einsehen" disclosure in the KPI init dialog) or type
   it manually from scratch. Live/Cached only decide *when* that SQL
   gets re-run:
   - ``live`` — on every KPI read (day-fresh, small/fast queries)
   - ``cached`` — cached with a configurable TTL via
                ``cache_ttl_seconds`` (default 300 = 5 min; ``-1`` =
                until next midnight UTC for "daily reset"; up to
                30 d). Heavy reports or frozen periods just use
                ``cached`` with a long TTL.

   **Enabling a timeline on live/cached KPIs.** By default both modes
   keep no history — every read overwrites the previous value in the
   envelope and the prior reading is lost. If you need a sparkline, a
   trendline, or a queryable "open orders over the last 30 days" view,
   call ``set_track_history`` with ``enabled=true``. From that point
   on the resolver appends one row per **value change** (deduped
   against the most recent history entry) into the same monthly
   shards that push KPIs use. ``history`` and ``get`` with
   ``include_history=N`` read from that same store for both source
   types — the consumer can't tell push and derived history apart.
   Turning it back off (``enabled=false``) stops new appends; the
   rows already collected remain readable.
4. ``set_active(false)`` hides the KPI; ``set_active(true)`` brings
   it back. Values can only be written to active push KPIs.
5. ``delete`` also cleans up the linked Xentral report and
   cache entries (best-effort, swallows failures).

## Constraints & invariants

1. **No silent creates.** ``set_value`` on an unknown key is an
   error, not an implicit create. Catches typos before they fragment
   the metric.
2. **Keys are immutable.** Don't rename — the cards reading the KPI
   pin it by key. If a metric changes meaning, ``init`` a new key
   and ``set_active(false)`` the old one.
3. **Tenant-scoped.** No cross-tenant KPIs. Even sibling licenses
   stay separate.
4. **History is forever.** Every ``set_value`` adds a history row,
   even if the value is identical to the previous one. The KPI store is
   the audit log of KPI evolution.
5. **Read paths are cheap.** The KV layer is cached. ``list`` walks
   the index, then reads one object per KPI.
   For a tenant with hundreds of KPIs the right pattern is ``list``
   once on the frontend, not ``get`` per card.
6. **Derived KPI = no ``set_value``.** To overwrite the value
   manually you have to switch source (delete + re-init with
   ``value_source=push``).
7. **Pick source by freshness need:**
   - ``live`` for day-fresh numbers and small/fast queries
   - ``cached`` as the default for derived KPIs — cached, TTL via
     ``cache_ttl_seconds`` (5 min for live operations, ``-1`` for
     daily-reset on heavy reports / frozen periods, ``604800`` for
     weekly, etc.).

## Tool actions

| Action | Required args | Notes |
|---|---|---|
| ``init`` | ``key``, ``labels``, ``unit``, ``value_type`` | ``group``, ``initial_value`` optional. For derived KPIs also ``value_source`` (live/cached), ``report_id``, ``prompt``, ``sql_string``, ``cache_ttl_seconds``. ``initial_value`` is rejected for derived KPIs. |
| ``set_value`` | ``key``, ``value`` | ``as_of`` optional. Fails if KPI is missing, inactive, or ``value_source != push``. |
| ``get`` | ``key`` | For derived KPIs returns the current value resolved from the linked report (transparent via the cache layer). |
| ``list`` | — | ``group`` and ``active_only`` (default true) filter. Resolution of derived values is best-effort — failures land in ``current_error``. |
| ``set_active`` | ``key``, ``active`` | Toggles visibility. |
| ``set_track_history`` | ``key``, ``enabled`` | Derived KPIs only (live/cached). Toggles persistent history-recording — from then on the live resolver appends a row whenever the value changes. Push KPIs return 400 (they already record on every ``set_value``). |
| ``history`` | ``key`` | Returns rows oldest first. Always populated for push KPIs. For derived KPIs the list is only non-empty after ``set_track_history(enabled=true)`` has been called and the value has changed at least once. |
| ``delete`` | ``key`` | Also tears down the linked Xentral report + cache entries. |
