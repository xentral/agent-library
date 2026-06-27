# Layout, partials catalog & styling

Shared building blocks and styling rules for any Xentral PDF template.

## Reusable partials

Include them, passing data with `{% with %}` — do not reinvent these blocks:

| Partial | Renders | Key params |
|---------|---------|-----------|
| `_base/_partials/recipient.html.j2` | Buyer address block | `buyer`, `title`, optional `sender_line` |
| `_base/_partials/ship_to.html.j2` | Alternate shipping address | `ship`, `title` |
| `_base/_partials/contact_person.html.j2` | Contact person block | (optional) |
| `_base/_partials/info.html.j2` | Key/value metadata table | metadata fields |
| `_base/_partials/items.html.j2` | Positions / line-item table | `items`, `labels=L`, `columns=[...]` |
| `_base/_partials/totals.html.j2` | Net / VAT breakdown / gross | `items`, `totals`, `labels=L` |

`items.html.j2` `columns` keys: `pos`, `sku`, `article`, `qty`, `unit`,
`unit_price`, `vat`, `total`.

## Base layout

Templates extend the shared base:

```jinja
{% extends "_base/base.html.j2" %}
{% block content %}
  … your document …
{% endblock %}
```

## Per-page headers & footers

Use CSS `@page` margin boxes — **not** `position: fixed` / `position: running()`:

```css
@page {
  @bottom-center { content: "…"; }
  @top-right     { content: "…"; }
}
```

## Design tokens without touching CSS

Prefer `action: set_style` for font sizes and column widths so old saved
templates and the editor stay consistent. Reach into raw CSS only for layout the
tokens can't express.

## Formatting filters (always localize)

- Money: `{{ amount | money }}` (or `| float | format | replace('.', ',')`).
- Dates: `{{ data.documentDate | date }}` — respects the template `locale`
  (`locale: "de-DE"`). An unformatted ISO date in the output is a bug `check`
  flags.
- Numbers: `{{ n | number }}` (tabular figures on amounts).

## Translations

All visible strings are `{{ L.key }}`. Add/merge strings one language at a time
with `action: set_translation`; set `languages: ["de", "en"]` on the template.
Partial translations inherit from the primary language.

## Assets

`action: set_asset` adds/replaces a named image (logo, signature) referenced
from the template — keep binaries out of the HTML body.

## Accessibility / PDF variants

Tagged/accessible output (PDF/UA-1) and custom `@font-face` route through the
WeasyPrint engine; the fast default is Gotenberg/Chromium. The `engine` field
picks the renderer — only set it when you specifically need the accessible or
e-invoice path (for e-invoices see [e-invoice-compliance.md](e-invoice-compliance.md)).
