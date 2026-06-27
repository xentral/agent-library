# Transactional documents — invoices, delivery notes, orders, credit notes

Documents bound to an ERP record with **line items**. Clone `document_blank` (or
the closest sibling such as `xentral_classic_rechnung`) and adapt.

## Structure (top → bottom)

1. **Recipient address** — `recipient.html.j2` partial (`buyer`, `title`).
2. **Info table** — document number, date, customer number, your reference —
   `info.html.j2`.
3. **Optional alternate shipping address** — `ship_to.html.j2` (`ship`).
4. **Positions table** — `items.html.j2` (see columns below).
5. **Totals** — net / VAT breakdown / gross — `totals.html.j2`.
6. **Payment / footer** — terms, IBAN, due date (only where the document type
   needs them — bind explicitly, e.g. `{{ data.payment.iban }}`).

See [partials-and-styling.md](partials-and-styling.md) for the full partial
catalog and how to include them.

## Positions table

```jinja
{% with items=items, labels=L, columns=['pos','article','qty','unit_price','vat','total'] %}
  {% include "_base/_partials/items.html.j2" %}
{% endwith %}
```

Valid `columns` keys: `pos`, `sku`, `article`, `qty`, `unit`, `unit_price`,
`vat`, `total`. Choose the set per document type — a delivery note typically
drops price columns (`pos`, `article`, `qty`, `unit`); an invoice keeps them.

## Totals & VAT

```jinja
{% with items=items, totals=totals, labels=L %}
  {% include "_base/_partials/totals.html.j2" %}
{% endwith %}
```

Group VAT by rate when you render your own breakdown:

```jinja
{% for rate, group in items | groupby('effectiveTaxRate') %}
  {{ rate }}%: {{ (group | sum(attribute='taxAmount')) | money }}
{% endfor %}
```

Always filter money: `{{ amount | money }}` (or
`{{ amount | float | format | replace('.', ',') }}`). Never print raw floats.

## Document type binding

On `create`, set/derive `document_type` (invoice, delivery_note, sales_order,
offer, credit_note) — from the explicit field, the `v3_endpoint` hint
(e.g. `/api/v3/invoices/{id}?include=all` → `invoice`), or the template name.
The tool does not enforce the data shape; you are responsible for binding the
right fields. Use `set_debug_capture` + `last_payload` to see the exact dict a
real document feeds in.

## Per-document-type notes

- **Invoice** — needs payment terms, IBAN, due date, and (DACH) §14 UStG
  mandatory fields; if it must be a legal e-invoice, see
  [e-invoice-compliance.md](e-invoice-compliance.md).
- **Delivery note** — no prices; may need batch/serial/weight columns; alternate
  ship-to common.
- **Order confirmation / offer** — validity date, delivery date; offer often
  carries intro/outro infoboxes.
- **Credit note** — mirrors the invoice; negative or absolute amounts per your
  data; reference the original invoice number in the info table.
