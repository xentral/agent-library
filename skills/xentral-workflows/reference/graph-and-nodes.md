# Workflows — graph & node contract

## Envelope shape

A stored workflow is a JSON object:

```json
{
  "id": "wf_lq0xy12_a3f7",
  "name": "Cancel prepayment orders",
  "description": "Cancels prepayment orders older than 7 days with no payment.",
  "trigger_type": "schedule",
  "orientation": "horizontal",
  "enabled": true,
  "nodes": [ /* React-Flow Nodes */ ],
  "edges": [ /* React-Flow Edges */ ],
  "created_at": "2026-06-02T08:15:00Z",
  "updated_at": "2026-06-02T08:15:00Z"
}
```

Required on `init`: `id` (snake_case, 3-64 chars, unique per tenant), `name`. Everything else optional with sensible defaults.

`orientation` sets the canvas reading direction — where the node connectors sit and how a business reader's eye travels: `"horizontal"` (left → right; inputs on the left, outputs on the right) or `"vertical"` (top → bottom). **Always build new workflows horizontal** and set `"orientation": "horizontal"` so agent- and MCP-created flows read consistently in the UI. `vertical` is **not an agent choice** — it exists only as a manual toggle the user can flip in the editor; never emit it. Lay out the node `position`s horizontally: keep `y` constant and grow `x` by ~400 per step (a card is ~320px wide); a branch offsets its two lines by `y` ±200. Tall cards are resource nodes (`business-entity`/`xentral-api`/`kpi`/`report`/`integration-action`): each declared operation renders its own row/handle, so an N-operation card is roughly `140 + 40·N`px tall — give vertically-stacked branch lines enough `y` gap that these taller cards never overlap. Gaps are harmless, overlaps are not — when unsure, over-space.

`name` and `description` are user-facing. The `description` is **markdown** and must let a business reader understand the workflow **without opening the canvas** — write it in this order: (1) what the workflow does and why, one plain opening paragraph (it doubles as the clamped card teaser, so no markup in the first paragraph); (2) optionally **How the algorithm works** with a small ASCII flow sketch in a ``` fence (branch/loop/recursion shapes earn one, a linear flow does not); (3) **What happens step by step** as a numbered list that mirrors the node titles; (4) **What gets changed** as bullets — name every write, or state explicitly that nothing is changed; (5) **Prerequisites and limits** as bullets (runtime, caps, batching). Use bold section headings exactly like that — not `#` headings. A one-line description is only acceptable for a trivial two-node flow.

## Trigger types

| `trigger_type` | When it fires | Trigger node typeId |
|---|---|---|
| `manual` | Click in UI / API call | `trigger-manual` |
| `schedule` | Cron plan (daily, hourly, ad-hoc) | `trigger-schedule` |
| `webhook` | External HTTP POST | `trigger-webhook` |
| `in-erp` | ERP event (order created, document cancelled …) | `trigger-erp-event` |
| `integration-event` | Event from a connected integration (new email, …) | `trigger-integration-event` |
| `form` | Form submit via public link | `trigger-manual` (form not yet dedicated) |

## Node shape

Every node is a React-Flow entry:

```json
{
  "id": "n_abc123",
  "type": "wfNode",
  "position": { "x": 80, "y": 80 },
  "data": {
    "typeId": "trigger-schedule",
    "config": { "schedule": { "active": true, "frequency": "daily", "time": "09:00" } }
  }
}
```

- `id` — unique within the workflow.
- `type` — always `"wfNode"`.
- `position` — pixel coords.
- `data.typeId` — references a registered node type.
- `data.config` — type-specific payload; the schema lives in the type entry in `frontend/.../nodeTypes.js`.

Edges connect nodes:

```json
{ "id": "e1", "source": "n_abc123", "target": "n_xyz789", "type": "default" }
```

Edges leaving a **branch node** must set `sourceHandle` to pick which output they hang off. The handle ids are fixed per node type — use these exact strings (NOT `"yes"`/`"no"`):

