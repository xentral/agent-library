# PDF templates — building & editing

## Building a new template: structure first, then skin

A template has two layers. Keep them separate in your head — it is the single
biggest lever for building many different-looking documents reliably:

* **Structure** — the page frame (`{% extends "_base/base.html.j2" %}`), the
  regions (`<section data-box="...">`), the shared partials (items / recipient /
  totals), the data binding and the `{{ L.key }}` translations. This is proven
  and reusable; you should NOT re-derive it.
* **Skin** — the template's own `css`. It cascades after `base.css` and can
  override every default. This is where a document gets its look. A new look is
  new css, nothing more.

**Two-step workflow for a brand-new template:**

1. **Classify the document, then clone a structure starter:**
   * Line-item document — invoice, order, delivery note, offer, credit note;
     anything with a positions table → clone **`document_blank`**.
   * Free-form letter — cover letter, reminder, notice; no positions →
     clone **`letter_blank`**.

   Clone = `get` the starter, then `create` with its html as the starting point.
   The starter already wires up the full structure, so you start from a
   complete, correct skeleton instead of a blank page.

2. **Skin it** — design the look ONLY in the `css`. Start from the starter's
   neutral skin and restyle: set design tokens in `:root` (`--fs-*`, `--col-*`)
   via `set_style` first, then add per-region rules. **Do not copy a
   fully-styled built-in's css to "adapt" it** — you end up fighting an existing
   look instead of building yours.

> Editing an instance's **existing** template is different: `get` that template and
> tweak it in place — skip the classify/clone step.

### Scope first: one recipient vs a group vs all

Before gathering evidence, **ask the scope** (the gate surfaces it as a `scope`
decision dimension for invoices) — it changes what you do. It applies to both
customer documents (invoice, delivery note, offer) and supplier documents
(purchase order): "one supplier vs all suppliers" is the same question.

