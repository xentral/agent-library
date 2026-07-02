# Workflows — code nodes, helpers & data

## Code node — what's allowed

> Reaching for a `code` box means you've already ruled out every data and flow node above (see the node-first principle at the top of "Available node types") — Code is the exception, not the default. What follows is the sandbox contract for that exceptional case.

`code`, `condition`, `expression`, `while` (raw `expression`) and `loop`/`worklist` roll-up values all run through the same sandbox (an AST allowlist, then an isolated subprocess). Write to the allowlist so you never have to discover the rules by trial-and-error — anything not listed is rejected before the run with a `CodeValidationError`.

**Allowed:** `if`/`elif`/`else`, `for`, `while`, `break`, `continue`, `pass`; `def` + `return` (use a named function where you'd reach for a lambda); assignments and augmented assignments; comprehensions (list/set/dict/generator); f-strings; slicing and subscripts (`x[1:3]`, `d["k"]`); attribute access and method calls (`row.get(...)`, `items.append(...)`); all arithmetic/boolean/comparison/bitwise operators and the ternary `a if c else b`.

**Allowed builtins (these only):** `abs bool dict enumerate float int len list max min print range round set sorted str sum tuple zip` plus `True False None` and the exceptions `ValueError TypeError KeyError IndexError ZeroDivisionError Exception`. Anything else (`map`, `filter`, `any`, `all`, `reversed`, `sorted`'s `reverse=` aside, `re`, `json`, …) is **not** in scope at runtime. The workflow helpers `business_entity_op`, `xentral_op`, `xentral_request`, `log`, and the JSON helpers `to_json` / `parse_json` (see below) are also in scope.

**Not allowed (hard reject):**
- `lambda` — use a named `def` instead (`sorted(rows, key=by_qty)` with `def by_qty(r): return r["min_qty"]`), or an explicit loop.
- `import` / `from … import`, `with`, `try`/`except`, `raise`, `class`, `async`/`await`/`yield`, `global`/`nonlocal`.
- The calls `eval exec compile open input breakpoint getattr setattr delattr vars globals locals memoryview __import__`.
- Dunder names (`__import__`, `__builtins__`) and any `_`-prefixed attribute access (`x.__class__`, `x._internal`) — ordinary methods like `.get`/`.append`/`.strip` are fine.

**Size limit:** max. **500 non-empty lines** and **100,000 characters** per code box. Larger code must be split across multiple code boxes or visible workflow nodes.

**Readability limit:** Write code so a workflow builder can read it in the inspector. No semicolon compression, no one-letter helper functions, no nested mini-parsers, and no hidden fixed ERP reads/writes. Longer code is okay when it is cleanly structured, has English comments on the important sections, and `description`/`algorithm` explain the flow without requiring the reader to inspect the Python.

**Lambda replacement patterns:**
```python
# sort: instead of sorted(tiers, key=lambda t: t["min_qty"])
def by_min_qty(t):
    return t["min_qty"]
tiers_sorted = sorted(tiers, key=by_min_qty)

# or a plain loop (no key function at all):
best = None
for t in tiers:
    if qty >= t["min_qty"] and (best is None or t["min_qty"] > best["min_qty"]):
        best = t
result = best["price"] if best else None
```

## JSON — output and parsing

You almost never need to build JSON by hand, and you should not: string-concatenating a serializer (`'{"id":' + esc(x) + …`) is brittle, trips the code-complexity check, and hides a real bug the day a value contains a quote or newline. Two in-scope helpers cover every case:

- **`to_json(obj)` → JSON string.** Use it whenever a Code box must *produce* JSON text: an `http-request` body, a file payload, any field that has to be JSON. It escapes for you and — unlike the run's output preview — is **not** truncated, so a feed with thousands of items comes out complete. Values JSON can't represent directly (dates, `Decimal`) are coerced to strings rather than crashing.
- **`parse_json(text)` → Python objects** (dict/list/scalars) from a JSON string; returns `None` for a non-string or invalid input, so a bad payload never crashes the box.

**When you need neither:** to pass structured data to another **code / logic** node, just assign the dict or list to `result` — downstream boxes and `{{ }}` value refs receive the raw Python object, no serialization involved. Reach for `to_json` only at the boundary where the value must become a JSON *string* (a text field like an HTTP body renders a referenced dict as its Python `repr`, which is **not** valid JSON — so serialize it there).

```python
# BAD — hand-rolled serializer: brittle, trips the complexity check
def esc(v): ...
products_json = '[' + ','.join(item_to_json(i) for i in items) + ']'
result = '{"products":' + products_json + '}'

# GOOD — one call, full and correctly escaped; feed this to the HTTP body
result = to_json({"meta": {"generatedAt": now(), "count": len(items)}, "products": items})
```

## Date helpers

ERP automations almost always filter by date: "older than 7 days", "last month", "overdue". The engine ships **date helpers** for this — ready functions resolved at **run time** in the **tenant timezone** (no hardcoded ISO strings, no freezing on scheduled runs). Point-in-time helpers return **ISO strings** (so a value drops straight into a filter), duration/comparison helpers return `int`/`bool`, and range helpers return a `{gte, lte}` dict.

**Where you use them:**
- **Filters / write values** (`business-entity` / `xentral-api` `params.<op>.{path,query,body}`): as a binding `{ "mode": "date", "expr": "<call>" }` (the 90% case).
- **Compute-value node** (`expression`): in a `{{ }}` hole, e.g. `"{{ start_of('month', -1) }}"`.
- **Condition / code** (`condition` / `code`): call directly — `is_overdue(order['dueDate'])`, `days_since(inv['date']) > 30`.

**Functions:**

| Function | Returns | Meaning |
|---|---|---|
| `now()` | datetime ISO | now (with tz offset) |
| `today(offset=0, unit="days")` | date ISO | today; `today(-7)` = 7 days ago, `today(-1,"months")` |
| `yesterday()` / `tomorrow()` | date ISO | sugar for `today(-1)` / `today(1)` |
| `shift(value, n, unit="days")` | same as input | shift any date; `shift(invoiceDate, 30, "days")`; month-end clamps (31→28) |
| `start_of(unit, offset=0)` | datetime ISO | period start (00:00). `unit` ∈ day/week/month/quarter/year |
| `end_of(unit, offset=0)` | datetime ISO | period end, **inclusive** (…59.999) |
| `period(unit, offset=0)` | `{gte,lte}` | a period's range |
| `last(unit)` / `this(unit)` | `{gte,lte}` | sugar = `period(unit,-1)` / `period(unit,0)` |
| `ytd()` | `{gte,lte}` | year start to now |
| `last_n_days(n)` | `{gte,lte}` | last n days to now |
| `days_between(a, b)` | int | b − a in days |
| `days_since(d)` / `days_until(d)` | int | relative to today |
| `is_overdue(d)` | bool | `days_since(d) > 0` |
| `is_before(a,b)` / `is_after(a,b)` / `between(d,lo,hi)` | bool | comparisons |
| `age_bucket(d, edges=[30,60,90,120])` | str | AR aging: `"0-30"`/`"31-60"`/…/`"120+"` |
| `business_days(n, anchor=None, region=None)` | date ISO | +n business days (skips weekends **and the tenant region's public holidays**) |
| `next_business_day(anchor=None)` / `is_business_day(d)` | date ISO / bool | next workday / is workday |

**Range spread:** a `{gte,lte}` value in `query` is auto-expanded into bracketed keys — `"invoiceDate": last('month')` → `invoiceDate[gte]=…&invoiceDate[lte]=…`. For a one-sided bound, write a scalar with an explicit operator key instead: `"createdAt[lt]": { "mode": "date", "expr": "today(-7)" }`.

**Examples mapped to ERP algorithms:**
```jsonc
// Cancel prepayment (>7 days):     "createdAt[lt]": { "mode": "date", "expr": "today(-7)" }
// OPOS digest last month:           "invoiceDate":   { "mode": "date", "expr": "last('month')" }
// Best-before early warning (<30d):  "bestBefore[lte]": { "mode": "date", "expr": "today(30)" }
// Cash-discount deadline as a write: "skontoUntil":   { "mode": "date", "expr": "shift(today(), 10, 'days')" }
// Dunning tier in a condition:       condition.expression: "30 < days_since(inv['dueDate']) <= 60"
// AR aging label in a code box:      result = age_bucket(inv['dueDate'])
```

**Limits / gotchas:**
- **Helper arguments inside `{{ }}` holes must be literals** (`today(-7)`, `start_of('month',-1)`). To compute off an upstream **node value** (e.g. `invoiceDate + 30 days`), use a `condition`/`code` box — variable names are directly available there (`shift(order['invoiceDate'], 30, 'days')`).
- **`today()` returns a plain date, `start_of`/`end_of` return datetimes** — deliberate: "older than" wants a date, "last month" wants a clean upper bound 23:59:59.
- **`mode:"date"` allows ONLY date-helper calls** (no arbitrary names/calls). An empty `expr` is treated as unset (→ `None`); an invalid `expr` fails **only the affected node at run time** with a clear error (no silently-sent `"today(-7)"` filter value) — the rest of the workflow still renders/runs.
- **Holidays:** the business-day helpers skip weekends **and** the applicable region's public holidays. Region cascade: **workflow envelope field `holiday_region`** (e.g. `"holiday_region": "US"` for a US workflow) → empty = derived from the timezone → none (weekends only). So one tenant can run a DE workflow and a US workflow side by side. Values are `CC` or `CC-SUB` (`DE`, `DE-BY`, `US-CA`). The function's `region` param is unnecessary. Coverage is a window around "today" (last year .. +2y); date math far outside it falls back to weekends-only.
- **NOT yet included:** **fiscal-year offset** (`year`/`quarter` are calendar periods). Coming later.

## Tool actions

| Action | Required args | Notes |
|---|---|---|
| `help` | — | Returns this guide (pass `locale='en'` or `'de'`). |
| `list` | — | All workflows for the tenant, newest first. |
| `get` | `id` | Full envelope for a single workflow. |
| `init` | `id`, `name` | Create a new workflow. Optional `description`, `trigger_type`, `nodes`, `edges`, `enabled`. Duplicate id → error. |
| `update` | `id` | Patch semantics — only passed fields are overwritten. `id` and `created_at` are protected. |
| `delete` | `id` | Hard-delete including index entry. |

## Fetching data vs. computing

Decide deliberately where each data access lives. Don't cram everything into one code block, and don't force every fetch into its own node either — pick per access.

**Source preference (in this order):**
1. Is there a `business-entity` for it? → use the **business-entity** node. Friendliest, catalog-backed, real labels.
2. No matching business entity? → use a **`xentral-api`** node against the raw Xentral endpoint.
3. Not a Xentral call at all? → **`http-request`**.

**Where the access lives:**
- **Default — one node per access.** Each fetch/write is its own `business-entity`/`xentral-api` node. It streams started/finished, shows as a box in the run timeline, and is rewireable and reusable.
- **Code/logic nodes are glue only** — transform, decide, aggregate over data that was *already* fetched.
- **Exception — fetch inside code when the number or depth of accesses is data-dependent** (recursion, unknown nesting, paging). Then call `business_entity_op(...)` / `xentral_op(...)` directly inside a `code` node (or a loop body). It's the same call as the node — it just won't appear as its own box (logs only). That's the only trade-off, and in this case it's worth it.

**One-line rule:** Do you know the number of accesses while building? → one node per access. Does it depend on the data? → fetch in code.

