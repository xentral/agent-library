# PDF templates — authoring the HTML/CSS body & engine

## Engine structure

* **`html_css`** — HTML body + optional shared CSS. Most flexible.
  Renders via Gotenberg/Chromium by default (fast). The service switches
  to WeasyPrint automatically only for the *tagged* variants — PDF/UA-1
  and the PDF/A-*a levels (e.g. `pdf/a-3a`) — and for templates with a
  custom `@font-face`. The PDF/A-*b levels (incl. `pdf/a-3b` ZUGFeRD/
  Factur-X) stay on Gotenberg/Chromium; the PDF/A container conversion
  runs downstream via LibreOffice, so those files carry a LibreOffice
  `Producer` — expected, not a WeasyPrint render. See the renderer
  table under "Compliance & e-invoicing" for the full mapping.
  Paged media (page-break, per-page headers/footers, page numbers) via
  `@page` rules works on **both** engines — so footers/page numbers
  always go through `@page`, never a flow `<footer>`. 90% of the
  templates use this engine.
* **`libreoffice_docx`** — A `.docx` body with `{{placeholders}}` and
  table loops. Rendered via Gotenberg. Use when the customer's office
  staff want to edit the layout in Word. Slower than HTML.
* **`pdf_passthrough`** — A static PDF body, no rendering. Used for
  cover sheets, contract appendices, legal terms that never change
  shape. Pure file delivery.

The engine is fixed at create time — switching later means rebuilding
the template.

## Authoring the HTML/CSS body

The HTML body is **HTML + CSS + Jinja2**. At render time the ERP
payload is injected as `data.*` and the render service produces the PDF
(Gotenberg/Chromium by default — see the engine structure above). The
editor's "What can I do here?" drawer shows a compact version of this
content — the section below is the *author-facing* view for the agent.

### Data access

```jinja
<h1>Invoice {{ data.documentNumber }}</h1>
<p>To: {{ data.documentAddress.name }}</p>
<p>Date: {{ data.documentDate }}</p>
```

* Missing fields render as **empty**, not "undefined" — no crash.
  Still gate with `{% if %}` to avoid empty labels in the PDF.
* Field names are case-sensitive. `data.documentNumber` ≠
  `data.documentnumber`.
* Anything the HTML references MUST be in `example_data`, otherwise
  the editor preview breaks (see Constraints §3).

### Loops over line items

