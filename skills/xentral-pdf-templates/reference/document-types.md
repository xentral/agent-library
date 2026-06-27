# PDF templates — mandatory content per document type

## Mandatory content per document type

What MUST appear on the document for it to be correct (and, for invoices,
legally compliant). Most of it is **bindings to `data.*`** + labels/
translations — not free text. This is a build checklist, **not a gate**: the
gate (`action='create'`) only enforces the *decisions* (scope, e-invoice
format, language), never the content. For e-invoices the structured legal
values are carried by the embedded XML anyway — the PDF is the human-readable
view.

**Invoice / credit note** (`invoice` / `credit_note` — legally e.g. §14 UStG in DE):
* Full seller: name, address, **tax number OR VAT-ID**
* Full buyer: name, address
* **Unique, sequential** document number (`data.documentNumber`) + date (`data.date`)
* **Service/delivery date** (`data.deliveryDate` / service period) — note it even when equal to the invoice date
* Per line: quantity + description (`li.quantity`, `li.unit`, `li.name`)
* **Net amount per tax rate**, **tax rate**, **tax amount**, **gross total** (`data.totals.*`)
* On tax exemption / reverse charge / intra-EU supply: the **required note** (e.g. "reverse charge")
* Credit note also: **reference to the original invoice** (number/date); use the word only for a genuine reversal/correction
* For public-sector / Peppol recipients: **Leitweg-ID** / **buyer reference**

**Delivery note** (`delivery_note` — no tax statement):
* Recipient + **delivery address** (may differ from the invoice recipient → `ship_to`)
* Document number + date, reference to the order (`data.orderNumber`)
* Per line: quantity + description — **no prices/tax**
* Optional: weight/packages, batch/serial numbers (industry-specific, see industry rules)

**Order confirmation** (`sales_order`):
* Recipient, document number + date, customer order number/reference
* Lines with quantity, description, **prices** + totals
* Delivery/service date, payment/delivery terms

**Quote** (`offer`):
* As order confirmation, plus the quote's **validity date**
* Clearly marked as a non-binding quote

**Purchase order to supplier** (`purchase_order`):
* Your company as the buyer, supplier as the recipient
* Order number + date, lines with quantity/description/purchase price
* Delivery date + delivery address — **no e-invoice obligation on your side**

**Return / label / picking list / master sheet** (`return`, `label`, other):
* Free-form per purpose — no statutory mandatory content. Bindings + clear
  identifiers (document/customer/article number, barcode) suffice.

For ALL types: sender legal footer (`@page` footer, see above), correct
**number/date format** for the target country (`format_locale`), and complete
`example_data` so the preview exercises every branch.

## Industry-specific rules — what to add per business

These are not framework rules — they are the **domain knowledge** that
makes a template look right to the operator's customers. Always read
the tenant's `xentral_business_plan` profile (business_model,
sales_channels) before starting; that narrows down the rules below.

### Food, beverages, perishables

* **Batch / lot number** must be printed on the delivery note. Per
  line item, not just at the document level. Required by EU
  traceability law (Reg. 178/2002).
* **Best-before date (MHD)** must be visible per line item where the
  article has one. Show in the same row as the article — operators
  will scan visually.
* **Net / gross weight** on delivery notes for bulk goods. Customers
  audit weight on receipt.
* **Country of origin** for fresh produce, fish, meat — labeling
  regulations apply.
* **Cold-chain indicator** on transport documents if the goods need
  refrigeration (temperature class label).

### Pharma / medical / dental

* **Charge / lot number** on every line — same legal basis as food
  but stricter audit.
* **Expiry date** required.
* **GTIN / PZN / UDI** machine-readable barcode on the line — pharma
  customers scan into their inventory system.
* **Distributor license number** in the footer of every shipping doc.
* No discounts on prescription items on the invoice — they're
  reimbursed by insurance, not by the patient.

### B2B wholesale / industrial

* **Customer's article number** next to your own SKU. The customer
  reorders by *their* number, not yours. Two columns side by side.
* **Tax exemption note** in the footer when the buyer is VAT-exempt
  (intra-EU, third-country). Specific legal phrase per country.
* **Incoterms** prominently in the header of offer and order
  confirmation. EXW/FCA/DAP/DDP changes everything about who pays
  for what.
* **Payment terms** as a fixed phrase, not just a date. "Net 30 days
  from invoice date, 2% Skonto if paid within 10 days."
* **Order reference** (customer's PO number) on every document —
  invoices that don't quote the PO get rejected by their AP system.

### E-commerce / B2C

* **Different shipping address** must always be shown when present
  and different from the billing address — gifts, drop-off addresses,
  workplace deliveries. Default: print both blocks side by side; if
  same, print one and mark as "Bill-to and ship-to".
* **VAT breakdown** on B2C invoices is legal requirement in EU when
  the order is over the small-receipt threshold (€250 in DE).
* **Return policy** as a short footer line ("14-day right of withdrawal,
  see <link>"). Required for distance contracts.
* **Order tracking / customer-portal link** on the delivery note —
  reduces "where is my order" support tickets.

### Manufacturing / made-to-order

* **Drawing / revision number** on production orders and delivery
  notes. Engineering changes mid-order are common.
* **BOM lines** on the production order — operators on the shop floor
  read them.
* **Serial number** at delivery for traceable goods.
* **Warranty start date** explicit on the delivery note — usually
  the date of delivery, but contract may shift it.

### Configurable products / kits

* **Sub-items / kit components** indented under the parent line on
  delivery notes. Customer is shipped components, not the abstract
  kit, but needs to see the link.
* **Configuration recap** (chosen options) on the order confirmation
  and the invoice. The customer agreed to *these* options.

### Services / professional services

* **Time / unit detail** on the invoice line: "8 h × €120 = €960".
  Customers audit hours.
* **Period covered** in the document header ("Services rendered
  Mar 1 – Mar 31, 2026").
* **Project / engagement reference** prominently.

### Rentals / subscriptions

* **Rental period** (start / end / duration) per line.
* **Return reminder** as a separate block on the delivery note.
* **Late-fee schedule** referenced in the footer.

### Pos / restaurant / hospitality

* **Receipt order** — items in the order they were ordered, not
  alphabetical. Customer follows along.
* **Service charge** as a separate line, not folded into prices.
* **VAT receipt format** matches the local fiscal printer rules
  (DE: TSE signature block; AT: BMF receipt code; …).

