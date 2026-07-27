---
name: xentral-datasets
description: >
  Create and edit the customer's own data tables ("lite datatables") with the
  xentral_datasets tool. A DataSet is a SET OF TABLES (like a Supabase project),
  isolated per tenant in a managed Postgres. Covers starting from a template
  (CRM, sales pipeline, inventory, operations, finance, storage) versus a blank
  set, adding/renaming/dropping typed columns, and reading/writing rows. Use when
  the user wants an ad-hoc list, an import target, working data, or an agent
  scratch table — NOT for ERP master data (customers/orders/products/invoices),
  which belongs to xentral_erp_core.
examples:
  - "Make me a CRM to track contacts and deals."
  - "Create a table of suppliers with a quality rating and import this CSV into it."
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
- **Table** — a table inside a set, addressed by `table`. Holds typed columns.
- **Column** — `{name, type, label}`; types: `text, number, boolean, date,
  datetime, json, select`. Adding a column is a metadata edit — no migration.
- **Row** — a record; each column value is stored under its column name.

## How to work

1. **Start from a template when one fits.** Templates are whole multi-table
   sets: `crm` (contacts, companies, deals, activities), `sales`, `inventory`,
   `operations`, `finance`, `storage`. `create_set` with the template's tables,
   or start blank and add tables.
2. **Create / evolve** — `create_set`, `create_table`, `add_column`,
   `rename_column`, `drop_column`. Names start with a letter and use only
   letters, digits, underscores.
3. **Read / write rows** — `rows` (with optional `search`, `sort`, `limit`),
   `insert`, `update`, `delete`. Only known columns may be written.

## Actions (xentral_datasets)

`list_sets`, `create_set`, `describe_set`, `drop_set`,
`create_table`, `describe_table`, `drop_table`,
`add_column`, `rename_column`, `drop_column`,
`rows`, `insert`, `update`, `delete`, `help`.

Every write is tenant-isolated at the database layer; you never see or need the
underlying credentials.
