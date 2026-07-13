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

## Integrations in workflows (external connectors)

Workflows are **not** only for internal ERP data. The instance connects to external integrations (CRMs, shops, marketplaces, mail, messaging — e.g. HubSpot, Google, a shop system, Slack, …), and **any** of their actions can run inside a workflow via the `integration-action` node. Treat this as a first-class capability: when the operator or the prompt asks to sync with an external tool, build the workflow — don't defer it to "the native connector does that" (defer only if an out-of-the-box connector already does exactly what's asked).

**Discover what's available** at build time — the live catalog `GET /instances/{lid}/integration-actions` (grouped by `tool_id`) lists the connected integrations and their actions. Pick the `tool_id` + action the task names.

Sync shapes (vendor-neutral — the same for any connector):

- **Inbound (import / react to the external tool):** trigger `trigger-integration-event` (the tool fires an event) or `trigger-schedule` + an `integration-action` *list* action; then `loop` → create/update the matching ERP entity.
- **Outbound (push to the external tool):** an `integration-action` write action (update a record, adjust stock, create a fulfillment, send a message) after the ERP step that produced the change.

**Not connected yet?** The workflow catalog (`GET …/integration-actions`) lists only *connected* integrations, so it can come back empty — but that is **not** a reason to skip, and **not** a licence to guess the slug. The curated integration catalog still carries the toolkit's real actions: call `xentral_integrations` `list_actions` (`template_id=<tool_id>`) to get the **real** `action` slug + params even before the tool is connected, and author the node with those. Invent a best-guess slug only if the curated catalog has nothing for that tool. Either way leave `connection_id` empty (unpinned), mark it **provisional**, and tell the user the integration must be connected and a connection pinned before the run. Never block building the shape on connection state.

**Which** integration and **which** records to sync is a per-task decision — it comes from the operator's request or the prompt, not from this guide.

**Always leave a go-live activation task.** A provisional `integration-action` node, and *every* `shiplabel` node, will not run until the user supplies credentials — and **where** they do that differs by node type. So whenever a build includes an `integration-action` or a `shiplabel` node, ALWAYS finish by leaving the user a short, plain-language task (create a **Decision** via `xentral_decisions`, and repeat it in your closing summary) that names the go-live step **per node**:
- **`integration-action`** → "To go live, connect **<tool>** under **Integrationen / Integrations** (`/app/integrations`): open the card, click **Verbinden / Connect** and enter the credentials." That hub is the only place external integrations are connected.
- **`shiplabel`** → "To go live, open the workflow **<workflow name>**, click the **<carrier>** Paketmarke/Shipping-label node, and enter the carrier access data in its form." Carrier credentials live on the node itself (a deployment may instead set `SHIPLABEL_*` env).

Adapt the wording to the actual tool / carrier, and list one step per unconnected node. **Never connect anything yourself** — the user does it; your job is to tell them exactly where. This is not optional: a workflow that silently needs credentials it never asked for reads as broken.

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
