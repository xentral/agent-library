# App anatomy, design patterns & guardrails

## Anatomy of an app

```
{
  "slug": "warehouse-scan",        // snake_case, unique per instance
  "name": "Warehouse Scan",
  "summary": "Stock in/out by scan.",
  "category": "logistics",          // custom | logistics | production | finance | sales
  "category_label": "Logistics",
  "accent": "#6D7CFF",
  "platform": "mobile",             // "mobile" | "web" (Desktop)
  "linked_entities": ["Product", "DeliveryNote"],
  "form": {
    "home": "s_home",               // ID of the start screen
    "screens": [ ... ]
  },
  "files": [ ... ]                  // optional docs/rule files (yaml, python)
}
```

### Screens (`form.screens`)

```
{
  "id": "s_home",
  "name": "Goods receipt",
  "type": "screen",        // "screen" (in menu) or "dialog" (modal, not in menu)
  "inMenu": true,
  "components": [ ... ]
}
```

Exactly **one** screen is `home`. `dialog` screens don't appear in the menu and
are opened from a button action.

### Minimal example

```
"form": {
  "home": "s_home",
  "screens": [{
    "id": "s_home",
    "name": "Goods receipt",
    "type": "screen",
    "inMenu": true,
    "components": [
      { "id": "c1", "type": "heading", "props": { "text": "Goods receipt" } },
      { "id": "c2", "type": "section", "props": { "text": "Scan" }, "children": [
        { "id": "c3", "type": "formfield", "props": { "label": "Item barcode", "fieldType": "text", "dataSource": "Product" } },
        { "id": "c4", "type": "formfield", "props": { "label": "Quantity", "fieldType": "number" } },
        { "id": "c5", "type": "button", "props": { "text": "Book in", "variant": "primary", "action": "tool:book_in" } }
      ]},
      { "id": "c6", "type": "table", "props": { "label": "Recent bookings", "columns": "Item, Qty, Time", "dataSource": "DeliveryNote" } }
    ]
  }]
}
```

## Mobile vs. Desktop

- **Mobile** (`platform: "mobile"`) — scanners and on the go (warehouse, pick,
  field sales). Narrow screens, large tap targets, single column, live preview
  to a phone via QR.
- **Desktop** (`platform: "web"`) — tables and analyses on screen (commission
  settlement, overviews).

The platform can be changed later.

## Designing good UIs

Patterns that make an app read as professional rather than a form dump:

- **One job per screen.** A screen answers one question or completes one task.
  Split the rest into more screens (in the menu) or a `dialog` reached by a
  button. One clear primary `button` per screen.
- **Group, don't pile.** Wrap related fields in a titled `section` or `box`. Use
  `row` / `grid` for things that belong side by side; default vertical flow for
  reading order.
- **Lead with the headline number, then the list.** `kpibox` (bound via
  `kpiKey`) for the metric that matters, then a `table` (bound via `dataSource`)
  for detail. Don't show a raw table where one number would do.
- **Bind to real data.** Prefer `dataSource` / `kpiKey` / `agent` over static
  text — that's what makes the app live instead of a mockup.
- **State at a glance.** `statusbadge` for a record's state, `timeline` for a
  sequence, `opstasks` to surface what needs attention.
- **Agents where free text beats a form.** `chatagent` for open questions
  ("which supplier is cheapest for X?"); `formagent` for structured intake an
  agent then processes. A short chat often replaces three fields.
- **Actions belong together.** Put a screen's buttons in an `actionbar`
  (right-aligned by default) instead of scattering them.

## Guardrails

- `slug` is snake_case (`^[a-z][a-z0-9_-]{2,127}$`), unique per instance, and must
  not collide with a built-in template slug.
- `linked_entities` reference only the **global entity catalogue**: Customer,
  Supplier, Product, User, SalesOrder, SalesInvoice, DeliveryNote, PurchaseOrder,
  BillOfMaterials, CostCenter.
- A table's `dataSource` points at an entity key; `columns` are the display
  columns.
- Apps start as a **draft** (`enabled: false`) — invisible to the team until
  `set_enabled`.
- Validation is advisory, not blocking — same freedom as the designer UI.

## Out of scope

Studio renders surfaces and wires actions. The actual business logic behind a
`tool:<name>` button (what happens on click) is an MCP tool you define
separately — not in the screen JSON.
