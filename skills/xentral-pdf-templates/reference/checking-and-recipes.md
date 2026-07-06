# PDF templates — checking, constraints, recipes

## Checking a template (`action='check'`)

Before you report a template done — and especially for any invoice, credit
note or other Geschäftsbrief — run `action='check'`. It is a read-only
"doctor": no writes, no side effects, safe anytime. It returns a JSON report of
findings grouped by severity (`error` / `warning` / `info`), each with a `fix`
hint. This is the structured counterpart to the in-editor "Schnellprüfung"
button, callable directly by the agent.

What it inspects (a broad linter — non-exhaustive):

* **Structure & engine** — `document_type` binding (so live data and the
  real-document picker resolve), empty / renders-empty body, and whether a
  declared e-invoice tag is actually configured (PDF/A-3 + embedded XML).
* **Translations & i18n** — for *every* shipped language it resolves each
  `L.*` key and flags: keys that are empty (print blank), keys missing in a
  language so it falls back to the default-language text (e.g. German leaking
  into the English PDF), and dead translation keys nothing references.
* **Number & date formatting / locale** — raw `{{ data.date }}` / amount fields
  printed without `| date` / `| money` / `| number` (would show the ISO string
  or an unformatted number), plus format-locale problems (automatic / invalid /
  language ↔ format-locale mismatch).
* **Assets & fonts** — referenced-but-missing assets, unused assets, the default
  font, fonts declared but never used.
* **Data binding & known gotchas** — `data.*` fields used but absent from
  `example_data`; the `data.items` → `dict.items()` collision (use
  `data['items']`); `background-clip:text` gradient text (invisible in print).
* **Hygiene / PDF-UA** — image `alt`, table `scope`, exactly one `<h1>`,
  tabular-aligned amounts, plus **language-code validity**: every explicit
  language value (the `languages` field, translation keys, a literal
  `<html lang="…">` or `{% set _LANG %}`) must be a valid BCP-47/ISO-639 code.
  A country code used as a language — the classic `us` / `at` / `ch` — is
  flagged (`language_country_code`): it yields an invalid PDF `/Lang` (PDF/UA
  error) and never matches at runtime, so translations silently fall back. Word
  forms / POSIX underscores (`englisch`, `de_DE`) trip `language_malformed`.
  Runtime `data.language` is *not* your concern — the base template normalizes
  it (see [building-and-editing](building-and-editing.md)).
* **Mandatory content & legal disclosures.** Pass `legal_form`
  (`gmbh` | `ag` | `ohg_kg` | `ek`) to check the Geschäftsbrief requirements
  (company name + legal form, registered office, register court + number,
  managing directors / board — §35a GmbHG / §125a HGB) plus the per-document-type
  required fields (for invoices and credit notes the §14 UStG essentials:
  issuer + recipient, number, date, time of supply, per-rate VAT, VAT ID / tax
  number). `check_content=true` adds the deeper content-compliance layer; `industry`
  (`food` | `electronics` | `pharma`) adds batch / serial / best-before rules.

### Live pass — judge the REAL output

Pass `live=true` (or a specific `sample_doc_id`) to additionally render a
**real** Beleg from the instance — via the template's `v3_endpoint`, most recent
document when no id is given — and inspect the actual page: dates normalised to
the document locale, and identifiers that are present in the data but missing
from the rendered page. This catches "renders fine, but the customer number
never shows" — things a static check can't see. Automatically skipped for
templates without a `v3_endpoint`.

Typical loop: `create` / `set_block` → `check legal_form=gmbh` → fix findings →
`check live=true` → `render output=image` to eyeball the layout → done.

## Constraints & invariants

1. **One document type per template.** Don't try to make one template
   handle both invoices and credit notes. The data shapes differ in
   subtle ways (sign of amounts, fixed phrases) and you will hit edge
   cases later. Make two.

2. **Templates are scoped to one instance.** Copying a template to
   another instance is an explicit operation (read + create with new
   `instance_id`). There is no shared template pool. Each instance
   owns its visual identity.

3. **The example data is part of the contract.** If the template
   relies on a field, that field MUST be in `example_data` so the
   editor preview renders meaningfully. Otherwise the next operator
   to open the template sees a broken preview and panics.

4. **Renderings must be idempotent.** Same input → same output bytes
   (within timestamp tolerance). No randomness, no clock-dependent
   layout. Otherwise audit and share-link caching break.