* **One named recipient** (a specific customer or supplier — "an invoice for
  customer X", "a PO for supplier Y"): do **not** run a usage analysis. Resolve
  that record (via the Co-Pilot) and read it — country, language,
  USt-IdNr./Leitweg-ID — which determines language, locale and whether an
  e-invoice format is required. Confirm, then create. (A one-off document needs
  no template — just `render`.)
* **A customer/supplier group, or all of them (a default template)**: run
  `action='survey'` with `analyze=true`. It returns the inventory plus a `usage`
  block (languages, countries, currency, derived locale + translations the
  instance's real documents needed) and, for invoices, a `usage.compliance`
  e-invoice recommendation.

  **Then SHOW the user what you found before building** — especially the
  languages: "Your documents over the last 12 months were DE 156 / EN 4 → I'll
  ship DE + EN; correct?" Let them confirm, correct, or add a missing language.
  Only after that confirmation create the template with the agreed
  `languages` + `format_locale`. The point is the user gets to react to the
  real data, not just accept a silent guess.

### E-invoice: the default for B2B invoices (opt-out allowed)

Don't wait for the user to say "ZUGFeRD". For invoices, `create` returns
`needs_clarification` until the e-invoice format is decided — for B2B this is
effectively mandatory, so raise it proactively rather than skipping it. Confirm
the format (use the survey's `usage.compliance` recommendation or the recipient's
record), then create with the chosen `compliance`. The user **may decline** —
choose `none` (or pass `force`) — that's a valid answer, just make it a conscious
one. Pass `document_type` on `create` when the name is ambiguous so the template
binds to the right type instead of the generic default.

Passing an e-invoice format in `compliance` (e.g. `zugferd-en16931`) now also
**configures the real policy** (PDF/A-3 + embedded XML) — not just a label; the
editor will show it as configured. To add e-invoice to an *existing* template,
`update` with `compliance_policy` (or the format). And set **`format_locale`**
(BCP-47, e.g. `de-DE`, `de-CH`) from the survey's `usage.derived.locale_candidates`
so money/number/date formatting matches the market — it's a real field, not just
a display hint.

### Structure contract (what the starters give you)

* **Page frame:** `{% extends "_base/base.html.j2" %}` provides only the page
  skeleton — `<head>`, locale resolution, `@page` margins and the footer
  margin-boxes. It imposes **no** page number and **no** visible header. Fill
  `{% block content %}`; override `{% block footer %}` only for a custom in-body
  footer.
* **Document language (`<html lang>` → PDF `/Lang`):** the base template owns
  this. `data.language` arrives **raw from the ERP** (country codes, words:
  `us`, `at`, `englisch`, …) and is **not** a valid BCP-47 tag — the base runs
  it through the `bcp47` filter to a real tag (`de-DE`/`en-GB`/`fr-FR`/`nl-NL`/
  `it-IT`, fallback `de-DE`) so PDF/UA validators accept `/Lang`. **Never write
  `data.language` into a `lang=` attribute yourself**, and don't hand-roll a
  `<head>`; if you truly must, use `{{ data.language | bcp47 }}`, never the raw
  value.
* **Header (letterhead):** the starter carries a **visible** `{% block letterhead %}`
  (logo via `assets.logo` + company block). It is THE header — edit it in place;
  **never draw a second header inside `{% block content %}`** (that's the classic
  doubled-header bug). For no header, override the block empty.
* **Page number:** lives in the **footer** (the starter's css `@page @bottom-center`)
  — exactly one, never top-right. Don't add another.
* **Regions** are `<section>` elements with `data-box="<key>"` and a
  `.box-<key>` class — `base.css` styles them, your css restyles them, and
  `set_block` can target them. Keys: `recipient, info, subject, intro, items,
  totals, payment, notes, signature, shipping, contact-person, ship-to, body`.
* **Partials** — include with `{% with ... %}{% include "_base/_partials/<p>.html.j2" %}{% endwith %}`:
  * `items.html.j2` — positions table. Pass `items`, `labels=L`, `columns=[...]`.
    Column keys: `pos | sku | article | qty | unit | unit_price | vat | total`
    (order matters; the 6-col set matches `base.css` default widths).
  * `recipient.html.j2` — address block. Pass `buyer`, `title`, optional `sender_line`.
  * `totals.html.j2` — net / VAT-breakdown / gross. Pass `items`, `totals`, `labels=L`.
  * `ship_to.html.j2`, `contact_person.html.j2` — optional blocks.
* **Text** is `{{ L.key }}`, maintained per language with `set_translation`
  (never an inline `_ALL_LANG` dict).

## Editing: safe + granular (use these, not full rewrites)

Editing is **validate-or-reject**: every change is test-rendered before it is
saved. If it doesn't render, **nothing is persisted** — you get the render
error back; read it, fix the cause, retry. The previous working template stays
intact, so you can always recover. Never assume a change "took" without the
ok result.

Prefer **targeted** edits over rewriting the whole HTML/CSS:

* **One region → `set_block`.** Regions are addressable as `<!-- box:NAME -->`
  comment blocks, as HTML elements carrying `data-box="NAME"` (this is how the
  shipped document templates are built — e.g. `<section data-box="info">…</section>`;
  `set_block` replaces the element's **inner** content, keeping the wrapper/class)
  **or** as Jinja `{% block NAME %}` (header = `letterhead`,
  `footer`, `content` included; the override is auto-created if the template
  still inherits the base). `list_blocks` shows what's there, `get_block`
  reads one, `set_block` replaces **only** that region — so editing the items
  table can never disturb the footer. Standard names: header, info, recipient,
  ship-to, items, totals, footer, contact.
  Bespoke templates **without** markers (hand-authored HTML, no `data-box` tags):
  `list_blocks` auto-derives the regions from **unique container classes** — every
  one-off class on a block element (e.g. `bl-items`, `bl-subject`, `bl-foot`) becomes
  addressable, while repeated utility classes (`num`, `bl-foot-col`) are skipped. So
  the original boxes stay editable without hand-tagging.
  `list_blocks` returns a `previews` text snippet per block — use it to map a user's
  intent ("top-right box") onto the right name (e.g. `bl-info`) in one shot, instead
  of opening every block with `get_block`.
* **Fonts / line height / positions-table column widths → `set_style`** (design
  tokens), NOT a full CSS rewrite. Tokens: `fs-body, lh-body, fs-h1, fs-h2, fs-h3,
  fs-table, col-pos, col-qty, col-unit-price, col-vat, col-total`. Example
  "make the body bigger": `set_style({"fs-body": "11pt"})`. Avoids the
  error-prone hand-editing of `nth-child` column widths.
* **Logo / image → `set_asset(name, source)`** (a `data:` URI or http(s) URL),
  referenced as `{{ assets.NAME }}`. Adds/replaces one asset without touching
  html/css; other assets are preserved.
* **Document strings / translations → `set_translation(lang, translations)`.**
  The UI strings (`doc_title`, `col_qty`, `net_total` …) live structured in the
  `translations` field and are injected at render time as `{{ L.key }}` — no
  longer an `_ALL_LANG` dict in the HTML. Merge one language per call. Values
  may be strings, nested objects (`L.sec.scope`) or lists of pairs
  (`L.reasons`). Mirrors the business sidebar's "Translations" table.
* **Custom info boxes → `set_infobox(infobox_key, …)` / `list_infoboxes` /
  `delete_infobox`.** Placeable text blocks: `placement` = `intro_top` (top),
  `outro_bottom` (bottom), `footer_all` (every page footer), `header_all`
  (every page header). `content`/`box_title` are `{lang: text}` and may contain
  Jinja (`{{ data.iban }}`). Validate-or-reject with rollback.
* **Whole body / new layout → `update` (with `html`, and/or `css`)** — still
  available for big changes; also validate-or-reject. (On the in-app Co-Pilot
  surface these are the separate ops `update_html` / `update_css`; via the
  `xentral_pdf_templates` MCP tool there is ONE `update` action that takes `html`
  and/or `css` — there is no `update_html`/`update_css` action here.)

These apply to BOTH surfaces — the in-app Co-Pilot tools and the
`xentral_pdf_templates` MCP actions (`list_blocks` / `get_block` / `set_block`
/ `set_style` / `set_asset` / `set_translation` / `list_infoboxes` /
`set_infobox` / `delete_infobox`).

### Few round-trips (each call costs)

Every tool call is a round-trip. Keep them low — this is the biggest speed
lever, not the system:

* **Smallest tool first:** `set_style` (tokens) → `set_block` (one region) →
  `update` with `css` ONLY (html untouched) → full `update` of `html` only as a
  last resort. Re-sending the whole template on every tweak is the main reason
  edits feel slow.
* **Verify — two levels, depending on the change:**
  * *Does it render at all?* → `render` + `output='metadata'` (just
    `{filename, size_bytes}`, the cheapest check).
  * *Does it look right?* → `render` + `output='image'` — rasterizes the pages
    to PNG previews you can actually **SEE**. **Mandatory after any visual
    change, before you report done:** check orientation, column layout,
    barcode/QR sizes, overflow, page count — and if it's wrong, fix and
    re-check.
  * `output='url'` and `output='base64'` give you a **PDF**, which the model
    CANNOT view (base64 is gibberish text, a URL you can't open). They're for
    handing to a human, **not** for self-verification. To look, always use
    `output='image'`.
  * *Is the e-invoice / compliance config set?* → `get` returns
    `compliance_policy` (the executable contract: `pdf_variant` + attachment
    metadata, distinct from the descriptive `compliance` tag). A non-null
    `compliance_policy` with the expected `pdf_variant` and `factur-x.xml`
    attachment confirms it — no render byte-check needed.
* **Batch related edits, THEN render once** — not after every micro-step.
* **Don't `get` what you just wrote** — you already know its content.

### Consistent numbers & dates (don't mix formats)

Always format through the filters — never emit raw values, and **never set a
per-call locale**. The template's locale applies globally, so every value is
formatted uniformly:

* amounts → `{{ x | money }}`
* quantities / plain numbers → `{{ x | number }}`
* dates → `{{ x | date }}`

To change the format everywhere, change the template locale once — not each
number.

This also applies inside `rows` tuples and `{% with %}`/`{% set %}` blocks
(e.g. `(L.invoice_date, data.documentDate | date)`) — the shared partials
print values verbatim, they do **not** format for you.

**Do not hand-roll a date macro.** A `format_date` macro that does
`date_str.split('.')` only reformats dot-separated `dd.mm.yyyy` input — but
real ERP data arrives as ISO `YYYY-MM-DD`, so the split yields one part and the
macro silently prints the raw ISO string. It looks correct in the preview only
because the hand-written `example_data` happens to use dot-formatted dates.
`{{ x | date }}` (Babel) parses ISO and localizes correctly — always use it.

### Free-form by design

Templates do **not** require document fields. The only gate is "it renders".
Price lists, catalogs, reports etc. are fine — leave out recipient/items/totals
and build your own layout (wrap your own regions in `<!-- box:NAME -->` to keep
them addressable). For a non-letter layout, override `{% block letterhead %}{% endblock %}`
empty (or don't extend the base) to drop the default header.

## Concepts & terminology

| Term | Meaning |
|---|---|
| Template | The recipe (engine + body + style) that turns data into a PDF. |
| Engine | `html_css` (default, renders via Gotenberg/Chromium; the service switches to WeasyPrint only for tagged variants — PDF/UA-1, PDF/A-*a — and custom fonts), `libreoffice_docx`, `pdf_passthrough`. Picks the renderer. |
| Body | The actual `index.html` (for HTML/CSS) or the binary `.docx` / `.pdf` (for the other engines). |
| Example data | A JSON payload bundled with the template — used in the editor's preview and as a fallback when render data is missing. |
| Render | One execution: combine template + data → PDF bytes. Not stored, just returned. |
| Render storage | Separate concept: opt-in archive of a render in S3, keyed by instance + template + entity id. |
| Share | A public, token-protected URL that renders the template with a chosen entity's data — used for "view your invoice" customer links. |
| Compliance attachment | XML payload bundled into the PDF (Factur-X / ZUGFeRD / XRechnung) so the file is both human-readable and machine-readable. |
| v3 endpoint | The Xentral REST endpoint the template's "real samples" picker queries (e.g. `/api/v2/sales_orders`). Defines which entity type the template renders. |

