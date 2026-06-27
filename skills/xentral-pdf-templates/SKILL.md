---
name: xentral-pdf-templates
description: >
  Design and edit Xentral PDF business documents — invoices, delivery notes,
  offers, order confirmations, credit notes, and free-form letters — with the
  `xentral_pdf_templates` MCP tool. Covers the Jinja2 + HTML/CSS model, the
  create/check/render workflow, and routes to detailed references for
  transactional documents, e-invoice compliance, free documents, and
  layout/styling. Use whenever the user wants to create, restyle, or fix a PDF
  document template in Xentral.
---

# Building Xentral PDF documents (Belege)

The `xentral_pdf_templates` tool is a **plain rendering engine**: Jinja2 +
HTML/CSS in, PDF out. It does **not** know what an invoice should look like —
that knowledge lives in this skill. Always start from a scaffold or an existing
template; never hand-write a full document structure from memory.

## The model in one paragraph

Templates are **Jinja2 + HTML + CSS**. Missing data accesses render empty
(chainable-undefined), so don't guard every field. Per-page headers/footers use
CSS `@page` margin boxes, not `position: fixed`. The base layout is extended
(`{% extends "_base/base.html.j2" %}` + `{% block content %}`). Visible text
comes from translations as `{{ L.key }}`; money/dates/numbers must be filtered
(`| money`, `| date`, `| number`) and localized — never print raw floats or ISO
dates.

## The workflow (every task)

1. `action: help` — the live manual for this tool version. Read once per session.
2. `action: list` — see built-in + custom templates; **clone the closest match**.
3. `action: get` (`id`) — pull `html`, `css`, `example_data`, metadata.
4. Edit **surgically** where possible: `set_block`, `set_style`, `set_asset`,
   `set_infobox`, `set_translation` — instead of rewriting `html`/`css`. Every
   write is validate-or-reject; `list_versions` / `restore_version` make all
   writes undoable.
5. `action: check` — static hygiene (unformatted dates, untranslated vars,
   missing assets) + optional live render and e-invoice XML validation.
6. `action: render` — produce the PDF / PNG preview. **Verify against real ERP
   data, not just `example_data`** — example data hides date/number/locale bugs.
   Debug binding with `set_debug_capture` → render → `last_payload`.

## Two scaffolds

- **`document_blank`** — line-item document (invoice, order, delivery note,
  offer, credit note). Clone for anything with positions.
- **`letter_blank`** — free-form letter, no positions table.

## Which reference to read

Read the file that matches the task — do not load all of them:

- **Building & editing a template** — structure-first-then-skin, the scaffolds,
  granular edits (`set_block`/`set_style`/…), concepts/terminology →
  [reference/building-and-editing.md](reference/building-and-editing.md)
- **Authoring the HTML/CSS body, partials & engine** — the base layout,
  partials, `@page` headers/footers, styling, engine selection →
  [reference/authoring-and-styling.md](reference/authoring-and-styling.md)
- **Transactional documents** (invoice, delivery note, order confirmation,
  credit note) — mandatory content per document type + industry-specific rules →
  [reference/document-types.md](reference/document-types.md)
- **E-invoice compliance** (must be a legal ZUGFeRD / XRechnung / Peppol
  e-invoice) → [reference/compliance.md](reference/compliance.md)
- **Free / non-transactional documents** (letters, certificates, custom
  one-offs) → [reference/free-documents.md](reference/free-documents.md)
- **Checking, constraints, recipes** — `action='check'`, pre-flight checks,
  common pitfalls, recipes, public share link, debug payload →
  [reference/checking-and-recipes.md](reference/checking-and-recipes.md)

## Don'ts

- Don't start from an empty template — clone a scaffold or sibling.
- Don't hard-code visible text in one language — use `{{ L.key }}`.
- Don't print raw floats or ISO dates — always filter.
- Don't hand-build e-invoice XML — clone a compliant built-in (see the
  compliance reference).
- Don't rewrite the whole `html`/`css` when a `set_block` / `set_style` /
  `set_infobox` edit is enough.
