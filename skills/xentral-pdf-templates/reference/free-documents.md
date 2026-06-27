# Free / non-transactional documents — letters, certificates, one-offs

Documents **without a line-item table**: cover letters, dunning letters,
certificates, terms (AGB), custom one-offs. Clone **`letter_blank`** (or a
sibling like `agb_template`, `customer_sheet`).

## What's different from transactional documents

- **No positions/totals partials.** You usually need only the recipient block
  and free body content.
- **Body is free prose**, often driven by infoboxes so the text is editable
  without touching HTML.
- **Still localize**: visible text via `{{ L.key }}`, dates via `| date`.

## Typical build

1. Clone `letter_blank`.
2. Recipient: `recipient.html.j2` (`buyer`, `title`) — or a sender line for a
   pure letter.
3. Body: write the content in `{% block content %}`, or — better for text that
   business users will tweak — put it in an **infobox**:
   - `action: set_infobox` with placement `intro_top` / `outro_bottom` /
     `header_all` / `footer_all` / `watermark` / `stamp`. Content may use Jinja,
     so you can still interpolate `{{ data.* }}`.
4. Style + `@page` header/footer as needed — see
   [partials-and-styling.md](partials-and-styling.md).
5. `check` then `render` against real data.

## When a document is *almost* line-item

If it has a small table but isn't an ERP transactional document (e.g. a packing
checklist, a pick list), you can still use `items.html.j2` with a custom
`columns` set, or write a plain HTML table. Reach for
[transactional-documents.md](transactional-documents.md) only when it is bound
to an ERP record (invoice/order/delivery/credit note).
