# Workflows — worked examples & debugging

<!-- Sourced from backend/workflows/agent_guide/en.md — keep in sync. -->

## Example skeleton — "cancel prepayment order if > 7 days unpaid"

```json
{
  "id": "prepayment_cleanup",
  "name": "Cancel prepayment orders (>7 days)",
  "description": "Cancels prepayment orders that received no payment after 7 days.",
  "trigger_type": "schedule",
  "nodes": [
    { "id": "n_trig",   "type": "wfNode", "position": { "x": 80, "y": 80 },
      "data": { "typeId": "trigger-schedule",
                "config": { "title": "Every day at 09:00",
                            "schedule": { "active": true, "frequency": "daily", "time": "09:00" } } } },
    { "id": "n_query",  "type": "wfNode", "position": { "x": 80, "y": 280 },
      "data": { "typeId": "business-entity",
                "config": { "title": "Load open prepayment orders",
                            "varName": "openPrepayments",
                            "entityKey": "SalesOrder",
                            "operations": ["list"],
                            "params": { "list": { "query": { "paymentMethod": "prepayment",
                                                              "status": "open" } } } } } },
    { "id": "n_loop",   "type": "wfNode", "position": { "x": 80, "y": 480 },
      "data": { "typeId": "loop",
                "config": { "title": "For each open prepayment order",
                            "varName": "order",
                            "items": "{{ openPrepayments.data }}" } } },
    { "id": "n_guard",  "type": "wfNode", "position": { "x": 80, "y": 680 },
      "data": { "typeId": "condition",
                "config": { "title": "Is the order still open?",
                            "expression": "order.get('status') != 'cancelled'" } } },
    { "id": "n_cancel", "type": "wfNode", "position": { "x": 80, "y": 950 },
      "data": { "typeId": "business-entity",
                "config": { "title": "Cancel the unpaid order",
                            "entityKey": "SalesOrder",
                            "operations": ["update"],
                            "params": { "update": { "path": { "uuid": { "mode": "ref", "from": "n_loop", "path": "id" } },
                                                    "body": { "status": "cancelled" } } } } } }
  ],
  "edges": [
    { "id": "e1", "source": "n_trig",  "target": "n_query",  "targetHandle": "in:list" },
    { "id": "e2", "source": "n_query", "target": "n_loop",   "sourceHandle": "data:list" },
    { "id": "e3", "source": "n_loop",  "target": "n_guard",  "sourceHandle": "a" },
    { "id": "e4", "source": "n_guard", "target": "n_cancel", "sourceHandle": "a", "targetHandle": "in:update" }
  ]
}
```

Note how every node carries a business-readable `title` while the loop and condition reference the **`varName`-pinned variable** (`openPrepayments`, `order`) via `{{ }}` holes and raw Python respectively, and the `n_cancel` param `path.uuid` uses a **binding object** (`{ "mode": "ref", "from": "n_loop", "path": "id" }`) — param values do **not** support `{{ }}`, and `from` is the loop node's **id** so it resolves to the current loop item. The edge feeding each resource node carries `targetHandle: "in:<op>"` (`in:list`, `in:update`), branch edges carry the right `sourceHandle` (`data:list`, loop `a`, condition `a`), and the redundant-update guard (`condition` testing `order` status) keeps the run idempotent.

## Example skeleton — recursive bottom-up BOM cost rollup

> **Build this node-first, not as the code below.** A BOM rollup is the textbook fit for the **`worklist`** node (queue-driven explosion of unknown depth, with built-in dedupe/cycle-safety) or **`call-workflow`** recursion (`workflowId: "self"`, with `cacheKey`/`maxDepth`) — and a product's parts and prices are their **own entities** (`PartsListItem`, `PurchasePrice`), so they're `business-entity` nodes, not `business_entity_op(...)` calls buried in code. Composed that way, the whole thing is visible on the canvas with at most a tiny `expression`/`code` box for the per-level `Σ(price × qty)`. The `while`+stack+code version below is kept only as a **last-resort illustration** for a shape no node can express — it is **not** the recommended pattern, and not what to emit when the palette already covers it.

The reason `while` was ever reached for here: a bill of materials (Stückliste) can nest BOMs inside BOMs to **arbitrary, data-dependent depth**, so a `loop` (for-each over a known list) can't express it. The algorithm is a post-order walk over a stack kept in `context`: only finalize a BOM's cost once all its sub-BOM children are costed. Leaves take their own purchase price. (With `worklist`/`call-workflow` you get the depth handling for free instead of hand-rolling the stack, the dedupe and the cycle guard in code.)

