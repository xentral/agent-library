# CSV import — reference

Loaded on demand from `SKILL.md`. Covers the failure mode the flow is built
around, warning semantics, probe and cleanup mechanics, and the quirks real
customer exports contain.

## The failure mode this flow exists for

A real customer export omitted one field on 95.6% of its rows and padded the line
end with an empty field. Every row therefore still carried the header's field
count, and every CSV parser accepted the file without complaint.

But each value sat one column to the left of its label:

```
header:  … ;Kundennummer;Typ        ;Firmenname ;Strasse    ;PLZ  ;Ort    ;Land ;Telefon
row:     … ;            Kunde      ;Acme GmbH  ;Hauptstr. 1;10115;Berlin ;DE   ;+49 30 …  ;
                        ^ Typ         ^ Firmenname            ^ PLZ  ^ Ort   ^ Land  ^ Telefon
```

A positional import writes company names into `type`, postal codes into `street`,
and phone numbers into `country`. Nothing downstream can detect it: every value is
a valid string, every row has the right arity, no constraint is violated. The
customer discovers it weeks later when a report is wrong.

**This is why analysis precedes loading, and why a probe precedes the full run.**
Neither step is ceremony.

## Detection is by value domain, not position

The analyser classifies each column's values into a signature — `email`, `phone`,
`iso_country`, `zip`, `date`, `money`, `percent`, `url`, `integer` — and compares
it against what the *header* implies. When several columns independently contradict
their own header but match a neighbour's at the same offset, that is a shift.

In the example above: `Land` holds phone numbers, `Ort` holds country codes, `PLZ`
holds city names. Three independent columns agreeing on offset 1 is evidence; one
odd column is not, and does not raise a warning.

## Warning semantics

| Code | Meaning | How to treat it |
|---|---|---|
| `column_shift` | Values are offset against the header. | **Stop.** Report it and get an explicit decision. Fixing the export is nearly always right. |
| `ragged_rows` | Some rows have a different field count. | Report the count. Short rows import as empty, long rows are truncated. |
| `empty_columns` | Columns with no data at all. | Mention it; usually harmless, sometimes a sign the wrong export was run. |

A `column_shift` warning blocks the import. Overriding it is possible but must be
a deliberate, stated choice — never a default and never silent.

## What the analysis returns

Per column: normalized name, verbatim source header, position, fill count,
distinct count, max length, signature, up to five example values. Plus the
detected delimiter and encoding, and the row count.

A few KB regardless of file size. **The bulk data is never returned**, which is
what keeps cost bounded, makes hallucinated cell values impossible, and keeps
personal data out of the transcript.

## Column naming

Headers are folded to SQL-safe names: lowercased, umlauts transliterated
(`Straße` → `strasse`), everything else collapsed to underscores.

```
"Externe Nummer (lead_id)"       → externe_nummer_lead_id
"Top-Opp Wahrsch. %"             → top_opp_wahrsch
"Opportunity-Wert gesamt (EUR)"  → opportunity_wert_gesamt_eur
```

Duplicate headers are suffixed (`name`, `name_2`), empty or non-alphabetic ones get
positional names (`col_4`). **No column is ever dropped** — records are copied
positionally, so losing one would shift everything after it.

## Writing rows yourself: rows_bulk

When you already hold the data — you generated it, or you cleaned a file locally —
`rows_bulk` is the write path. One COPY per call instead of one round trip per row.

```json
{
  "action": "rows_bulk",
  "dataset": "crm_import",
  "table": "leads",
  "column_names": ["sku", "menge", "preis", "aktiv", "angelegt"],
  "rows": [
    ["A-1", "5",  "1.50",  "true",  "2026-01-12"],
    ["A-2", "12", "99.99", "false", "2026-02-01"]
  ]
}
```

Positional, not a list of objects. Repeating the keys on every row roughly doubles
what you have to emit — measured on a 5235-row export mapped to 12 columns: 523k
tokens as objects, 293k as arrays.

Rules worth knowing before you build a payload:

- **Strings are fine.** Values are coerced per column type, so `"5"` into an
  `integer` and `"2026-01-12"` into a `date` both work. A value that cannot convert
  is an error naming the column and the value.
- **A batch is atomic.** One bad row and none of that batch lands. Fix and resend
  the batch; nothing is half-written.
- **`null` stays NULL** — not an empty string.
- **Max 500 rows per call.** Send batches in sequence.
- **System columns are refused.** `id`, `created_at`, `updated_at` are managed.
- **Width is checked.** Every row must have exactly one value per `column_names`
  entry; a short row is an error, not a padded row.

### When to stop using it

Every value is model output. Rough sizes for a 12-column table:

| rows | output tokens |
|---|---|
| 100 | 6k |
| 500 | 30k |
| 2000 | 118k |
| 5235 | 293k |

Up to a few hundred rows this is comfortable. Past about a thousand, upload the
cleaned file to Fileshare and use the CSV import instead — the data then never
passes through you, and the server does one COPY over the whole file.