5. **A `share_token` is mandatory — and a public secret.** PDF
   shares require a non-empty token to activate; activation without
   a token is rejected by the backend with `400` (unlike dashboards,
   forms, and chat, where the token is optional). Reason: the public
   endpoint can render a live Xentral document for a caller-supplied
   `doc_id` — without the token gate, an attacker could enumerate
   documents via `/{share_id}/{1..N}`. Anyone with URL + token can
   render the document; treat token rotation as a security action —
   when an end customer's relationship ends, rotate.

## Public share link

A template can expose a public, login-free render URL per instance —
the typical use case is "view your invoice" emails to end customers.
Enable it in the editor under "Öffentlicher Link" → the backend
mints a one-time `share_id` (12 URL-safe chars, 72 bits of entropy)
→ URL `/public/pdf/{share_id}?token=…` renders live.

### What gets rendered

| URL form | Behaviour |
|---|---|
| `/public/pdf/{share_id}?token=…` | Renders the template with the **example data**. Used for static legal appendices and demo links. |
| `/public/pdf/{share_id}/{doc_id}?token=…` | Fetches the Xentral document at `doc_id` from the template's `v3_endpoint` **live** and renders with it. The caller picks the doc id — this is why the token gate is mandatory. |

A PDF share without a configured `v3_endpoint` always renders example
data, regardless of whether a `doc_id` is supplied.

### Token (mandatory)

The token is passed as `?token=…`, max 128 chars, constant-time
comparison. **Activating without a token is rejected with `400`** —
a PDF share cannot be link-only because that would enable document
enumeration. Token rotation changes the token without invalidating
the `share_id`; the URL keeps working with the new token while the
old one stops working.

All failures — unknown `share_id`, wrong token, deactivated share,
non-existent doc id — map to an identical `404` so a share's
existence (and the existence of any doc id behind it) stays opaque
to anonymous callers.

### Rotation and deactivation

Rotate the `share_id` when the audience changes or a token leak is
suspected (the URL changes; all recipients have to be re-notified).
Token-only rotation rotates just the secret while the URL stays
stable — the milder variant.

Deactivating without deleting also works (`is_active: false`); the
public endpoint then returns `404` until reactivated. `share_id` +
token are preserved.

### Auth context inside the render

Public renders run under a synthetic `AuthUser`
(`user_id="pdf-public-share"`), with no real JWT. Instance isolation
happens via `share_id` resolution: token + share_id match exactly
one instance; the backend sets `license_id` from the share record, not
from any caller-supplied header. There is therefore no path through
a public link into another instance.

## Capture the last payload (debug)

For debugging you can briefly cache and inspect a template's **last
rendered data** — the exact `data` dict that went into the render engine.
Useful when a template renders wrong and you want to see what actually
arrived (Xentral fetch, deep-merge result, or a headless POST body).

Everything the editor's "Letzte Payload (Test)" box does in the technical
settings is available to you via the tool:

| Action | Tool call |
|---|---|
| **Enable** capture | `set_debug_capture(name=…, enabled=true)` |
| **Disable** capture | `set_debug_capture(name=…, enabled=false)` |
| **Read** the last payload | `last_payload(name=…)` |
| **Clear** the payload | `clear_payload(name=…)` |

Properties — deliberately minimal and privacy-conscious:

* **Opt-in.** Capture only runs while the flag is on. The flag is
  **persistent per template** (survives reloads) and independent of any
  public share — so it also works for built-in templates and without a
  public link.
* **Latest only.** Each capture overwrites the previous one.
* **Fires in two places:** the in-editor live-Beleg preview
  (`source: "internal"`) **and** public-share calls (`source: "GET"` /
  `"POST"`).
* **Held only briefly in Redis, nowhere else.** Short TTL (~10 min), then
  Redis evicts it on its own. The payload never reaches persistent
  storage. Without Redis, `last_payload` is simply empty.
* **Size cap.** Above ~256 KB the `data` is dropped and only the marker
  `truncated: true` plus the metadata is stored.

The `last_payload` result carries metadata alongside `data`:
`captured_at`, `source`, `doc_id`, `resource`, `v3_endpoint`, `bytes`,
`truncated`, and `render_ok` / `render_error` (the latter only on rendered
paths; for `source: "internal"` it is a fetch with no render outcome).

