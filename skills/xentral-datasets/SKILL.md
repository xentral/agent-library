---
name: xentral-datasets
description: >
  Create, query and import into the customer's own data tables ("lite
  datatables") with the xentral_datasets tool. A DataSet is a SET OF TABLES (like
  a Supabase project), isolated per tenant in a managed Postgres. Covers starting
  from a template (CRM, sales pipeline, inventory, operations, finance, storage)
  versus a blank set, adding/renaming/dropping typed columns, reading/writing
  rows (including rows_bulk for many at once), read-only SQL, and the two ways to
  get a CSV in: the guided server-side import (upload to Fileshare, analyse, agree
  the destination, probe the first rows, confirm, load the rest, clean up), or —
  when you have local file tools — cleaning and repairing the file yourself and
  writing it with rows_bulk.
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

## Two ways to get data in — pick one first

Before anything else, work out which situation you are in. It changes the whole
procedure.

**Do you have local file tools?** Can you read a path, run a script, inspect bytes?

- **No** (you are the in-app Advisor): the customer's file is not reachable by you.
  Have them put it in Fileshare and run **the guided CSV import** below. The server
  does the parsing; you never see the rows.
- **Yes** (you are Claude Code or similar, on the customer's machine): the file is
  already in front of you, and you can do something the server cannot — **repair
  it**. Use the local path below.

Neither is a fallback for the other. They differ in who holds the data, and that
decides everything downstream.

### The local path

1. **Profile and clean the file with your own tools.** Read it, check the header
   against the values, fix what is broken, normalise types. Do this in a script —
   never by loading the file into your context.
2. **Get the target shape**: `describe_table` gives you the columns and their
   types. A few KB.
3. **Write it with `rows_bulk`** — batches of up to 500, positional value arrays.
   Values may be strings; they are coerced per column type.
4. **Say what you changed.** If you repaired a column shift, dropped rows, or
   converted dates, list it. The customer cannot see your script.

**Where the local path stops.** Every value you send is something you have to
write out. A 5000-row × 12-column export is roughly 300k tokens of output — slow,
expensive, and the wrong tool. Past about a thousand rows, upload the cleaned file
to Fileshare and switch to the guided import: the data then never passes through
you at all.

So: repair locally, and decide by size whether to *send rows* or *send a file*.

**Run `import_analyze` even after a local repair.** You believe you fixed the
file; the server checking it independently is how you find out. If the analysis
comes back clean, say that — it is the evidence your repair worked, not a
formality.

## The guided CSV import

Use this when the file is in Fileshare — either because the customer put it there,
or because you cleaned it locally and uploaded it.

Six phases. Each ends in something the customer can reject, and no phase silently
enables the next. Full detail — warning semantics, the failure mode this guards
against, cleanup mechanics, and the quirks real exports contain:
`reference/csv-import.md`.

### 0 · Get the file in

Both routes end in a `file_key`, and it is the same store either way:

- **The customer attached it in the chat.** It is already in Fileshare — the
  message you received carries its `file_key`. Use that key. Never ask them to
  upload the file a second time.
- **Otherwise:** `xentral_fileshare` `action='upload'` → keep the `file_key`.

**Never answer from what you can see of the file.** Anything too big to inline
reaches you as a `file_key` plus, at most, a labelled sample of the first lines. A
row count, a sum or a "the file contains…" taken from that sample is wrong, and
specific enough to be believed. `import_analyze` reads every row and comes back in
a few KB — that is the only honest source for a statement about the whole file.

### 1 · Open a session

`import_session` with the `dataset` and `file_key` → a `session_id`. Pass it to
every later call, so everything the import creates is recorded in one place and
can be undone together.

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

**Import into a set you created yourself.** `import` creates a table, which is
DDL, and you may only do DDL on your own draft objects (see *Lifecycle*). Trying
to import into a set the customer built returns:

```
Error: agents cannot do this
       (agents may only add tables to their own draft datasets)
```

So `create_set` a draft set for the import — name it after the source, e.g.
`crm_import` — and load into that. Then tell the customer where the data landed so
they can activate it, or copy from it with `query` + `insert` into a table of
theirs. That is the intended shape, not a workaround: raw imported data belongs in
a staging area you own until a human has looked at it.

### 4 · Probe the first rows

`import` with `limit_rows=5` loads into `<table>_probe` — never the target table.
Read the rows back with `rows` or `query` and show them.

The probe answers what the profile cannot: do these rows look right to the person
who knows this data? If they are wrong, fix and re-probe — the probe table is
dropped and rewritten, so looping is cheap.

### 5 · Load the rest

Only after an explicit confirmation: `import` **without** `limit_rows`. Never skip
to the full run because the profile "looked fine".

### 6 · Offer to clean up — and know what you can actually do

Ask which the customer wants. Both are correct: a recurring import keeps its
table, a one-off leaves nothing. **Never clean up on your own**, and never after
a failure — that is exactly when the customer needs to inspect what was written.

`import_status` / `import_sessions` list what a session created.

**You cannot hard-delete.** `session_cleanup` is a hard delete, and the store
locks agents out of those (see *Lifecycle* below), so it will come back with each
artifact `failed` and the store's reason attached. That is correct behaviour, not
a bug to route around. So:

- Report the refusal and what is still there, and let the customer remove it in
  the app; **or**
- `archive_table` the tables yourself — freshly imported tables are `draft`, which
  you are allowed to archive, and archiving is reversible.

Do not call `session_cleanup` repeatedly hoping it takes. Workflow artifacts are
reported as `unsupported` for a different reason: cleanup cannot remove them at
all yet.

## Lifecycle: draft → active → archived

Every set and table carries a status, and it governs what you may do:

- **`draft`** — while it is being built. You can edit it and `archive_table` /
  `archive_set` it. New tables, including the ones an import creates, start here.
- **`active`** — a human published it. Protected: it must be archived before it
  can be removed, and that is a human action.
- **`archived`** — reversible soft-delete. Purging is a human action.

As an agent you may create and edit, and archive **your own drafts**. You can
never hard-delete, never purge, and never touch an active or locked object. There
is no `drop_set` / `drop_table` on this tool for that reason.

This is why the cleanup step above reads the way it does — and it is a good
default: an import you just made is a draft, so it stays yours to undo, while data
the customer has committed to is not something you can remove by accident.

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
