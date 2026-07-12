---
name: xentral-workflows
description: >
  Build, edit, and debug node-based Xentral workflow automations with the
  xentral_workflows tool. Covers when to use a workflow vs a custom agent,
  starting from the template library (init_from_template) instead of a blank
  graph, the workflow envelope/graph shape, trigger and schedule setup, node
  operation selection, stable varName references, and debugging failed runs.
  Use when the user wants to automate a recurring business routine — dunning /
  OPOS escalation, low-stock reorder, document validation, prepayment-order
  cleanup, return-to-credit-note, BOM cost rollup, invoice-after-shipment.
examples:
  - "Build a workflow that cancels prepayment orders unpaid after 7 days."
  - "Set up a multi-stage dunning escalation for overdue invoices."
  - "Turn every return into a credit note automatically."
---

# Workflows

## Purpose

The workflow store keeps **node-based automations** per instance. A workflow is a directed graph: a **trigger** fires, then **action nodes** run in the order defined by the edges.

Workflows sit one layer below custom agents:

- **Custom agent** = LLM with instructions + tool access, decides at runtime what to do.
- **Workflow** = explicit step list, deterministic, idempotent, ideal for routine operations (dunning, stock checks, document validation).

If the decision is **always the same** → workflow. If the step **depends on the input** (mail classification, request routing) → agent.

## When to call

* Operator describes a recurring routine ("every day at 09:00 cancel all prepayment orders older than 7 days that have no payment") → `init` a workflow.
* Operator asks "what workflows do I have?" → `list`.
* Workflow needs change (new step, different cron) → `update`.

**Don't** call:
* For one-off operations (Excel import, manual cleanup) — workflows are for recurring work.
* When the decision logic needs LLM reasoning — then a custom agent (`xentral_agents`) is the right tool.

## Start from the library, not a blank canvas

Before building from scratch, check the shipped templates: call **`list_library`** to see the ready ERP-classic workflows (prepayment cleanup, dunning escalation, low-stock reorder, return→credit-note, BOM cost rollup, …) and **`init_from_template`** to clone one into the instance, then adapt it. Each template is already wired to the contract described below — correct `targetHandle` operation selection, stable `varName` references, binding objects for resource params — so cloning and tweaking is faster and less error-prone than hand-assembling a graph. The worked examples further down in this guide mirror those library templates. Hand-build only when no template is close.

## Construction recipe

When the operator asks for a workflow:

1. **Clarify the trigger.** Cron? Event? Manual? → set `trigger_type`.
2. **Clarify the source.** Which Xentral entity supplies the input list? → business-entity node with operation `list` and `params.list.query` filters. The source can also be an **external integration** (a shop/marketplace like Shopify) — an `integration-action` list action or an integration event; see "Integration sync" below.
3. **Clarify processing.** Per-item decide vs treat all the same? Loop + condition or direct action node?
4. **Run the action.** Update / Delete / Send Mail / CRM entry?
5. **Wire the edges.** Trigger → source → optionally loop → condition → action(s).
6. **Save.** `init` with the assembled `{nodes, edges}` graph.

Node positions: always lay them out **horizontally, left → right** — keep `y` constant (e.g. `y = 80`) and step `x` by ~400 per node (cards are ~320px wide); a branch offsets its two lines by `y` ±200 for the Yes/No paths. Set `"orientation": "horizontal"` to match. **Never build vertical** — it is only a manual toggle the user can flip in the editor, not something an agent emits. The user can still rearrange, but the saved plan must render without overlaps, so over-space rather than risk cards overlapping the next node.

## Integration sync (external connectors — Shopify, Amazon, and any other)

Workflows are **not** only for internal ERP data — they can pull from and push to **any** connected external integration via the `integration-action` node. This is generic: it is not a Shopify feature. **Discover what's there first** — read the live catalog (`GET /instances/{lid}/integration-actions`, grouped by `tool_id`) to see which integrations and actions exist; if the task names a specific connector (Shopify, Amazon, …), build the sync for it. Building the sync as a workflow is a first-class, expected task: when the operator (or the prompt) asks to import orders, sync stock, or report shipment status back to a shop/marketplace, **build the workflows** — do not reflexively defer it to "the native connector does that." (Defer only if the out-of-the-box connector already does exactly what's asked and no custom mapping/steps are needed.)

