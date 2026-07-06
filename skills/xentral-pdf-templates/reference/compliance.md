# PDF templates — compliance & e-invoicing

## Configuring compliance & e-invoicing

The status pill **"Compliance & e-invoicing — not configured"** in
the editor means the template has an empty `compliance_policy` block
(no PDF/A profile, no XML attachments, no XMP claims). When the user
needs an e-invoice or the template must be archival, fill it in here.

### The `compliance_policy` schema

```yaml
compliance_policy:
  pdf_variant: pdf/a-3a              # container profile, see below
  xmp:
    pdfuaid_part: 1                  # also claim PDF/UA-1
  attachments:
    - filename: factur-x.xml
      mime: text/xml
      relationship: Alternative      # Alternative | Source | Data | Supplement | Unspecified
      description: Factur-X invoice (EN 16931 BASIC)
      content_template: |
        <?xml version="1.0" encoding="UTF-8"?>
        ...                           # Jinja template, same `data` source as the HTML
```

`pdf_variant` values:

| Value | Purpose |
|---|---|
| _empty_ | Plain PDF, no claim. |
| `pdf/a-2b` | GoBD archive (delivery notes, dunning letters, internal docs). |
| `pdf/a-3a` | Archive + allows attachments **and** tagging (e-invoice to B2C, government). |
| `pdf/a-3b` | Archive + attachments without tagging (classic ZUGFeRD B2B invoice). |
| `pdf/ua-1` | Accessibility only, no archive claim. |

### Use-case picker

The editor shows a radio list instead of raw ISO names. Each pick
maps 1:1 to the structure above:

| Use case | `pdf_variant` | `xmp.pdfuaid_part` | Attachment |
|---|---|---|---|
| Standard | _empty_ | — | — |
| Archive | `pdf/a-2b` | — | — |
| E-invoice B2B (DE) | `pdf/a-3b` | — | `factur-x.xml` (ZUGFeRD/Factur-X) |
| E-invoice B2C / authorities (DE) | `pdf/a-3a` | `1` | `factur-x.xml` |
| Peppol (NL / EU) | `pdf/a-3a` | `1` | `peppol-invoice.xml` (UBL) |
| Accessible government publication | `pdf/ua-1` | — | — |

Anything that doesn't fit this matrix shows up as "Custom" and the
advanced block opens automatically.

### Which renderer each variant uses

The compliance variant — not just the `engine` field — decides which
engine actually rasterises your HTML/CSS. This matters because CSS
support differs between engines. The render service resolves it like so:

| Variant / condition | HTML→PDF engine (build your CSS against this) | Notes |
|---|---|---|
| _empty_ (plain PDF) | requested engine — **Gotenberg/Chromium** by default | |
| `pdf/a-1b`, `pdf/a-2b`, `pdf/a-3b` | **Gotenberg/Chromium** | PDF/A container conversion runs downstream via **LibreOffice**, so the file's `Producer` reads "LibreOffice" — expected, not a WeasyPrint render. |
| `pdf/a-3a` (and any tagged `*a` level) | **WeasyPrint** | Only WeasyPrint emits the tagged structure tree PDF/A-*a requires. |
| `pdf/ua-1` | **WeasyPrint** | Same — tagged/accessible output. |
| `engine='weasyprint'` chosen explicitly | **WeasyPrint** | Covers every variant. |
| template uses a custom `@font-face` | **WeasyPrint** | Forced regardless of variant — Gotenberg's `@font-face` loading is racy. |

Practical takeaway: a classic ZUGFeRD B2B invoice (`pdf/a-3b` +
`factur-x.xml`) renders on **Gotenberg/Chromium**, so author against
Chromium's CSS quirks (e.g. `@page` backgrounds aren't painted), even
though the finished file is stamped with a LibreOffice `Producer`.

### Profile URN — which phrase where

The profile URN sits inside the XML attachment and decides whether
the tax authority accepts the file as EN-16931-conformant:

| Profile | URN | EN-16931? |
|---|---|---|
| Factur-X MINIMUM | `urn:factur-x.eu:1p0:minimum` | no (warning only) |
| Factur-X BASIC WL | `urn:factur-x.eu:1p0:basicwl` | no (warning only) |
| Factur-X BASIC | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:basic` | **yes** |
| Factur-X EXTENDED | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended` | yes |
| XRechnung 3.0 | `urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0` | yes |
| Peppol BIS 3.0 | `urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0` | yes |
| NLCIUS 1.0 | `urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0` | yes |

For the German B2B e-invoicing mandate (effective 2025-01-01) pick
BASIC or higher. MINIMUM/BASIC WL are non-conformant and trigger a
warning from the sanity check.

### Example: Factur-X / ZUGFeRD EN 16931 BASIC

Complete `content_template` for the "E-invoice B2B" and "E-invoice
B2C" use cases — Jinja against the same `data` payload as the HTML
body. Amounts come from `data.totals.*` and `data.lineItems[].*`;
**do not** recompute them in the XML (otherwise the XML drifts from
what is visible — the most common compliance failure).

