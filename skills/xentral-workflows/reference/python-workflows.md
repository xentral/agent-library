# Writing a workflow as Python

A workflow can be written as a Python file instead of assembled as a graph.
Same runtime, same triggers, same run log — a different way of stating it.

Use `init_python` / `update_python` with the whole file in `python_source`.

## The shape

```python
from xentral.workflow import workflow, step, erp_event, business_entity_op, log

@workflow(name="Overdue check", trigger=erp_event("salesOrder.created"))
def main(trigger):
    with step("Load customer"):
        customer = business_entity_op("Customer", "get", {"id": trigger["body"]["customerId"]})

    if customer["balance"] > 1000:
        with step("Flag it"):
            log("over limit")
            result = {"flagged": True}
```

Five rules, and that is the whole contract:

1. **Exactly one `@workflow(...)` function**, taking exactly one argument — the
   trigger payload. `name` and `trigger` are required, `description` optional.
2. **Each box is a `with step("Label"):` block.** The label is what the run log
   and the canvas show. Write the call on one line so it gets a stable id;
   pass `id="…"` to fix the id yourself.
3. **Control flow is ordinary Python** — `if`, `else`, `for`, `while`. There is
   no `{{ }}` template language: an earlier step's value is just a variable.
4. **Import only from `xentral.workflow`.** Everything a node can do is a
   function there. No other import is accepted.
5. **A step's output is whatever it assigns.** Assign to a named variable and
   later steps read that name.

Name, description and trigger are read off the decorator — do **not** also
pass them as tool arguments.

## Choosing between Python and the graph

| Prefer the graph | Prefer Python |
|---|---|
| A non-technical user needs to read the flow on the canvas | The logic is the point — nested loops, many conditions, intricate aggregation |
| The workflow is a short, linear list of ERP steps | The graph would need several `code` boxes anyway |
| Someone will edit it in the designer | It belongs in review / version control as text |

A Python workflow **is** shown on the canvas — the graph is derived from the
source — but read-only. Editing happens in the code.

The honest default: if you were about to build a graph whose real work sits in
`code` boxes, write it as Python instead. If a colleague in operations has to
maintain it by clicking, build the graph.

## Triggers

```python
manual()
schedule(frequency="daily", time="09:00")   # hourly | daily | weekly | monthly
schedule(frequency="weekly", time="08:00", weekdays=["mo", "th"])
schedule(frequency="hourly", hour_interval=6)
webhook()
erp_event("salesOrder.created")
integration_event(connector="shopify", event="order.created")
```

Several triggers on one flow: `trigger=[manual(), schedule(frequency="daily")]`,
then `fired("schedule")` in the body tells you which one started this run. Two
triggers of the same kind are rejected — the run could not tell them apart.

Registration is identical to the graph path: a `schedule(...)` really does
register with the schedule service, and a `webhook()` really does need
`share`. Declaring a trigger is not the same as arming it.

## What you can call

Everything below is imported from `xentral.workflow`. These are the same
implementations the graph nodes use, so behavior matches node for node.

**ERP and business data**
`business_entity_op(entity_key, operation, params)` ·
`xentral_action(name, params)` · `xentral_op(method, path, params)` ·
`xentral_request(method, path, **kwargs)` · `kpi_op` · `report_run` ·
`dataset_query` · `dataset_import` · `fileshare_op`

**Outside the ERP**
`integration_action(tool_id, action, params)` · `http_request(method, url, headers, body)` ·
`web_search(query)` · `shiplabel_create_label(carrier, request)` ·
`send_email(to=…, subject=…, body=…)` · `create_decision(text)` · `create_job(title, content)`

**Language work**
`run_agent(model=…, prompt=…)` · `run_judge(intent=…)`

**In a box**
`log(...)` · `skip(reason)` · `sleep_for(seconds)` · `to_json` / `parse_json`

**Dates** — same helpers as the graph path: `now today yesterday tomorrow shift
start_of end_of period last this ytd last_n_days days_between days_since
days_until is_overdue is_before is_after between age_bucket business_days
next_business_day is_business_day`.

`business_entity_op` takes the operation as an argument, so there is no
`targetHandle` to get wrong — the commonest graph mistake does not exist here.

## What the sandbox rejects

The whole file goes through the same AST allowlist a `code` box gets, plus
exactly the syntax above. Everything listed under "Code node — what's allowed"
in [code-and-data.md](code-and-data.md) still applies to the file as a whole:

- `import` anything other than `from xentral.workflow import …`
- `with` over anything other than `step(...)`
- `lambda`, `try`/`except`, `raise`, `class`, `async`/`await`/`yield`,
  `global`/`nonlocal`
- `eval exec compile open input breakpoint getattr setattr delattr vars
  globals locals memoryview __import__`
- dunder names and `_`-prefixed attribute access

Same size ceiling: 500 non-empty lines, 100,000 characters.

A rejected file is **not stored**. The error names the line, so fix that line
and resend — there is no `check` step to run afterwards the way there is for a
graph.

## Capabilities the Python path does not have yet

Build these as a graph:

- **Human task / worklist** — no DSL helper exists, so a Python workflow
  cannot create a task or wait for a person.
- **Rule groups** — write the `if` / `elif` chain yourself instead.

Self-recursion needs no node: write a recursive Python function in the file.

## Converting an existing graph workflow

`draft_python` translates a stored graph workflow into Python and **changes
nothing** — it returns a draft.

Roughly four out of five nodes convert. The rest come back as
`# TODO(convert):` with the node's original config, and the response lists
them; the converter never invents a call it cannot derive. `xentral-api` nodes
always need a hand (they store an OpenAPI operation, not the method and path
`xentral_op` takes).

Workflow: `draft_python` → resolve **every** TODO → `init_python` under a
**new** id → prove the replacement runs → only then retire the original. Do
not overwrite the graph workflow; `update_python` refuses it on purpose.

## Debugging

`xentral_workflow_debug.run_workflow(dry_run=true)` works exactly as it does
for a graph — the run log is keyed by the same step labels you wrote. Running
a single box in isolation is not supported for Python workflows yet.
