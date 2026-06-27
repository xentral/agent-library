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
---

# Workflows

## Purpose

The workflow store keeps **node-based automations** per tenant. A workflow is a directed graph: a **trigger** fires, then **action nodes** run in the order defined by the edges.

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

Before building from scratch, check the shipped templates: call **`list_library`** to see the ready ERP-classic workflows (prepayment cleanup, dunning escalation, low-stock reorder, return→credit-note, BOM cost rollup, …) and **`init_from_template`** to clone one into the tenant, then adapt it. Each template is already wired to the contract described below — correct `targetHandle` operation selection, stable `varName` references, binding objects for resource params — so cloning and tweaking is faster and less error-prone than hand-assembling a graph. The worked examples further down in this guide mirror those library templates. Hand-build only when no template is close.

## Construction recipe

When the operator asks for a workflow:

1. **Clarify the trigger.** Cron? Event? Manual? → set `trigger_type`.
2. **Clarify the source.** Which Xentral entity supplies the input list? → business-entity node with operation `list` and `params.list.query` filters.
3. **Clarify processing.** Per-item decide vs treat all the same? Loop + condition or direct action node?
4. **Run the action.** Update / Delete / Send Mail / CRM entry?
5. **Wire the edges.** Trigger → source → optionally loop → condition → action(s).
6. **Save.** `init` with the assembled `{nodes, edges}` graph.

Node positions: lay them out **vertically** — `x = 80`, and step `y` by the card's height (~200 after a plain node, +40 per extra operation on a resource node, ~+70 after a branch node whose Yes/No labels hang below it; see the orientation note above). Do **not** use a flat 140 step — multi-row entity cards and branch labels would overlap the node below. The user can still rearrange, but the saved plan must render without overlaps.

## MCP agent loop: build, check, learn

When you author a workflow through MCP, use this loop:

1. **Discover before building.** Read this guide (`help`). Check library templates (`list_library`). For ERP data, use Business Entity / API discovery before assuming entity names, fields, actions or process steps. If a real entity/action exists, model it visibly as a node.
2. **Build the smallest visible version.** Every fixed data access, fixed action and business decision belongs on the canvas. Agent and Code nodes are only for language work or short glue logic.
3. **Always run `check` after `init`/`update`.** Treat `error` as not done. Review warnings deliberately; for reachable writes, recommend or run `xentral_workflow_debug.run_workflow(dry_run=true)` when that is part of the task.
4. **Fix check failures directly.** Change handles, operations, nodes, prompts or data sources. Then run `check` again. Do not compensate by making code boxes bigger.
5. **When stuck, separate local from generic.** Local/tenant-specific means e.g. "this tenant has no tag named X", "this instance has no data", "no mail account is configured" — that is not product feedback. Generic means e.g. "Business Entity X lacks a central business field", "an existing ERP action is not modeled as an entity action", "a standard transform/filter/aggregation node is missing", "the check cannot detect a whole class of bad workflows yet".
6. **Report generic gaps.** If the gap would likely help many workflows/tenants and you cannot build the workflow cleanly without it, record it via `xentral_feedback` (category `feature_request` or `bug`, `request_report=true`). Keep it short: desired workflow, missing general building block, why visible nodes would become possible. Do not include customer data or full document/email contents.
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