```jinja
<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">

  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:basic</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>

  <rsm:ExchangedDocument>
    <ram:ID>{{ data.documentNumber }}</ram:ID>
    <!-- 380 = Commercial invoice (UNTDID 1001) -->
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">{{ data.documentDate|replace('-','') }}</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>

  <rsm:SupplyChainTradeTransaction>
    {% for li in data.lineItems %}
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument>
        <ram:LineID>{{ loop.index }}</ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedTradeProduct>
        <ram:SellerAssignedID>{{ li.number }}</ram:SellerAssignedID>
        <ram:Name>{{ li.name }}</ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice>
          <ram:ChargeAmount>{{ li.price.net.amount }}</ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <!-- C62 = "one" / piece (UN/ECE Rec 20) -->
        <ram:BilledQuantity unitCode="C62">{{ li.quantity }}</ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <!-- S = Standard rate (UNTDID 5305) -->
          <ram:CategoryCode>S</ram:CategoryCode>
          <ram:RateApplicablePercent>{{ li.effectiveTaxRate }}</ram:RateApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>{{ li.lineItemRevenue.net.amount }}</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
    {% endfor %}

    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>{{ data.company.name }}</ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>DE</ram:CountryID>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration>
          <!-- VA = VAT registration number (UNTDID 1153) -->
          <ram:ID schemeID="VA">{{ data.company.vatId }}</ram:ID>
        </ram:SpecifiedTaxRegistration>
        <ram:SpecifiedTaxRegistration>
          <!-- FC = Fiscal / tax number -->
          <ram:ID schemeID="FC">{{ data.company.taxId }}</ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>{{ data.documentAddress.name }}</ram:Name>
        <ram:PostalTradeAddress>
          <ram:PostcodeCode>{{ data.documentAddress.zipCode }}</ram:PostcodeCode>
          <ram:LineOne>{{ data.documentAddress.street }}</ram:LineOne>
          <ram:CityName>{{ data.documentAddress.city }}</ram:CityName>
          <ram:CountryID>{{ data.documentAddress.country }}</ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>

    <ram:ApplicableHeaderTradeDelivery>
      <ram:ActualDeliverySupplyChainEvent>
        <ram:OccurrenceDateTime>
          <udt:DateTimeString format="102">{{ (data.serviceDate or data.documentDate)|replace('-','') }}</udt:DateTimeString>
        </ram:OccurrenceDateTime>
      </ram:ActualDeliverySupplyChainEvent>
    </ram:ApplicableHeaderTradeDelivery>

    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      {% set vat_amount = (data.totals.gross.amount|float) - (data.totals.net.amount|float) %}
      <ram:ApplicableTradeTax>
        <ram:CalculatedAmount>{{ '%.2f' % vat_amount }}</ram:CalculatedAmount>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:BasisAmount>{{ data.totals.net.amount }}</ram:BasisAmount>
        <ram:CategoryCode>S</ram:CategoryCode>
        <ram:RateApplicablePercent>{{ data.financials.tax.taxRates.standard }}</ram:RateApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>{{ data.totals.net.amount }}</ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount>{{ data.totals.net.amount }}</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">{{ '%.2f' % vat_amount }}</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>{{ data.totals.gross.amount }}</ram:GrandTotalAmount>
        <ram:DuePayableAmount>{{ data.totals.gross.amount }}</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
```

### Example: Peppol BIS 3.0 (UBL) — header skeleton

Different XML family (UBL instead of CII), same EN-16931 business
terms:

```jinja
<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>{{ data.documentNumber }}</cbc:ID>
  <cbc:IssueDate>{{ data.documentDate }}</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>

  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>{{ data.company.name }}</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>{{ data.company.vatId }}</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>

  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>{{ data.documentAddress.name }}</cbc:Name></cac:PartyName>
    </cac:Party>
  </cac:AccountingCustomerParty>

  <cac:LegalMonetaryTotal>
    <cbc:TaxInclusiveAmount currencyID="EUR">{{ data.totals.gross.amount }}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount     currencyID="EUR">{{ data.totals.gross.amount }}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>
```

### Sanity check ("Schnellprüfung")

The "Schnellprüfung" button in the compliance block calls the backend
`validateCompliance` API. This is **not** a full KoSIT / EN-16931
conformity check — it's a sanity check:

* XML is well-formed (lxml parse).
* Profile URN is present and known.
* EN-16931 BASIC mandatory fields exist — invoice number (BT-1),
  type code (BT-3), issue date (BT-2), seller name (BT-27), seller
  VAT ID (BT-31), buyer name (BT-44), currency (BT-5), grand total
  (BT-112), amount due (BT-115).

Severity:

* `error` → blocks save or flags an audit warning. Examples:
  malformed XML, missing mandatory BT.
* `warning` → save allowed, but flagged in red. Examples: unknown
  profile URN, MINIMUM / BASIC-WL profile (not EN-16931-conformant
  for the German mandate).

Run the sanity check before saving any compliance template — see
pre-flight check §4.

### Common compliance pitfalls

| Mistake | Consequence |
|---|---|
| HTML amounts edited but XML rendered from stale source | Tax authority rejects — XML and PDF show different totals. **Always render from the same `data` object**. |
| `pdf_variant: pdf/a-3a` without `xmp.pdfuaid_part: 1` for B2C / authorities | BFSG / EAA accessibility requirement (effective 2025-06-28) not met. |
| Factur-X XML as `attachment` without a matching `pdf_variant` (e.g. plain PDF) | File is human-readable but not a valid archival container — no GoBD archivability. |
| Profile URN MINIMUM or BASIC WL for the DE B2B mandate | Flagged as warning by the sanity check — recipient AP system rejects. |
| Multiple attachments with the same `filename` | XMP index breaks — most readers only open the first one. |
| `position: absolute` (web `.sr-only`) on a `<caption>` / table part | WeasyPrint emits empty `/Table` structure nodes (one deep chain per real table) → PDF/UA structure-tree warning. Hide in flow instead — see authoring-and-styling.md "Visually hiding text". |

