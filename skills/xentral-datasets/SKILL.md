---
name: xentral-datasets
description: >
  Create, query and import into the customer's own data tables ("lite
  datatables") with the xentral_datasets tool. A DataSet is a SET OF TABLES (like
  a Supabase project), isolated per tenant in a managed Postgres. Covers starting
  from a template (CRM, sales pipeline, inventory, operations, finance, storage)
  versus a blank set, adding/renaming/dropping typed columns, reading/writing
  rows, read-only SQL, and the guided CSV import — upload to Fileshare, analyse,
  agree the destination, probe the first rows, confirm, load the rest, clean up.
  Use when the user wants an ad-hoc list, an import target, working data, or an
  agent scratch table — NOT for ERP master data (customers/orders/products/
  invoices), which belongs to xentral_erp_core.
examples:
  - "Make me a CRM to track contacts and deals."
  - "Here's a CSV export from our old system — can you get it into Xentral?"
  - "Add a 'priority' column to my tasks table and mark the overdue ones done."
---

# DataSets

## Purpose

DataSets are the customer's **own free-form data**, kept in a platform-managed,
schema-per-tenant Postgres — the place for the lists a small/medium business
needs when there is no ERP entity for the job yet. A **DataSet is a set of
tables** (like a Supabase project): one set groups several related tables, each
with its own typed columns and rows.

Reach for DataSets when the user wants to *keep and edit their own data*. Do NOT
use it for ERP master data — customers, orders, products, invoices live in the
ERP and are reached through `xentral_erp_core`.

## Model

- **Set** — the DataSet container (a Supabase-style project). Addressed by
  `dataset` in the tool.
- **Table** — a table inside a set, addressed by `table`. A real Postgres
  relation, so it is queryable with plain SQL and scales with indexes.