The three flows to build for a shop/marketplace connector, one workflow each (Shopify action slugs shown as the concrete example; other connectors expose the equivalent actions in the same catalog):

- **Order import** — trigger `trigger-integration-event` ("order created") or `trigger-schedule` (poll); `integration-action` `SHOPIFY_GET_ORDERS_WITH_FILTERS` (list) → `loop` → create the ERP `SalesOrder` (business-entity `create`), mapping the shop-order fields. (`SHOPIFY_GET_ORDER` for a single order by id.)
- **Stock export back to the shop** — trigger on a stock change or a schedule; per SKU, `integration-action` `SHOPIFY_ADJUST_INVENTORY_LEVEL` (use `SHOPIFY_GET_INVENTORY_LEVELS` to reconcile first).
- **Fulfillment / tracking feedback** — trigger after shipment (ERP event "delivery note shipped"); `integration-action` `SHOPIFY_CREATE_FULFILLMENT` with the tracking number, so the shop marks the order shipped.

**Discovery & provisional nodes.** The `integration-action` catalog (`GET /instances/{lid}/integration-actions`) lists only *connected* integrations, so on an instance without Shopify connected it comes back empty. That is **not** a reason to skip the workflow: author the `integration-action` nodes anyway with the action slugs above, leave `connection_id` empty (unpinned), and mark them **provisional** — tell the user the integration must be connected and a connection pinned in the inspector before the workflow runs. Never block building the workflow shape on connection state (same rule as the rest of the write path — build what the designer UI would let a human build).

## MCP agent loop: build, check, learn

When you author a workflow through MCP, use this loop:

1. **Discover before building.** Read this guide (`help`). Check library templates (`list_library`). For ERP data, use Business Entity / API discovery before assuming entity names, fields, actions or process steps. If a real entity/action exists, model it visibly as a node.
2. **Build the smallest visible version.** Every fixed data access, fixed action and business decision belongs on the canvas. Agent and Code nodes are only for language work or short glue logic.
3. **Always run `check` after `init`/`update`.** Treat `error` as not done. Review warnings deliberately; for reachable writes, recommend or run `xentral_workflow_debug.run_workflow(dry_run=true)` when that is part of the task.
4. **Fix check failures directly.** Change handles, operations, nodes, prompts or data sources. Then run `check` again. Do not compensate by making code boxes bigger.
5. **When stuck, separate local from generic.** Local/instance-specific means e.g. "this instance has no tag named X", "this instance has no data", "no mail account is configured" — that is not product feedback. Generic means e.g. "Business Entity X lacks a central business field", "an existing ERP action is not modeled as an entity action", "a standard transform/filter/aggregation node is missing", "the check cannot detect a whole class of bad workflows yet".
6. **Report generic gaps.** If the gap would likely help many workflows/instances and you cannot build the workflow cleanly without it, record it via `xentral_feedback` (category `feature_request` or `bug`, `request_report=true`). Keep it short: desired workflow, missing general building block, why visible nodes would become possible. Do not include customer data or full document/email contents.
7. **Tell the user honestly where it stands.** If a generic gap prevents a clean workflow, do not ship a disguised script workflow. Say: "This could be built cleanly if X existed; I reported Y as feedback." If a provisional workaround exists, label it clearly as provisional.

Feedback is not a substitute for fixing the graph: report only general platform gaps, not every check finding and not one-off issues that correct wiring would solve.

## Workflow vs custom agent

| Question | Workflow | Custom agent |
|---|---|---|
| Decides path at runtime? | Only via `condition` with a clear expression | Yes, LLM decides each run |
| Repeatable identically? | Yes | Roughly, but LLM drift |
| Audit trail clear? | Yes (the graph is the spec) | Only via prompt + logs |
| Editable by non-techies? | Limited — positions static | Yes (instructions = text) |

Build a workflow when you could explain "step 1, then step 2, then …". Build an agent when the right answer depends on the content of an incoming request.

## Detailed references — read on demand

Load only the file you need for the step you are on:

- **Graph & node contract** — envelope, triggers, node shape, titles, data references, the node-type catalog:
  [reference/graph-and-nodes.md](reference/graph-and-nodes.md)
- **Code nodes, date helpers, tool actions, fetch-vs-compute**:
  [reference/code-and-data.md](reference/code-and-data.md)
- **Worked examples, idempotency, debugging a run**:
  [reference/examples-and-debugging.md](reference/examples-and-debugging.md)
