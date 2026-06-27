---
name: xentral-pdf-templates
description: >
  How to design and edit Xentral PDF business documents — invoices, delivery
  notes, offers, order confirmations, credit notes, letters — with the
  `xentral_pdf_templates` MCP tool. Covers the Jinja2 + HTML/CSS model, the
  reusable layout partials, the blank scaffolds, money/date/locale formatting,
  per-page headers/footers, and e-invoice compliance (ZUGFeRD / XRechnung /
  Peppol). Use this whenever the user wants to create, restyle, or fix a PDF
  document template in Xentral.
---

# Building Xentral PDF documents (Belege)

The `xentral_pdf_templates` tool is a **plain rendering engine**: Jinja2 +
HTML/CSS in, PDF out. It does **not** know what an invoice should look like —
that knowledge lives here. Always start from a scaffold or an existing
template; never hand-write a full document structure from memory.

## First moves

1. `action: help` — the live manual for the current tool version. Read it once
   per session; flags and field names below may evolve.
2. `action: list` — see built-in + custom templates. Clone the closest match
   instead of starting empty.
3. `action: get` with an `id` — pull a template's `html`, `css`,
   `example_data`, and metadata so you can see the real shape before editing.

The two blank scaffolds are your starting points:

- **`document_blank`** — line-item document (invoice, order, delivery note,
  offer, credit note): address block, info table, positions table, totals,
  payment details. Clone this for anything with line items.
- **`letter_blank`** — free-form letter, no positions table.

## The templating model

- **Jinja2** with chainable-undefined: a missing `data.a.b.c` renders empty
  rather than erroring — do not wrap every access in `if`.
- **HTML + CSS**, intentionally neutral in the scaffolds; you restyle via CSS.
- **Per-page headers/footers** use CSS `@page` margin boxes
  (`@bottom-center`, `@top-right`, …), **not** `position: fixed`.
- The base layout is extended: `{% extends "_base/base.html.j2" %}` then
  `{% block content %}…{% endblock %}`.

### Reuse the partials — do not reinvent these blocks

Include them; pass the data in with `{% with %}`:

| Partial | Renders | Key params |
|---------|---------|-----------|
| `_base/_partials/recipient.html.j2` | Buyer address block | `buyer`, `title` |
| `_base/_partials/ship_to.html.j2` | Alternate shipping address | `ship`, `title` |
| `_base/_partials/info.html.j2` | Key/value metadata table | metadata fields |
| `_base/_partials/items.html.j2` | Positions / line-item table | `items`, `labels=L`, `columns` |
| `_base/_partials/totals.html.j2` | Net / VAT breakdown / gross | `items`, `totals`, `labels=L` |

```jinja
{% with items=items, labels=L, columns=['pos','article','qty','unit_price','vat','total'] %}
  {% include "_base/_partials/items.html.j2" %}
{% endwith %}
```
Valid `columns` keys: `pos`, `sku`, `article`, `qty`, `unit`, `unit_price`,
`vat`, `total`.

### Formatting — always localize

- Money: `{{ amount | money }}` (or `| float | format | replace('.', ',')`).
  Never print raw floats.
- Dates: `{{ data.documentDate | date }}` — respects the template `locale`.
  An unformatted ISO date in the output is a bug; the `check` action flags it.
- Numbers: `{{ n | number }}` (tabular figures on amounts).
- UI strings come from translations as `{{ L.key }}` — never hard-code visible
  words in one language. Add strings with `action: set_translation` (one
  language per call); set `languages: ["de", "en"]` and `locale: "de-DE"` on
  the template.

## Editing surgically

Prefer the narrow actions over rewriting `html`/`css` wholesale:

- `set_block` — replace one layout block (footer, items region) only.
- `set_style` — design tokens (font sizes, column widths) without touching CSS.
- `set_asset` — add/replace a named image (logo, signature).
- `set_infobox` — a placeable text box (`intro_top`, `outro_bottom`,
  `header_all`, `footer_all`, `watermark`, `stamp`); content may use Jinja.
- Versioning: `list_versions` / `get_version` / `restore_version` — every write
  is undoable, so iterate freely.

Every write is **validate-or-reject**: a broken template is refused, not saved.

## Verify before declaring done

- `action: check` — static hygiene (unformatted dates, untranslated vars,
  missing assets) plus optional **live render against a real document** and
  e-invoice XML validation. Run it after edits.
- `action: render` — produce the PDF (or a PNG preview / base64) with real or
  example data. **Verify against real ERP data, not only the hand-written
  `example_data`** — example data hides date/number/locale bugs.
- Debugging data binding: `set_debug_capture` on, render once, then
  `last_payload` shows the exact dict the template received.

## E-invoice compliance (legally critical — keep it in the tool, not in prose)

For ZUGFeRD / XRechnung / Peppol, **clone the matching built-in**
(`invoice_zugferd_en16931`, `invoice_peppol_bis_v3`, country variants) — it
carries the correct `compliance_policy` (embedded XML + PDF/A-3a). Do not try
to assemble e-invoice XML by hand. Pass the `compliance` tag on `create` so the
policy is derived automatically, and run `check` to validate the XML against
EN 16931. For German invoices, `check` can also verify §14 UStG mandatory
fields.

## Don'ts

- Don't start from an empty template — clone a scaffold or sibling.
- Don't hard-code visible text in one language — use `{{ L.key }}`.
- Don't print raw floats or ISO dates — always filter.
- Don't hand-build e-invoice XML — clone a compliant built-in.
- Don't rewrite the whole `html`/`css` when a `set_block` / `set_style` /
  `set_infobox` edit is enough.