- **Column** — `{name, type, label}`; types: `text, integer, number, boolean,
  date, datetime, uuid, json, select, reference` (`reference` is a real foreign
  key to another table's id in the same set). Adding or changing a column is a
  real `ALTER TABLE`, not a metadata edit — it applies to existing rows, and a
  type change can fail on data that does not convert.
- **Row** — a record; each column value is stored in its own typed column.

## How to work

1. **Start from a template when one fits.** Templates are whole multi-table
   sets: `crm` (contacts, companies, deals, activities), `sales`, `inventory`,
   `operations`, `finance`, `storage`. `create_set` with the template's tables,
   or start blank and add tables.
2. **Create / evolve** — `create_set`, `create_table`, `add_column`,
   `rename_column`, `drop_column`, `change_type`, `set_not_null`, `set_default`.
   Names start with a letter and use only letters, digits, underscores.
3. **Read / write rows** — `rows` (with optional `search`, `sort`, `limit`),
   `insert`, `update`, `delete`. Only known columns may be written.
4. **Query** — `query` runs one read-only SQL statement (see below).

## Table names in SQL are not the display name

This trips up every first attempt. Table names are only unique *within* a set, so
the shared tenant schema cannot expose them flat. The physical relation has a
hashed name, and that is what SQL must use.

```
describe_table  → { "name": "leads", "sql_name": "t_bb5e7323b8ac522e", … }
query           → SELECT count(*) FROM t_bb5e7323b8ac522e
```

Always take `sql_name` from `describe_table` first. `SELECT * FROM leads` fails
with "relation does not exist".

`query` runs **one read-only statement** as the tenant's own Postgres role.
Writes and cross-tenant reads are rejected by the database, not by a filter — so
SELECT and `information_schema` work, nothing else does.

## The guided CSV import

Six phases. Each ends in something the customer can reject, and no phase silently
enables the next. Full detail — warning semantics, the failure mode this guards
against, cleanup mechanics, and the quirks real exports contain:
`reference/csv-import.md`.

### 0 · Get the file in

`xentral_fileshare` `action='upload'` → keep the `file_key`.

**Never ask for the CSV as a chat attachment.** Attachments cap at 512 KB and
inlined text truncates at 20 000 characters — a few percent of a typical export.
The truncation is labelled, so you will know you only got a fragment, but a
fragment is useless here: any row count or total computed from it is wrong.

### 1 · Open a session

`import_session` with the `dataset` and `file_key` → a `session_id`. Pass it to
every later call, so a single `session_cleanup` can undo the whole import.

### 2 · Analyse before anything else

`import_analyze` returns, per column: name, fill rate, distinct count, max
length, a value signature, and up to five example values — plus file-level
warnings. A few KB whatever the file size; the rows are never returned.

**Read the warnings out to the customer.** `column_shift` means the file is
structurally damaged: values sit one or more columns away from their header. Such
a file parses perfectly and imports into the wrong columns, so the import refuses
it. Do not override without an explicit decision — fixing the export upstream is
almost always the better answer.

### 3 · Agree the destination in chat

The example values make this answerable without loading anything:

- What is this file? What does one row represent?
- Which columns matter, which are noise?
- What is the natural key — the column that says "this is the same record"?
- Does it become a DataSet table, or eventually ERP records?

Default to a DataSet table. Writing ERP entities is the rare case and needs a
field mapping; a table gets the data somewhere queryable *now*, and promoting it
later is a normal SQL job.

### 4 · Probe the first rows

`import` with `limit_rows=5` loads into `<table>_probe` — never the target table.
Read the rows back with `rows` or `query` and show them.

The probe answers what the profile cannot: do these rows look right to the person
who knows this data? If they are wrong, fix and re-probe — the probe table is
dropped and rewritten, so looping is cheap.

### 5 · Load the rest

Only after an explicit confirmation: `import` **without** `limit_rows`. Never skip
to the full run because the profile "looked fine".

### 6 · Offer to clean up

`session_cleanup` removes everything the session created — the probe table, the
target table, the uploaded file — reports each artifact's outcome, and is safe to
run twice. Workflow artifacts are reported as `unsupported` rather than removed;
read that back instead of calling the cleanup complete.

Ask which the customer wants. Both are correct: a recurring import keeps its
table, a one-off leaves nothing. **Never clean up on your own**, and never after
a failure — that is exactly when the customer needs to inspect what was written.

`import_status` / `import_sessions` show what a session created.

## Every import is raw — and that is deliberate

Every column becomes `text`, with names normalized from the header. The import
practically cannot fail, which is the point: typing a customer's export at load
time means guessing, and a wrong guess *rejects rows*.

So get the data in, then shape it in SQL, where a mistake is a fixable statement
rather than a failed import:

```sql
SELECT to_date(angelegt_am, 'DD.MM.YY')                   AS created,
       replace(replace(wert, '.', ''), ' €', '')::numeric AS value
FROM   t_abc
WHERE  angelegt_am ~ '^\d{2}\.\d{2}\.\d{2}$';
```

Blank cells arrive as SQL `NULL`, not empty string.

There is no typed/mapped import mode yet. Do not offer one — say the shaping
happens in SQL, which is true and is the faster answer anyway.

## Recurring imports become workflows

Once an import is established as recurring, build a workflow with the
`dataset-import` and `dataset` nodes (`xentral_workflows`). The guided flow above
is conversational and stays manual; the workflow is for the unattended repeat.

**Volume must never travel through the graph.** The `loop` and `worklist` nodes
cap at 1000 items, and the cap is logged while the run still reports success — so
a row-by-row workflow over a 5000-row file imports 1000 rows and tells you it
worked. `dataset-import` returns counts rather than rows for exactly this reason.
Filter and aggregate in a `dataset` SQL node, and only ever loop over the result.

## Actions (xentral_datasets)

`list_sets`, `create_set`, `describe_set`, `drop_set`,
`create_table`, `describe_table`, `drop_table`,
`add_column`, `rename_column`, `drop_column`, `change_type`, `set_not_null`,
`set_default`, `rows`, `insert`, `update`, `delete`, `query`,
`import_session`, `import_analyze`, `import`, `import_status`,
`import_sessions`, `session_cleanup`, `help`.

Every write is tenant-isolated at the database layer; you never see or need the
underlying credentials.

## Reference

- `reference/csv-import.md` — the import flow in full.

For the exact parameter contract, call `action='help'` — the tool documents its
own schema, so it cannot drift from the implementation the way a copy here would.