| Node | Handle id | Meaning |
|---|---|---|
| `condition` | `a` | the **Yes / true** branch |
| `condition` | `b` | the **No / false** branch |
| `loop` | `a` | runs **once per item** (loop body) |
| `loop` | `b` | runs **once after** the loop finishes (Done) |
| `while` | `cond` | the **Test** node — re-run every iteration; the loop continues while its result is truthy |
| `while` | `a` | the loop body (**While**) — runs each iteration while the test holds |
| `while` | `b` | runs **once after** the loop finishes (Done) |
| `rule-group` | `r0`, `r1`, … | the matching rule branch (index = rule order) |
| `rule-group` | `else` | no rule matched |
| `judgment` | `a` | the **Confident** branch (verdict sound) |
| `judgment` | `b` | the **Doubtful** branch (verdict uncertain) |
| `business-entity` | `data:<op>` | the data produced by operation `<op>` (e.g. `data:list`, `data:read`, `data:create`, `data:update`) |
| `business-entity` | `status:<value>` | a lifecycle-status branch (e.g. `status:released`) — see caveat below |
| `kpi` / `fileshare` | `data:<op>` | same op-handle model as `business-entity` — one output per operation |

A plain (non-branch) action node has a single implicit output; its outgoing edges need no `sourceHandle`.

### Selecting the operation on a resource node (`targetHandle`) — REQUIRED

A `business-entity`, `xentral-api`, `kpi` or `fileshare` node can expose several operations (e.g. `list`, `read`, `create`, `update`, `delete`). The executor does **not** guess which one to run from the node's `operations` list — it reads the **incoming** edge's `targetHandle`, which must be `in:<op>`. So the edge that *feeds* a resource node carries `targetHandle: "in:list"` (or `in:read`, `in:create`, `in:update`, `in:delete`; for fileshare `in:read`/`in:create`/`in:update`/`in:delete`).

```json
{ "id": "e1", "source": "n_trig", "target": "n_query", "targetHandle": "in:list" }
```

**If you omit `targetHandle: "in:<op>"`, the node is skipped at runtime** (`skip("No operation selected …")`) and its variable resolves to `None` — every downstream node that reads it then fails. This is the single most common reason a workflow "does nothing". Always wire into the operation.

> **Caveat — `status:<value>` does not gate yet.** The executor follows **every** outgoing edge of a business-entity node regardless of handle, so a `status:released` edge runs unconditionally just like a `data:` edge. If you need real branching on a status value, do NOT rely on `status:<value>`; instead read the entity and put a `condition` node after it (`expression` testing the status field). Treat `status:<value>` as a visual grouping only.

## Node titles — write them for a business reader

`config.title` is what a non-technical reader (a CEO skimming the library, a designer-user opening the canvas, the step list in the workflow panel) sees as the step's name. Titles are MANDATORY on every node and must read as business steps, not as variable names or API shorthand:

- **Actions**: verb + object — "Load all products from Xentral", "Save the calculated price on the product". Never "Products", "Write", or an endpoint name.
- **Conditions**: a full question the reader can answer — "Is the product a bill of materials?". Never a bare expression like "Has parts?" referencing a variable.
- **Loops**: "For each <item> …", optionally with the purpose — "For each component: add up the cost".
- **Triggers / outputs**: say what starts the run / what is handed back — "Start — optionally with a product ID", "Return the calculated total to the caller".
- Never use identifier-style titles (`pid`, `ekObjekt`, `leafEk`) — those belong in `varName` (below). The whole graph must tell its story through the titles alone.

## Referencing data between nodes

Every node that produces a value is exposed under a **variable name** — the camelCase of its `config.varName` if set, otherwise of its `config.title`, otherwise of its type label, deduped in graph order (`businessEntity`, `businessEntity2`, …). **Always set a short `config.varName`** (e.g. `openOrders`, `pid`) on every node you reference — then the long business title can change (or be localized) without breaking a single `{{ }}` reference, and reference it by that name, never by the node `id`.

There are **three** reference forms — and they are NOT interchangeable. Using the wrong one is a silent failure (the value renders as a literal string or `None`). Pick by where you are writing:

1. **Template fields** (`loop.items`, `loop.rollupValue`, `worklist.seed`/`enqueueFrom`/`rollupValue`, `expression.expression`, `transform.source`, `call-workflow.input`/`cacheKey`, `state.*.value`, `agent.prompt`, `http-request.url`/`body`/`headers`, `output.value`): use a `{{ name.path }}` hole, where `name` is the node's **variable name** (from `varName`, see above).
   - **Reserved namespaces:** `{{ state.<key>.<path> }}` reads the run-wide `state` dict (written by the `state` node); `{{ trigger.<key> }}` reads the run's input (for a `call-workflow` child, the passed `input` map; otherwise the trigger payload). Neither collides with node variable names.
   - `{{ openOrders }}` → the whole result of the node with `varName: "openOrders"`.
   - `{{ openOrders.data }}` → walk into the result; a Xentral list returns its rows under `data`, so a loop iterates `{{ openOrders.data }}`.
   - `{{ openOrders.data.0.id }}` → dot/index walk to one field.
   - `loop.items` **must** be a *pure* hole (`{{ openOrders.data }}`), not mixed text — it has to resolve to a real list.
   - `expression.expression` and `loop.rollupValue` mix `{{ }}` holes with math operators: `{{ Line.qty }} * {{ Line.price }}`. Unlike `condition` (raw Python, attribute access on objects), the `{{ }}` holes here walk the path safely into the JSON dicts — this is the **preferred**, non-technical-readable way to read a field.
   - These are the ONLY fields that understand `{{ }}`. `{{ }}` does **not** work anywhere else.