```json
{
  "id": "bom_cost_rollup",
  "name": "Nightly BOM cost rollup",
  "description": "Recomputes purchase cost for every bill of materials bottom-up.",
  "trigger_type": "schedule",
  "nodes": [
    { "id": "n_trig", "type": "wfNode", "position": { "x": 80, "y": 80 },
      "data": { "typeId": "trigger-schedule",
                "config": { "schedule": { "active": true, "frequency": "daily", "time": "02:00" } } } },
    { "id": "n_query", "type": "wfNode", "position": { "x": 80, "y": 280 },
      "data": { "typeId": "business-entity",
                "config": { "title": "Load all BOM products", "varName": "bomProducts",
                            "entityKey": "product",
                            "operations": ["list"],
                            "params": { "list": { "query": { "isBom": true } } } } } },
    { "id": "n_seed", "type": "wfNode", "position": { "x": 80, "y": 480 },
      "data": { "typeId": "code", "config": { "title": "Build the work stack", "varName": "seed", "code": "<seed code below>" } } },
    { "id": "n_while", "type": "wfNode", "position": { "x": 80, "y": 680 },
      "data": { "typeId": "while", "config": { "title": "Work through the stack, bottom-up" } } },
    { "id": "n_test", "type": "wfNode", "position": { "x": 380, "y": 680 },
      "data": { "typeId": "code", "config": { "title": "Is work remaining?", "varName": "workLeft", "code": "<test code below>" } } },
    { "id": "n_step", "type": "wfNode", "position": { "x": 80, "y": 950 },
      "data": { "typeId": "code", "config": { "title": "Cost one BOM (children first)", "varName": "costOneBom", "code": "<step code below>" } } },
    { "id": "n_write", "type": "wfNode", "position": { "x": 80, "y": 1150 },
      "data": { "typeId": "code", "config": { "title": "Write the costs back to the products", "varName": "writeBack", "code": "<write code below>" } } }
  ],
  "edges": [
    { "id": "e1", "source": "n_trig",  "target": "n_query", "targetHandle": "in:list" },
    { "id": "e2", "source": "n_query", "target": "n_seed",  "sourceHandle": "data:list" },
    { "id": "e3", "source": "n_seed",  "target": "n_while" },
    { "id": "e4", "source": "n_while", "target": "n_test",  "sourceHandle": "cond" },
    { "id": "e5", "source": "n_while", "target": "n_step",  "sourceHandle": "a" },
    { "id": "e6", "source": "n_while", "target": "n_write", "sourceHandle": "b" }
  ]
}
```

The four `code` values are JSON strings (escape newlines as `\n`); shown unescaped here for readability:

```python
# n_seed — initialize the work stack and the cost memo in context
context['stack'] = [p['id'] for p in (bomProducts.get('data') or [])]
context['cost'] = {}          # productId -> rolled-up purchase cost
```

```python
# n_test (wired to the "Test" output) — loop while work remains
result = len(context.get('stack', [])) > 0
```

```python
# n_step — post-order: cost a BOM only after its sub-BOMs are done
node_id = context['stack'][-1]                       # peek, don't pop yet
comps = (business_entity_op('billOfMaterials', 'list',
         {'query': {'parentId': node_id}}).get('data') or [])
pending = [c for c in comps
           if c.get('isBom') and c['componentId'] not in context['cost']]
if pending:                                       # children first
    for c in pending:
        context['stack'].append(c['componentId'])
else:                                             # all children costed -> finalize
    context['stack'].pop()
    total = 0.0
    for c in comps:
        cid = c['componentId']
        unit = context['cost'].get(cid)
        if unit is None:                          # leaf: take its own purchase price
            prod = business_entity_op('product', 'read', {'path': {'uuid': cid}})
            unit = float(prod.get('purchasePrice') or 0)
            context['cost'][cid] = unit
        total += unit * float(c.get('quantity') or 0)
    context['cost'][node_id] = total
```

```python
# n_write (Done branch) — persist the computed costs
for pid, cost in context.get('cost', {}).items():
    business_entity_op('product', 'update',
        {'path': {'uuid': pid}, 'body': {'calculatedPurchasePrice': round(cost, 4)}})
log(f"Updated {len(context.get('cost', {}))} product costs.")
```

Why `while` and not `loop`: the number of passes equals the total number of BOM nodes across the whole tree — unknown until you walk it. The wired `n_test` re-runs each iteration and stops the loop the instant the stack empties. **Mind the 1000-iteration cap**: it bounds *total BOM nodes processed per run*, not tree depth — if a catalog can have more than 1000 distinct BOMs/sub-BOMs, page the top-level list (`n_query`) and run the rollup in batches, or raise the cap deliberately. A `componentId not in context['cost']` check doubles as cheap cycle protection (a BOM that references itself won't be re-pushed forever).

## Idempotency

Workflows must be **safely re-runnable**. If you cancel an order, check status first — the second run otherwise errors on the redundant update. When building, scope filters so already-processed items are excluded (`status != cancelled`).

## Debugging a workflow

When an existing workflow misbehaves (wrong results, missed records, a failing node), do **not** debug by staring at the JSON — switch to the **`xentral_workflow_debug`** tool and read its `help` first. It lets you probe the tenant's live Xentral API with throwaway Python scripts in the workflow sandbox, execute the workflow for a step-level transcript, and apply config fixes directly (`apply_patch`) — then verify with a re-run. Use `xentral_workflows` to build and edit; use `xentral_workflow_debug` to find out why a built workflow doesn't do what it should.

**Don't wait for it to misbehave — test as you build.** Validation only checks the graph's shape, never the live API, so a wrong endpoint or binding surfaces only at runtime. Right after building a read/source node, smoke-test it with `xentral_workflow_debug` `run_node` (one node, live, read-only) to confirm its endpoint resolves and returns the shape you expect. Before activating a workflow that writes, run it once with `run_workflow dry_run=true`: the whole graph runs but every write is suppressed and logged as `[dry-run] suppressed …`, so you can confirm what it *would* write with zero side effects.

