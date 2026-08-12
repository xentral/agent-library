# Fileshare — recipes, pre-flight, pitfalls

Read this when you are about to act on a file and want the shape of the flow, or
when something did not behave as expected.

## Pre-flight

- **Always `list` before a per-file action.** Guessing a `file_key` from a filename
  is the single most common failure here. Filenames collide; keys do not.
- **Before `upload` of structured data, check it parses.** A malformed CSV
  uploaded silently is worse than no file: the next agent or import trusts it.
- **Before `delete`, say the name and size out loud.** See rule 3 in `SKILL.md`.
- **Before reading a table, ask whether you need the contents or a figure.** A
  figure means `xentral_datasets`; contents mean `read`.

## Recipes

### 1 · The user attached a file to their message

You already hold the `file_key` (`source='chat'`). Do not `list`, do not ask for
an upload.

- Prose, small (a contract clause, a config, a log excerpt) → `read` it.
- CSV / TSV, or any question about counts, sums or duplicates →
  `xentral_datasets(action='import_analyze', file_key=…)`, then follow the guided
  import in the datasets skill.
- Something you cannot read (xlsx, an archive) → say what it is, and offer the
  route: a CSV export, or a workflow that processes it.

### 2 · "Was liegt bei mir?" — overview

- `xentral_fileshare(action='list')`
- Summarise by `source` and `mime_type`; name the newest handful. Do not dump the
  raw list — the user asked what they have, not for JSON.

### 3 · Sanity-check a file before triggering an import

- `list` with the likely `tags` or `source`
- Newest match → `metadata` (name, size, type). `read` only if it is small and you
  actually need the bytes.
- Confirm with the user that this is the file they mean, then hand the `file_key`
  to the downstream tool.

### 4 · Drop an artifact you produced

- `upload` with `filename` (dated, e.g. `cleanup_2026-05-17.csv`), the body in
  `content`, a `description` saying what it is, and `tags` so it is findable later.
- Tell the user it is in the Datenaustausch and how to recognise it. A file the
  user cannot find again did not help them.

### 5 · Inbound email attachment

- `xentral_fileshare(action='list', source='inbox')`
- `metadata` to confirm which one, then `read` if it is text-extractable, else
  point at the UI.

### 6 · Remove an obsolete file

- `list` (filtered) → identify candidates → repeat filename, size and
  `uploaded_at` back to the user → `delete` only on explicit consent.

## Pitfalls

| Pitfall | Why it hurts |
|---|---|
| Reading a 5 MB CSV | Over the inline cap: you get metadata and no content. Profile it with `import_analyze` instead of reporting failure. |
| Answering a "how many / how much" from a sample or the first lines | The figure is wrong and sounds precise. Only `import_analyze` (every row) or SQL over an imported table can answer it. |
| Asking the user to upload a file they attached | It is already stored; you hold the key. This is the fastest way to look broken. |
| `content` for binary data | Stored as text → the download is corrupt. Use `content_b64`. |
| Reusing a filename instead of the `file_key` | Filenames collide, keys do not. |
| Uploading without `tags` | Nobody finds it later, including you on the next turn. |
| Treating the store as ERP data | Files do not appear in customer histories. Linking to a customer is a Correspondence entry via `xentral_erp_core`. |
| Deleting to "clean up" without being asked | Irreversible, and not your call. |

## Out of scope

- **Diffs and version history** — none exist. Suggest dated filenames.
- **Folders** — the store is flat; `tags` are the grouping mechanism.
- **Cross-tenant sharing** — files belong to one tenant, full stop.
- **Long-term archival** — this is *working* storage. Records belong in the ERP.
- **Streaming downloads** — the UI does that; `read` returns bytes inline and is
  the wrong tool for a huge file.
