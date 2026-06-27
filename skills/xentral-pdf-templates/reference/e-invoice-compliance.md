# E-invoice compliance — ZUGFeRD / XRechnung / Peppol

Legally critical. The deterministic XML generation + validation lives in the
**tool**, not in prose — your job is to wire a template to the right policy, not
to assemble e-invoice XML by hand.

## Golden rule

**Clone a compliant built-in. Never hand-build the XML.**

- ZUGFeRD / Factur-X (EN 16931): clone `invoice_zugferd_en16931`.
- Peppol BIS 3: clone `invoice_peppol_bis_v3`.
- Country variants: `invoice_belgium`, `invoice_italy_fattura`,
  `invoice_swiss_qr`, …

These carry the correct `compliance_policy` (embedded XML + PDF/A-3a). Cloning
inherits it; starting from `document_blank` does not.

## On create

Pass the `compliance` tag (e.g. `"zugferd"`) so the policy is derived
automatically. If you create from a non-compliant base, the policy will be
missing and `check` will warn that the template claims an e-invoice format
without a configured policy.

## Validate before done

- `action: check` validates the produced e-invoice XML against the **EN 16931**
  profile and reports mandatory-field gaps.
- For German invoices, `check` can also verify **§14 UStG** mandatory fields and
  Geschäftsbrief disclosures (register court, tax ID, managing directors).

## Engine / format

E-invoices render as **PDF/A-3a** with the XML embedded. The engine selection
and the `compliance_policy` come from the cloned built-in — don't override the
engine unless you know the target profile. PDF/UA-1 (accessible) is a separate
concern handled by the WeasyPrint path; see
[partials-and-styling.md](partials-and-styling.md).

## What you still author

The **visual** invoice (layout, branding, line items, totals) is normal
template work — see [transactional-documents.md](transactional-documents.md).
The compliance layer rides underneath it via the policy; the human-readable PDF
and the embedded XML describe the same document, so keep the bound data
consistent across both.