2. **`condition.expression` and `rule-group` rules** are evaluated as raw **Python**, NOT templated. Reference upstream nodes by their variable name as a plain Python local (each box's result is assigned to that name; an un-run box is `None`). Inside a loop body the loop's own variable name is the **current item**. Example: a loop with `varName: "order"` (titled "For each open order") exposes `order`, so a following condition uses `expression: "order.get('status') != 'cancelled'"`.

3. **Resource-node param values** (`business-entity` / `xentral-api` `params.<op>.{path,query,body}`): these do **NOT** understand `{{ }}`. A plain value is a literal; to inject an upstream value use a **binding object**:
   ```jsonc
   { "mode": "ref", "from": "<node id>", "path": "id" }   // reads context[<node id>].id
   ```
   `from` is the producing node's **`id`** (not its variable name). To use the **current loop item**, point `from` at the **loop node's id** — the executor stores the current item in `context[<loop node id>]`. Literal values are written plainly (`"status": "cancelled"`, `"isBom": true`). Example — cancel the current loop order:
   ```jsonc
   "params": { "update": {
     "path": { "uuid": { "mode": "ref", "from": "n_loop", "path": "id" } },
     "body": { "status": "cancelled" }
   } }
   ```
   For **relative dates** (the most common filter case) there is a third binding: `{ "mode": "date", "expr": "today(-7)" }` — `expr` is a **date-helper call** resolved at run time (see the "Date helpers" section). Example — invoices older than 7 days / from last month:
   ```jsonc
   "params": { "list": { "query": {
     "createdAt[lt]": { "mode": "date", "expr": "today(-7)" },
     "invoiceDate":   { "mode": "date", "expr": "last('month')" }
   } } }
   ```

## Available node types

> **Pick a node first. Code is allowed for genuine program logic, but not for hidden modelling.** Build fixed data access, ERP actions and simple flow decisions from first-class palette nodes. A `code` box is right for genuinely code-shaped residual logic: complex calculations, data reshaping, aggregation, dynamic traversal, or glue code over data that is already visible upstream. A workflow that hides fixed ERP steps or business decisions in Code is still a script in disguise.
>
> Try in this order and stop at the first that fits:
> 1. **A data / ERP node** — `business-entity` (`list`/`read`/`create`/`update`/`delete`, incl. query filters), `fileshare` (tenant working files — an op-handle node like `business-entity`: operations `read`/`create`/`update`/`delete`, the op chosen by the incoming `in:<op>` edge, params under `config.params[op]`. `read`/`delete` take `path.file_key`; `create` takes `body.filename` + `body.content_b64` (binary) or `body.content` (UTF-8); `update` takes `path.file_key` + the same body. Content is usually bound from an upstream read node's `data:read.content_b64`), `xentral-action`, `integration-action`, `kpi`, `report`. If something feels like "nested data" (a product's parts, its prices, an order's positions), it is almost always its **own entity** — check with the entity reference search **before** writing `business_entity_op(...)` in code. If it's an entity, it's a `business-entity` node.
> 2. **A flow / logic node** — `loop`, `worklist` (trees / unknown depth), `while`, `condition`, `expression` (compute one value), `transform` (reshape fields), `state` (run-wide variables), `call-workflow` (recursion). These replace the classic reasons people reach for code: iterating, branching, computing, reshaping, accumulating, recursing.
> 3. **Only now** a `code` node — for residual logic that is truly code. Prefer clear, ordinary code over clever compression.
>
> Before adding any `code` box, be able to name which node in steps 1–2 you ruled out and why. "It was quicker to write code" is not a reason.
>
> **Documentation requirement for every `code` box:** Write `config.description` for a CEO or business owner, not for a developer. Start with the business purpose: what data comes in, what decision or reshaping happens, and what result the next step receives. Avoid API terms, Python terms and raw field names in prose; when a field matters, name the business meaning first and put the technical field in parentheses only when useful. For non-trivial logic, set `config.algorithm` with 3-6 business steps or a small ASCII sketch: no implementation details, but "read orders -> check the delivery traffic light for each order -> output a compact assessment". Comment the Python code itself **in English** at the important business blocks: loops, branches, aggregations, reshaping and side effects. Comments should explain why the block exists, not restate every assignment.
>
> **Understandability boundary:** If the residual logic is technically possible but only as an opaque Code box, do NOT author it as clever compressed Python. Stop and name exactly what is missing instead: e.g. "I need a Business Entity field for X", "I need action Y", "I need a transform/filter node for Z", "I need a tested runtime probe", "I need a business rule from the user". The right output is then a clear gap list, not an unreadable code box.

**Triggers:**
- `trigger-manual` — click / API call.
- `trigger-schedule` — cron plan. Config: `{ schedule: { active, frequency, time, weekdays?, monthday? } }`. **`active: true` is required for the plan to actually fire** — it mirrors the inspector's "Add to schedule" toggle. Workflow-level `enabled: true` is NOT enough: only with `schedule.active: true` does the backend (`reconcile_schedules`) register a real `xentral_workflows` schedule row in the schedule-service. Without `active` the node is configured but dormant (the intended default for a freshly dropped Schedule node). Always set `"active": true` when authoring a plan that should run automatically.
- `trigger-webhook` — HTTP endpoint. Config: `{ path, method }`.
- `trigger-erp-event` — Xentral event. Config: `{ event }`, e.g. `"sales_order.created"`.
- `trigger-integration-event` — event from a connected integration (e.g. Gmail "new email"). Config: `{ connectorId, triggerSlug, connectionId, triggerConfig }`. The subscription is registered/removed via `PUT .../workflows/{id}/integration-trigger` (the editor's inspector does this), not by saving the node. One workflow per (trigger, connection) — a second activation is refused; use a second connection of the same account for parallel workflows. Event data is read downstream as `{{ trigger.data.<field> }}`.

**Actions:**
- `business-entity` — run an operation against one Xentral business entity. Operations: `list/read/create/update/delete` (there is no separate `search` — searching is `list` with query filters), plus every action/process step declared by the entity, e.g. `Printer.printDocument`. Config:
  ```jsonc
  {
    "title": "Load open sales orders", // business label on canvas + overview — mandatory
    "varName": "openOrders",         // the {{ }} reference name — set it on every referenced node
    "entityKey": "SalesOrder",       // the Xentral entity key
    "entityLabel": "Sales order",    // optional, log label only
    "operations": ["list"],          // which ops this node performs
    "params": {                      // params are keyed PER operation
      "list":   { "query": { "paymentMethod": "prepayment", "status": "open" } },
      "read":   { "path": { "uuid": { "mode": "ref", "from": "n_query", "path": "data.0.id" } } },
      "update": { "path": { "uuid": { "mode": "ref", "from": "n_loop", "path": "id" } }, "body": { "status": "cancelled" } },
      "delete": { "path": { "uuid": { "mode": "ref", "from": "n_loop", "path": "id" } } }
    }
  }
  ```
  Param sections per op: `list` → `query` (filters); `read`/`update`/`delete` → `path.uuid`; `create`/`update` → `body`. Each operation produces a `data:<op>` output handle.
  **List only the operations this node actually performs** in `operations` — usually exactly one. Every entry renders its own row/handle on the card, so a node that only searches is `operations: ["list"]`, NOT all five. Listing unused ops makes the card taller (a search step shows a misleading "Anlegen/Aktualisieren" and throws off your branch spacing) and reads as if the node writes when it only reads.
  Entity actions/commands use the same shape: `params.<action>.path.uuid` is the affected entity id, and `params.<action>.body` is the command payload. The renderer calls `PATCH /api/entity/<Entity>/actions/<action>` with `{ ids: [uuid], command: body }`.
  **Named printer / printing:** Use the existing emulated `Printer` business entity. Flow: `fileshare` `read` (params `read.path.file_key`, fed via `in:read`) for the PDF/file to print -> `business-entity` `Printer` operation `list` with query filters `{ "filter[0][key]": "name", "filter[0][op]": "equals", "filter[0][value]": "<printer name>" }` -> optional `condition`/`expression` for exactly one match -> `business-entity` `Printer` action `printDocument` with `path.uuid` from the found printer and `body.fileContent` bound from the fileshare node's `content_b64`, plus `body.fileName`/`body.quantity`. Do not use `xentral_actions`, and do not hide fileshare reading, printer listing, name matching, or printing inside a `code` node.
- `fileshare` — read or write tenant working files (Datenaustausch: uploaded CSVs, generated PDFs/exports, files to print). **Op-handle node like `business-entity`** — operations `read`/`create`/`update`/`delete`, the op chosen by the incoming `in:<op>` edge, each producing a `data:<op>` output. Config: `{ operations: [...], params: { <op>: { path?, body? } } }`. Per op:
  - `read` / `delete` → `params.<op>.path.file_key` (the file's id; bind it from an upstream list/read, or hard-link a known key).
  - `create` → `params.create.body` with `filename` + `content_b64` (binary) **or** `content` (UTF-8 text); optional `mime_type`.
  - `update` → `params.update.path.file_key` + the same `body` (replaces the file's content in place).
  `read` returns the file inline (`content`/`content_b64`), so a downstream node consumes it directly — e.g. bind a `create`'s `body.content_b64` from an upstream read's `data:read.content_b64`, or feed `Printer.printDocument` (see the printer flow above). Note: the path key is `file_key`, **not** `uuid`.
- `xentral-api` — call a raw Xentral OpenAPI endpoint when **no `business-entity` covers** what you need. Config: `{ title?, operations: [{ id, method, path, label? }], params: { <id>: { path, query, body } } }`. Like business-entity, each operation has its own output handle.
- `agent` — custom LLM step mid-flow. Config: `{ title?, model, prompt, structuredOutput?, maxSteps }`. `prompt` is a template field. The agent only receives data from previous nodes via `{{ }}` and returns text/structured text; it has no tools and cannot call ERP actions. Use separate resource/action/human-task nodes before or after the agent for reads, writes, sends or mutations.
- `kpi` — read or update one existing KPI. Config: `{ kpiKey, operations[] }` — operations are bounded by the KPI's value source (live → read; cached → read/history/refresh; push → read/history/write). One output port per operation.
- `report` — run one existing Xentral analytics report. Config: `{ reportId, params }`. Single output carrying the normalized `{ columns, rows, rowCount }` result.
- `human-task` — hand off to a human; endpoint node (no output). Config: `{ mode: 'task'|'job'|'email', … }` — `task` = operational action item, `job` = agent job, `email` = Xentral correspondence email. Free-text fields support `{{ ref }}`.
- `code` — inline Python snippet. Config: `{ title?, description, algorithm?, code }`. For data transforms and genuine program logic; upstream boxes are available as Python locals (their variable names). `description` is required, and `algorithm` is required once the logic contains loops/branches/aggregation. The Xentral helpers `business_entity_op(entity_key, op, params)`, `xentral_op(method, path, params)` and `xentral_request(...)` are in scope too — use them for **data-dependent** fetches inside the code (see "Fetching data vs. computing"). **Runs in a sandbox — only a safe subset of Python is allowed; see "Code node — what's allowed" before writing one** (notably: no `lambda`, no `import`).
- `condition` — branch. Config: `{ expression }`, a **Python** boolean over upstream variable names (NOT `{{ }}`). Outputs `a` (true) / `b` (false).
- `judgment` (palette "Agents & people" → **Judgment** / Prüf-Instanz) — a verdict gate for the unreliable steps (agents + people): it inspects what ran so far and branches on whether the result is sound. Config: `{ intent, watch?, rules?, threshold? }`. `intent` is the question to judge (plain text); `watch` is free-text with `{{ ref }}` holes pointing at the upstream outputs to inspect (interpolated into the judge's prompt like an `agent` prompt); `rules` is an optional list of `{ label, expression }` hard checks — each `expression` is **raw Python** (same rules/scope as `condition`) and any failure forces the verdict to **doubtful** without an LLM call, with `label` shown as the reason; `threshold` ∈ `low | medium | high` sets how strict the LLM verdict is. Outputs `a` (**Confident**) / `b` (**Doubtful**). It **is** a var source: it publishes `{ status, confidence, reasons, checkedAt }` under its variable name, so the doubtful branch can surface `{{ <varName>.reasons }}` in a human task / mail / note. (Phase 1: stateless per run — no learning from feedback yet.)
- `loop` — for-each over a list. Config: `{ title?, items, rollupOp?, rollupValue? }` where `items` is a pure `{{ ref }}` resolving to a list. Body runs via handle `a`, Done via `b`; inside the body the loop's variable name is the current item. **Optional roll-up (`rollupOp`):** `sum` / `count` / `min` / `max` / `collect` (list) / `concat` (text) — folds the passes into **one** value. `rollupValue` is the small per-item calculation (`{{ <loopVarName>.field }} * …`, empty for `count`). When `rollupOp` is set, the loop's **result** is that rolled-up value (instead of the list) — so `{{ <loopVarName> }}` in the Done branch yields e.g. the sum. This means a flat `Σ(field)` over a known list needs **no** code box.
- `worklist` (palette "Flow & logic" → **Work through a pile**) — a **queue-driven loop for trees/graphs of unknown depth** (BOM explosion, category trees, corporate hierarchies, paging). Same two outputs as `loop` (`a` body, `b` done). Config: `{ title?, seed, enqueueFrom?, dedupeKey?, rollupOp?, rollupValue? }`. `seed` (pure `{{ ref }}`) is the starting list; inside the body the current item is the variable name. `enqueueFrom` (pure `{{ ref }}`, evaluated **per item after the body**) yields a list that is **appended to the queue** — point it at a body node's output (e.g. the sub-parts just read) or a field of the current item (`{{ Pile.children }}`); empty = no follow-ups (behaves like a `loop`). `dedupeKey` (default `id`) makes each item run **once** and **cycles safe**. **Hard-capped at 1000 items** (logs `"Worklist capped at 1000 items."`, no error — page/split for bigger trees). Optional roll-up as on `loop` (`rollupOp`/`rollupValue`) folds the processed items into one value (e.g. Σ cost over the whole tree). Result: the roll-up value, else the list of **all** processed items. **Prefer `worklist` over `while`+`context`-queue code** whenever the intent is "… and everything below / at all levels / fully explode" — it keeps the queue/cycle/dedupe mechanics out of code.
- `expression` (palette "Flow & logic" → **Compute value**) — a single calculation or check, replacing trivial "just compute something" code boxes. Config: `{ expression }`. Unlike `condition`, it uses **`{{ name.field }}` holes** mixed with operators (`{{ price }} * {{ amount }}`, `{{ order.total }} > 1000`) — the holes walk safely into the JSON dicts. Linear (`in`→`out`); the result is available under the node's variable name.
- `transform` (palette "Flow & logic" → **Reshape fields**) — pulls named fields out of a list/object and renames them, replacing trivial "just reshape" code boxes. Config: `{ source, mappings: [{ from, to }] }`. `source` is a pure `{{ ref }}`; each row maps a dot-path `from` (in the source) to a new name `to`. For a list each item is reshaped, otherwise the object. **No** Python — paths are walked as data.
- `call-workflow` (palette "Flow & logic" → **Call workflow**) — calls a workflow **synchronously**, currently only **itself** (`workflowId: "self"`) → **recursion** for trees/graphs (BOM cost, category/org trees). Config: `{ title?, workflowId, input, cacheKey?, maxDepth?, onError? }`. `input` is a map → becomes the child run's **trigger payload** (read there as `{{ trigger.<key> }}`). The **return value** is the `output` node that ran in the child; available as `{{ <varName> }}`. **`cacheKey`** (strongly recommended) memoises per key for the whole root run — a sub-assembly used in several BOMs is computed **once**. **`maxDepth`** (default 50) is a mandatory guard: on reaching it the **recursion stops** and logs the call chain (no infinite run on cyclic BOMs). Each call gets its **own fresh `context`/`state`** (isolation, side-effect-free). Two outputs: `a` (Next) and `b` (Error, when `onError:"route"`). Other `workflowId`s follow later. **This means a BOM roll-up no longer needs `while`+stack+memo code.**
- `state` (palette "Flow & logic" → **State**) — read/write **run-wide named variables** (working stack, accumulator, memo) without a code box. Config: `{ operations: [{ op, key, value?/by? }] }` with `op` ∈ `set | append | inc | pop | remove | merge | delete` (in order). Read anywhere via `{{ state.<key> }}` **or** raw `state['key']` inside `condition`/`expression`. `state` is **per-run-scope** (not inherited by `call-workflow` children). Linear node, no result. **`while` without code:** wire a `condition` node (whose `expression` checks `state.*`, e.g. `state['stack'] != []`) to the `while`'s `cond` output — `condition` now publishes its boolean into `context`, so it works as the test.
- `while` — repeat while a test holds. Use it when the iteration count or nesting depth is **not known up-front** (recursion, paging, "keep going until done") — that's the case `loop` can't express. Config: `{ title?, expression? }`. The loop test is **wired**: connect a `code` / `business-entity` node to the `cond` (Test) output and the loop continues while that node's result is truthy; the Test node re-runs every iteration. The `expression` field (raw Python, like `condition`) is only a fallback used when nothing is wired to `cond`; an empty/absent expression evaluates to `False` (zero iterations) so a half-built node never spins forever. Body runs via handle `a`, Done via `b`. **Iterations are hard-capped at 1000**: on the 1000th pass the loop breaks and logs `"While loop capped at 1000 iterations."` — it does **not** raise, so a run that needs more iterations finishes *silently incomplete*. So before you reach for `while`, know your worst-case iteration count: if it can exceed 1000 (e.g. more than 1000 rows, deeper recursion, long paging), don't rely on the cap — page/chunk the work, raise the limit deliberately, or split the workflow. To carry state between iterations, mutate `context` inside the body/test (e.g. `context['queue']`) — both run in the same `main()` scope.
- `delay` — pause. Config: `{ duration, unit }`.
- `http-request` — REST call. Config: `{ method, url, headers, body }`.
- `web-search` — web search. Config: `{ query }`.

- `xentral-action` (palette group "ERP actions") — the generic `xentral_actions` node. Pick ONE action from the live catalog (`GET /instances/{lid}/xentral-actions`, grouped by category: sales, shipping, warehouse, documents, communication, …) and fill its params (rendered from the action's `input_schema`; values are template fields, `{{ ref }}` supported). Config: `{ action, params, inputSchema?, preconditions? }`. Execution RPCs into `POST /instances/{lid}/xentral-actions/{action}` — the SAME registry (`thirdpartytools/xentral` `XentralMCPService`) that agents, MCP and Studio use. New actions (e.g. `print_shipping_label`, `email_send`, `print_document`, `stock_put_away`, `stock_retrieve`) appear here automatically without touching the node. Batch by feeding a `loop` into it.
- `integration-action` (palette group "Integrations") — run ONE action of a connected external integration (Gmail, Slack, …) via the provider-neutral registry. Pick from the live catalog (`GET /instances/{lid}/integration-actions`, grouped by `tool_id`; only connected integrations appear) and fill its params (template fields, `{{ ref }}` supported). Config: `{ tool_id, action, actionLabel, connection_id, connectionLabel, paramDefs, params }`. The inspector auto-pins a connection into `connection_id`; the pin matters: unattended runs (schedule, webhook, integration event) execute with a service identity that owns no connections, so only a pinned connection — any connection of the tenant — resolves there. Execution RPCs into `POST /instances/{lid}/integration-actions/{tool_id}/{action}`.
  - **Unconnected integrations:** the live catalog lists only *connected* tools, but absence from it is **not** a veto. If the user explicitly names a SaaS tool that isn't connected yet (e.g. "send a Slack message"), still author the node — set your best-guess `tool_id`/`action` slug, leave `connection_id` empty (unpinned), and fill `params` with placeholders. Mark it **provisional**: the action slug and `paramDefs` can only be *verified* against the live catalog once the integration is connected, so don't present a guessed slug as confirmed — tell the user the node needs the integration connected and a connection pinned in the inspector before the workflow runs. Connecting is a separate, later step; never block building the workflow shape on it. (Same principle as the rest of the write path: don't refuse what the designer UI would let a human do.)

