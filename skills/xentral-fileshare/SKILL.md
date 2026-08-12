---
name: xentral-fileshare
description: >
  Work with the tenant's files — the Shared Drive / Datenaustausch — using the
  xentral_fileshare tool: list what is there, read a file, drop an artifact back,
  delete an obsolete one. Covers what a file_key is and why you always quote it,
  where a file came from (source: chat, inbox, slack, advisor, api), the inline
  read caps and what to do instead when a file is over them, and the boundaries
  to the tools that own other things: tabular data belongs to xentral_datasets,
  ERP records to xentral_erp_core / xentral_copilot, facts to
  xentral_knowledge_base. Most importantly: a file the user attached in the chat
  is ALREADY in here and you already hold its file_key.
  Use when a file is the subject — the user refers to one, you produced one, or
  you need its contents to answer.
examples:
  - "Here are my remaining master records, please put them in."
  - "Was liegt bei mir im Datenaustausch?"
  - "In der Mail vom Lieferanten war ein PDF — schau mal rein."
---

# Fileshare

## Purpose

Per-tenant storage for **working files** — CSVs to import, price lists, contracts
to reference, reports you generate, attachments captured from inbound email or a
chat message. Operators upload, you read along and may write back.

What it is *not*:

- **Not the ERP.** Customers, orders, products, invoices, delivery notes, returns
  are records in Xentral → `xentral_erp_core` / `xentral_copilot`.
- **Not the knowledge base.** Rules, organisation facts and reusable snippets go
  to `xentral_knowledge_base`. This is for *files*, not facts.
- **Not a table.** The moment the question is "how many rows", "what is the sum",
  "which of these already exist" → the file belongs in `xentral_datasets`
  (`import_analyze` first). See *Tabular data* below; getting this wrong is the
  most expensive mistake at this boundary.
- **Not versioned.** No diff, no history, no branches. A second upload of the
  same name is a second file.

## A file the user attached is already in here

The client uploads an attachment before your turn starts, so you hold its
`file_key`, with `source='chat'`. Therefore:

- **Never ask the user to upload a file they just attached.** They already did.
- **Never tell them a file was too large to receive.** Nothing is too large to
  receive. What is too large to *inline* reaches you as the key plus, at most, a
  labelled sample of the first lines — the file itself is complete in storage.
- **Never answer from a sample.** A row count, a total, or a "the file contains…"
  taken from a labelled sample is wrong, and specific enough to be believed. Read
  the file, or profile it.

## When to invoke

- The user refers to a file ("the price list I just uploaded", "die Datei vom
  Lieferanten") → `list` first, then act on the `file_key`.
- The user asks what is there ("welche Dateien liegen da?") → `list`, no filter.
- You produced something worth keeping (a cleanup report, an export) → `upload`,
  with `tags`, and tell the user it is in the Datenaustausch.
- You need a file's contents to answer, and it is small and not tabular → `read`.
- The user asks you to remove an obsolete file → `list`, confirm the name back to
  them, then `delete`.

Do **not** invoke when:

- The question is about an ERP record ("show me order 12345") → `xentral_copilot`.
- The file is a CSV/TSV whose *contents* matter → `xentral_datasets`.
- A file should be attached to an email being drafted → the email composer owns
  that.
- The user wants a new PDF template → `xentral_pdf_templates` `action='create'`.

## Concepts

| Term | Meaning |
|---|---|
| `file_key` | Stable UUID of one file. Survives renames; it is what every action takes. Quote it from a previous response — never reconstruct it, never pattern-match a filename instead. |
| filename | Display name only. **Not unique** — two files may share one. |
| `source` | How the file arrived: `chat` (user attached it to a chat message), `inbox` (inbound email), `slack` (posted in a thread), `advisor` (you uploaded it), `api` (manual UI upload), or custom. A `list` filter. |
| `source_id` | Where within that source: the conversation for `chat`, the thread for `slack`, the email id for `inbox`. |
| `tags` | Short free-form labels for grouping (`['pricing','q4']`). A `list` filter. |
| `mime_type` | Decides whether `read` returns text or base64. `text/*`, `application/json`, `application/xml`, `application/yaml`, `application/csv` count as text; everything else is binary. |
| Inline cap | `read` returns at most 200 KB of text / 100 KB of binary. Over that it returns metadata plus an error — see below. |

## Actions

- **`list`** — newest first, metadata only. Filters: `source`, `tags`, `limit`
  (default 50, max 500). Do this before any per-file action so you hold a real key.
- **`metadata`** — everything about one file without its bytes. Cheaper than
  `read` when you only need name, size, type, tags.
- **`read`** — the contents. Text returns inline (`encoding: 'text'`); small
  binary returns base64. Over the cap you get `error:
  'too_large_for_inline'` / `'binary_too_large_for_inline'` and no content.
- **`upload`** — `filename` plus **exactly one** of `content` (text) or
  `content_b64` (binary). Optional `mime_type` (guessed from the filename),
  `description`, `tags`. Lands as `source='advisor'`.
- **`delete`** — one file by key. Irreversible: no trash, no undo.

## When `read` will not give you the file

A file over the inline cap cannot be read through this tool at all. Do not tell
the user "it is too large" and stop — that is a dead end they cannot act on.
Instead:

- **CSV / TSV** → `xentral_datasets(action='import_analyze', file_key=…)`. It
  profiles **every** row — column names, fill rates, distinct counts, value
  signatures, warnings — and comes back in a few KB whatever the file size. This
  is also the right move for a *small* table the moment a figure is wanted.
- **Anything else** → say what the file is (from `metadata`) and point the user at
  the Datenaustausch UI, where they can open or download it.

## Rules that bite

1. **Tenant isolation is server-side.** A key from another tenant returns
   `not_found`. You never validate a license yourself.
2. **`content` XOR `content_b64`.** Both or neither is an error. Text for CSV /
   JSON / YAML / code; base64 for PDFs, images, archives. `content` for binary
   silently corrupts the file.
3. **`delete` is irreversible.** Repeat the filename and size back to the user and
   get consent — "delete `prices-q4.csv` (123 KB)?" — unless they named that exact
   file themselves. A UUID is not a confirmation prompt.
4. **Uploading is not linking.** A file here does not appear in a customer's
   history. If the user wants it *attached to a customer*, that is a Correspondence
   entry via `xentral_erp_core`.
5. **`uploaded_at` is server wall clock.** Fine for ordering, not for legal claims
   about when something happened.

## What this tool cannot do

Say so plainly rather than pretending otherwise, and reach for the alternative:

| Missing | Do this instead |
|---|---|
| Read part of a file (offset/limit) | Whole-file `read` under the cap; for a table, `import_analyze` |
| Search inside a file | For tabular data: `import` it, then SQL via `xentral_datasets(action='query')` |
| Edit a file in place | `upload` a new file (name it so the relation is obvious) and, if the user agrees, `delete` the old one |
| Folders | The store is flat — group with `tags` |
| Versions / diffs | Upload dated copies; there is no history |
| Extract xlsx / docx | Ask for a CSV export, or hand the file to a workflow |

Recipes, pre-flight checks and the pitfalls that cost the most time:
`reference/recipes-and-pitfalls.md`.