```jinja
<table>
  <thead>
    <tr>
      <th scope="col">Pos</th>
      <th scope="col">Article</th>
      <th scope="col">Qty</th>
      <th scope="col">Price</th>
    </tr>
  </thead>
  <tbody>
    {% for li in data.lineItems %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ li.name }}</td>
      <td>{{ li.quantity }} {{ li.unit }}</td>
      <td>{{ li.price.net.amount }} €</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

`<th scope="col|row">` is required for PDF/UA-1 conformance.

### What the V3 payload contains (document type → includes)

When a template targets a document type (Auftrag, Rechnung, Lieferschein,
…) via its `v3_endpoint`, the real-sample fetch queries the Xentral V3
API. Always send the **full include set** — otherwise fields are silently
missing from `data.*` and the template renders empty spots:

```
lineItems, lineItems.product, lineItems.customFields,
customFields, project, address, tags, activity
```

This is the complete public set, identical for every business-document
resource (`salesOrders`, `salesInvoices`, `deliveryNotes`, `offers`,
`creditNotes`, `purchaseOrders`, `proformaInvoices`, `returnOrders`).
The backend already sends it by default (`erp_samples._DEFAULT_V3_INCLUDES`).

**Hidden includes.** The V3 API additionally has includes prefixed
`__internal__` that are deliberately filtered out of the
"Allowed include(s) are …" error message — they cannot be discovered by
probing the API. Currently they exist only on `salesOrders`:

| Include | Adds to payload |
|---|---|
| `__internal__trafficLights` | `data.trafficLights` — system + custom traffic lights (`stock`, `vat`, `payment` with `unpaid`/`partiallyPaid`/`fullyPaid`, `creditLimit`, `deliveryBlock`, `addressValidation`, `production`, …) |
| `__internal__invoices` | `data.invoices` — ids of the invoices linked to the order |

The sample fetch appends these automatically
(`erp_samples._HIDDEN_V3_INCLUDES`). Sending `__internal__*` names to
resources that don't support them is harmless — they are silently
ignored, never rejected.

**Zwischenpositionen (intermediate positions) are NOT an include.**
Headings, subtotals, group totals, images and page breaks ride along
*automatically inside `lineItems`* — there is no extra include for them
and no way to switch them off. They appear as items with an `il-`
prefixed id and their own `type`; regular product positions have
`type: "product"`:

| `type` | Meaning | Extra fields |
|---|---|---|
| `product` | Regular product position | full product/price/quantity payload |
| `heading` | Group heading | `name`, `description` |
| `subtotal` | Subtotal row | `name`, `description` |
| `group_total` | Group total row | `name`, `description` |
| `image` | Image position | `name`, `description`, `image.id`, `imageWidth`, `imageHeight` |
| `page_break` | Manual page break | — |

Every loop over `data.lineItems` MUST branch on `li.type` — otherwise
intermediate rows render with empty qty/price cells, `loop.index`
counts them as positions, and totals computed in the template go wrong:

```jinja
{% set pos = namespace(n=0) %}
{% for li in data.lineItems %}
  {% if li.type == 'heading' %}
    <tr class="row-heading"><td colspan="4">{{ li.name }}</td></tr>
  {% elif li.type in ['subtotal', 'group_total'] %}
    <tr class="row-subtotal"><td colspan="4">{{ li.name }}</td></tr>
  {% elif li.type == 'page_break' %}
    <tr class="row-break" style="page-break-after: always"><td colspan="4"></td></tr>
  {% elif li.type == 'image' %}
    {# render via image.id if the template supports inline images #}
  {% else %}
    {% set pos.n = pos.n + 1 %}
    <tr>
      <td>{{ pos.n }}</td>
      <td>{{ li.name }}</td>
      <td>{{ li.quantity }} {{ li.unit }}</td>
      <td>{{ li.price.net.amount }} €</td>
    </tr>
  {% endif %}
{% endfor %}
```

The template's `example_data` SHOULD contain at least one intermediate
item per type the template handles, so the editor preview exercises
those branches.

### Conditional content

```jinja
{% if data.payment.iban %}
  <p>IBAN: {{ data.payment.iban }}</p>
{% endif %}
```

### Includes / partials (inheritance)

Built-ins inherit from a base layout and pull recurring blocks
(recipient address, info table, line items, totals) via
`{% include %}` from `_base/_partials/`:

```jinja
{% extends "_base/base.html.j2" %}
{% block content %}
  {% with buyer=data.documentAddress, title='Recipient' %}
    {% include "_base/_partials/recipient.html.j2" %}
  {% endwith %}

  {% with items=data.lineItems, labels=L,
          columns=['pos','article','qty','unit_price','vat','total'] %}
    {% include "_base/_partials/items.html.j2" %}
  {% endwith %}
{% endblock %}
```

When adjusting a built-in: override partial variables rather than
duplicating the markup, otherwise built-in updates won't reach the
custom template.

### Images & logo

Files uploaded under "Images" in the editor are exposed as
`{{ assets.NAME }}`. Use print units (`mm`), not pixels:

```html
<img src="{{ assets.logo }}"      alt="Company logo" style="width: 30mm; height: auto;">
<img src="{{ assets.signature }}" alt="Signature"    style="width: 40mm; height: auto;">
```

* **NEVER** write an image as a base64 `data:` URI straight into the HTML/CSS.
  Always store it via `set_asset(name, source)` and reference `{{ assets.NAME }}`.
  An inline base64 logo bloats the template so every later `get`/`update`/`render`
  round-trips that blob through the model context — the most common reason
  agent-driven PDF edits feel slow. Assets live separately from the HTML, so
  edits stay small and fast.
* Every `<img>` needs a non-empty `alt` (PDF/UA requirement).
* Purely decorative → `alt=""` AND `role="presentation"`.
* `{{ logo }}` is the legacy shorthand for `{{ assets.logo }}` —
  still valid, but new templates use `assets.*`.

### Custom fonts

Font assets (data URIs with a `font/` MIME, uploaded like images)
automatically become `@font-face` rules at render time — the CSS only
needs `font-family: '<asset_name>'`. Name suffixes build a family:
`brand`, `brand_bold`, `brand_italic`, `brand_bold_italic` all register
under `'brand'` with the matching weight/style. The default without
custom fonts is Liberation Sans (via the `'Helvetica'`/`'Arial'`
aliases). Always provide a fallback:
`font-family: 'brand', 'Helvetica', sans-serif;`. Do NOT hand-write
`@font-face` rules unless the customer needs special cases (e.g.
`font-weight: 300`) — hand-written rules win over the automatic ones.

### QR codes & barcodes

Helpers emit inline SVG, sharp at any zoom level:

```jinja
{# Generic QR from URL/text/JSON #}
<div style="width: 100px">{{ data.publicUrl | qr_code }}</div>

{# SEPA GiroCode — banking apps auto-fill the transfer dialog #}
{{ epc_qr(
    name=data.company.name,
    iban=data.payment.iban,
    amount=data.totals.gross.amount,
    reference=data.documentNumber
) }}

{# vCard for letterhead #}
{{ vcard_qr(name='Jane Doe', email='contact@example.com',
            org=data.company.name) }}

{# 1D barcodes: code128, code39, ean13, ean8, itf, upca, isbn13, isbn10 #}
{{ data.product.ean | barcode('ean13') }}
{{ barcode(data.documentNumber, 'code128') }}
```

EAN-13 requires exactly 12 or 13 digits — fails hard otherwise.

### Page format, header/footer, page numbers

A header or **footer that appears on EVERY page is done exclusively via
`@page` margin boxes** — `@top-*` and `@bottom-*`. This works on **both**
HTML engines: the render service translates the margin boxes into
per-page header/footer for Gotenberg/Chromium, and they are native in
WeasyPrint. This is the **one** place where per-page layout is configured:

```css
@page {
  size: A4;
  margin: 2cm 2cm 3cm 2cm;

  @top-right {
    content: "Page " counter(page) " of " counter(pages);
    font-size: 9pt;
    color: #6b7280;
  }
  @bottom-left {
    /* The CSS is rendered through the same Jinja env + `data`, so
       company fields can be interpolated directly. `\A` = line break,
       takes effect with `white-space: pre-line`. */
    content: "{{ data.company.name }} · VAT {{ data.company.vatId }}";
    font-size: 8pt;
    color: #6b7280;
    white-space: pre-line;
  }
  @bottom-right {
    content: "{% if data.company.hrb %}Reg. {{ data.company.hrb }}\A{% endif %}{% if data.company.email %}{{ data.company.email }}{% endif %}";
    font-size: 8pt;
    color: #6b7280;
    white-space: pre-line;
    text-align: right;
  }
}
```

> **NEVER** build the page footer as a flow element — a `<footer>` inside
> `{% block content %}` (or at the end of the body) is normal document
> flow and renders **exactly once at the end of the document**, not per
> page. This is the most common footer mistake in freshly generated
> templates. Footer content that must appear on every page → always the
> `@page` boxes. `{% block footer %}` is only for flow content that
> deliberately comes once after the content (e.g. a doc-code barcode).
>
> Margin-box limit: they carry text + counters only, no free HTML.
> base.css styles `@bottom-left` and `@bottom-right`, so a three-column
> footer is split across left/right.

### Page-break rules

```css
.no-break-inside { page-break-inside: avoid; }
.page-break-before { page-break-before: always; }

table tr  { page-break-inside: avoid; }
.footer   { page-break-inside: avoid; }
```

Without these, a long invoice splits mid-row or tears the footer
across two pages — the most common "looks fine with example data,
breaks in production" failure.

### Units & fixed sizes

| Prefer | Avoid |
|---|---|
| `mm`, `cm`, `pt`, `%` | `px` (printer-dependent) |
| `font-size: 9pt` | `font-size: 12px` |
| `width: 30mm` | `width: 110px` |

### Hiding decorative elements (PDF/UA)

Lines, background boxes, ornament logos get marked as PDF artifacts
so screen readers skip them:

```html
<hr class="decorative">
<div class="decorative bg-stripe" aria-hidden="true"></div>
```

### What the HTML engines CAN'T do

* No JavaScript. Inline `<script>` is ignored. Logic must live in the
  data or in CSS.
* No `position: sticky` / `position: fixed` for repeating headers/
  footers. Repeating headers/footers **always** use `@page` regions,
  never a flow `<footer>` (which renders once at the end of the doc).
* Modern flex/grid edge cases like `gap` inside tables are flaky —
  keep print layout conservative.