## Which set can be imported into

`import` creates a table, and creating a table is DDL. The store allows an agent
DDL only on objects it **owns** and that are still `draft` — ownership is by
principal, so "draft" alone is not enough. Importing into a set the customer
created is refused:

```
agents may only add tables to their own draft datasets (this one is draft)
```

The set was draft; it failed purely on ownership. So create the set for the import
yourself and load into that. Two ways to hand it over afterwards:

- Tell the customer where it landed and let them activate it in the app; or
- `query` the staged table and `insert` the rows into a table of theirs — no DDL
  on their object, so this is allowed.

This is the rule working as designed rather than an obstacle: imported raw data is
unvalidated, and keeping it in a set you own means a human decides when it becomes
real.

## Probe and full run

The probe loads the first N rows (default 5) into a **separate** probe table, not
the target table.

Separate on purpose: loading 5 rows into the real table and later appending the
rest makes "were the probe rows imported twice?" unanswerable. A distinct probe
table keeps the answer trivial — it is dropped, and the full run starts clean.

Re-probing is cheap: the probe table is dropped and rewritten each time. Loop as
often as the mapping needs.

## Session cleanup

A guided import creates several artifacts: the uploaded file, the probe table, the
target table, sometimes workflows. All of them carry one `import_session` id, so
they can be dealt with together rather than one by one.

Rules:

- **Explicit only.** Cleanup never runs on a timer, and never as a side effect of
  an error. A failed import is precisely when the customer needs to see what was
  written.
- **Ask, don't assume.** Recurring imports keep their table and workflow; one-offs
  leave nothing. Both are correct outcomes.
- **Partial failure is reported.** If one artifact cannot be removed, the rest
  still are, and the response says what remains, per artifact, with the reason.
- **Idempotent.** Running cleanup twice is safe; an artifact that is already gone
  counts as removed.

### What an agent may actually remove

`session_cleanup` performs a **hard delete**, and agents are locked out of hard
deletes by the store — every artifact comes back `failed` with
`DatasetForbidden: agents cannot hard-delete; archive instead`.

The caller's identity is what decides this: a human admin acting through the app
cleans up completely; an agent does not. The service passes the real actor rather
than assuming system privileges, so the refusal is deliberate.

Practical routes for an agent:

- **Archive instead.** Imported tables are created as `draft`, and archiving your
  own draft is allowed and reversible. This is usually what "undo the import"
  should mean anyway.
- **Hand it back.** Report which artifacts remain and let the customer remove them
  in the app.

Workflow artifacts are reported as `unsupported` for an unrelated reason: cleanup
has no way to remove them yet. Either way, do not present a cleanup as complete
when the response says it is not.

If the customer wants to keep the data but drop the scaffolding, that is a normal
request — keep the target table, archive the probe table, delete the uploaded file.

## Raw mode

Every column becomes `text`; names are normalized from the header. Practically
cannot fail.

This is the right default. Typing a customer's export at load time means guessing,
and a wrong guess *rejects rows*. Getting the data into a queryable table first
turns every subsequent problem into a SQL problem:

```sql
-- inspect before committing to types
SELECT angelegt_am, count(*) FROM t_abc GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

-- German dates and currency, converted in place
SELECT to_date(angelegt_am, 'DD.MM.YY')                              AS created,
       replace(replace(wert, '.', ''), ' €', '')::numeric            AS value
FROM   t_abc
WHERE  angelegt_am ~ '^\d{2}\.\d{2}\.\d{2}$';
```

Blank cells import as SQL `NULL`, not empty string — collapsing the two would
break `IS NULL` filters on every imported table.

## Not yet available: typed mode

A mapping document with per-column types, transforms and per-row validation is
designed but not implemented. **Do not offer it.** The honest answer today is that
everything lands as `text` and the shaping happens in SQL — which is also faster
than negotiating a mapping.

## Things real exports do

Recognise these from the analysis and mention them:

- **Sentinel dates.** `01.01.99` for "happened, date unknown". Import as `NULL`,
  not as 1999.
- **`-` as a null placeholder.** Common in exports from reporting tools.
- **Non-breaking spaces.** `Hauptstraße  4` — from pasting through Excel.
  Breaks every exact-match join until stripped.
- **Excel-mangled numbers.** `9,72E+11` was once an order number or a phone
  number. **Not recoverable** — the original digits are gone. Say so plainly and
  ask for a re-export with the column formatted as text.
- **UTF-8 BOM.** Handled automatically, but it is why the first header sometimes
  looks like `﻿Name` elsewhere.
- **Semicolon delimiters with decimal commas.** German exports. Delimiter sniffing
  scores by field-count consistency rather than character frequency for exactly
  this reason.

## Size

The import parses the file in memory to profile it, so there is an upper bound
(50 MB by default). Beyond that, ask for the file split — a larger limit would
only move the failure.