**Typical flow:** `set_debug_capture(name, enabled=true)` → render once
(pick a live Beleg in the preview or call the public link) → inspect with
`last_payload(name)` → for sensitive data, `clear_payload(name)` and
optionally `set_debug_capture(name, enabled=false)`.

## Pre-flight checks (before write)

Always run these before any change to a live template:

1. **Read the existing template** first — never blind-overwrite. The
   editor's "example data" you'd lose may be carrying a real-world
   payload that took someone an hour to capture.
2. **Check `v3_endpoint`** — does this template render the entity
   type the user thinks? A template wired to `/sales_orders` won't
   render an invoice.
3. **Verify all referenced data paths** are in the example payload.
   `{{customer.iban}}` only works if the example has a customer with
   an iban.
4. **Compliance attachment** — if the template has Factur-X /
   ZUGFeRD configured, validate the XML against the sample data
   (`validateCompliance` API) before saving.
5. **Try a real ERP sample** — the editor's "real samples" picker
   pulls 20 recent entities. Pick one and render. A template that
   looks fine with example data and crashes with `belege/123456`
   will crash in production.

## Common pitfalls

| Pitfall | Why it breaks |
|---|---|
| Hardcoding company address in HTML | Template stops working when the instance moves. Put it in `example_data.company` or read from the ERP setup. |
| Forgetting page-break rules | Long invoices split mid-row, addresses end up on the wrong page. Set `page-break-inside: avoid` on table rows and footer blocks. |
| Using fixed pixel sizes | Looks fine on one printer, breaks on another. Stick to `mm`, `pt`, `%`. |
| Inline `<script>` for "smart" things | Weasyprint doesn't run JS. Logic must happen *before* render (in the data) or in CSS. |
| Same template used for invoice and credit note | The arithmetic differs (negative amounts shown how?), legal phrases differ. Split. |
| Localized labels in HTML strings | Operators in DE need DE, in EN need EN. Use the template's locale switch or per-instance overrides. |
| Compliance XML drifts from PDF | Operator changes the invoice amount in HTML but the embedded XML still has the old amount. Tax authority rejects. Always regenerate the XML from the same source data. |
| `{{ data.items }}` (dotted) | Jinja resolves `.items` to the dict method, not your line-items key → 500. Use `data['items']` (subscript). |
| `background-clip: text` (gradient text) | Not painted by the print pipeline → the text renders invisible. Use a solid `color:` instead. |
| `<img>` without `alt` under PDF/UA | The accessible-PDF pipeline drops images that lack alt text → they print empty. Always add `alt="…"` (decorative: `alt="" role="presentation"`). |
| Full-bleed / dark background via `@page { background }` | Chromium (Gotenberg) doesn't paint `@page` backgrounds. Use `@page { margin: 0 }` + a full-size `body`/wrapper background instead. |
| Logo via `set_asset` "did nothing" | It DID persist — `get` returns it under `asset_names`. Reference it as `{{ assets.logo }}`. Pass logos through the `assets` map on create/update (not only inline). |

## Recipes (common flows)

1. **New template from a built-in.** Open the picker → choose
   "Delivery note" / "Invoice" / "Offer" → optionally pick a style
   variant → confirm. The template lands editable in the editor with
   an `example_data` payload ready to render.

2. **Clone an existing template.** Read source template → call create
   with a new `name` and the existing `html`/`css`/`example_data`.
   Rename inside the editor afterwards. (Useful for a "draft" version
   while the production one stays untouched.)

3. **AI-rebuild from a reference PDF.** Upload a PDF in the picker →
   "Eigenes Beispiel". The wizard streams an iterative reconstruction
   (3 LLM passes ~60-90s). The result is an editable HTML/CSS
   template — refine via chat.

4. **DOCX flow.** Create template with engine=`libreoffice_docx` →
   upload `.docx` body → the editor exposes a "Download → edit in
   Word → re-upload" cycle. Placeholders use the standard `{{ }}`
   syntax. Test with a real sample after each upload.

5. **Static legal appendix.** Create template with engine=
   `pdf_passthrough` → upload the static PDF. Use this for terms,
   privacy notice, conformity declaration. Cheaper than rebuilding
   in HTML.

6. **Public share link.** In the editor, share tab → enable → copy
   URL. The URL renders the template with whatever entity id is
   appended. Rotate the share id when the audience changes.

