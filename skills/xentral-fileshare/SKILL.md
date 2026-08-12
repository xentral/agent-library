---
name: xentral-fileshare
description: >
  Work with the tenant's files — the Shared Drive / Datenaustausch — using the
  xentral_fileshare tool: list what is there, read a file whole or in line windows,
  search inside one, edit it in place, drop an artifact back, delete an obsolete one. Covers what a file_key is and why you always quote it,
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
- **`read`** — the contents. Without `offset` you get the whole file (text inline;
  small binary as base64), or `error: 'too_large_for_inline'` if it does not fit.
  **With `offset`** (1-based line) plus `limit` (lines, default 200) you get a
  *window*, streamed — this is how a large file is read at all. The response says
  which lines you got, whether more follows, and the `offset` to continue from.
- **`find`** — search a text file line by line without loading it: `pattern`
  (substring, or `regex=true`), plus optional `ignore_case`, `context` (lines
  around each hit, max 5) and `max_hits` (default 50). Returns line numbers you
  feed straight back into `read` as `offset`.
- **`upload`** — `filename` plus **exactly one** of `content` (text) or
  `content_b64` (binary). Optional `mime_type` (guessed from the filename),
  `description`, `tags`. Lands as `source='advisor'`.
- **`update`** — change a text file in place, keeping its `file_key`: `content`
  replaces the body, `old_string` + `new_string` patches one occurrence. Read
  *Overwriting* below before using it.
- **`delete`** — one file by key. Irreversible: no trash, no undo.

## A big file: window it, search it, or profile it

Never say "the file is too large" and stop — that is a dead end for the user, and
these three routes exist precisely so it is never true:

- **You know roughly where to look** → `read` with `offset` / `limit`. Continue from
  the `to_line` the response reports.
- **You do not know where to look** → `find` with a pattern, then window around a
  hit's line number. Locating something in a 50 MB log costs a few hundred tokens.
- **A figure is wanted** — how many rows, what is the sum, which values occur — →
  `xentral_datasets(action='import_analyze', file_key=…)`. It reads **every** row
  and returns a few KB whatever the file size. This is also the right move for a
  *small* table: a window is a window, and a count taken from one is wrong.

Two things a response will tell you, and you must pass on rather than paper over:
a window says whether more follows, and `find` says when it stopped at `max_hits`.
Reporting "3 matches" for a file that has 900 is the same class of wrong answer as
counting rows from a sample.

Only a *binary* file over the cap has no route: say what it is (from `metadata`) and
point the user at the Datenaustausch UI.

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

## Overwriting

`update` is irreversible: there is no version history, no trash, and the `file_key`
stays the same — so everything that referred to this file now sees the new bytes.
Which is why the server, not your judgement, decides:

| The file | What you may do |
|---|---|
| You uploaded it (`source='advisor'`) | `update` freely — it is your own output |
| The user attached or uploaded it (`chat`, `api`, …) | **Upload a new file** beside it (`kunden-bereinigt.csv`) so the original survives. Only if the user explicitly asks to overwrite *that* file: repeat its name and size, say it cannot be undone, then `update` with `confirmed=true` |
| An inbound email attachment (`source='inbox'`) | Never. It is the record of what a supplier sent, and refusal is not negotiable |

And regardless of the file:

- **An overwrite is its own step, never a stage in a bigger task.** "Import this CSV"
  does not license writing a cleaned version back over it.
- **Patch anchors are exact.** `old_string` must occur once; two occurrences are
  refused with the count, because a first-match replace changes the wrong line
  silently. Include surrounding lines until the anchor is unique.
- **You cannot replace the body of a file you could not read whole.** Over the read
  cap the server refuses it — you would drop everything you never saw. Patch it
  instead; an anchor does not require having read the file.
- An edit that would leave the file empty is refused: `delete` is the separate,
  confirmed step for that.

## What this tool still cannot do

| Missing | Do this instead |
|---|---|
| Folders | The store is flat — group with `tags` |
| Versions / diffs / undo | Upload dated copies; an overwrite is final |
| Extract xlsx / docx | Ask for a CSV export, or hand the file to a workflow |
| Edit a binary file | Upload a corrected copy with `content_b64` |

Recipes, pre-flight checks and the pitfalls that cost the most time:
`reference/recipes-and-pitfalls.md`.
