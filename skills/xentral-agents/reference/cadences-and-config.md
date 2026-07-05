# Cadences & the full configuration surface

Every field the Agent-Konfiguration UI exposes is also a `custom_agent_add` /
`custom_agent_update` parameter. When in doubt about which cadence an intent
maps to, call `action='agent_types'` for the machine-readable catalogue.

## Cadence catalogue — and the `when` format

Cadence is the **agent trigger type**, not a scheduling frequency. Pick by
intent.

### User-triggered (`when` stays empty)

| Cadence | What it is | Typical use |
|---|---|---|
| `manual` | Quick ad-hoc task — user clicks "run now" in the Schedule view. | One-off job on demand. |
| `form` | The recipient opens a LINK, fills a structured form; the agent processes the submission. | Return registration, supplier onboarding questionnaire, master-data update, product-data capture. |
| `chat` | The user TYPES into a chat surface; the agent replies in turn. Interactive Q&A — **not** for structured data entry. | Internal FAQ bot, helpdesk bot, pre-sales widget. |

### System-triggered (`when` carries a match expression, not a time)

| Cadence | Fires on | `when` |
|---|---|---|
| `email` | every incoming mail that matches | inbox filter / match hint, e.g. `subject:invoice` |
| `event` | an ERP data change (new sales order, delivery status flip) | the AsyncAPI event name |

### Time-based (`when` required, format per cadence — all Europe/Berlin local)

| Cadence | `when` format | Example |
|---|---|---|
| `appointment` | one-off ISO date/time; disables itself after the run | `2026-07-01T09:00` |
| `daily` | `HH:MM` | `09:00` |
| `weekly` | `MON\|TUE\|WED\|THU\|FRI\|SAT\|SUN HH:MM` | `MON 08:00` |
| `monthly` | `<1-31>. HH:MM` | `1. 09:00` |
| `quarterly` | `Q1\|Q2\|Q3\|Q4` (first day of the quarter, 09:00) | `Q1` |
| `yearly` | `DD.MM. [HH:MM]` | `01.07. 09:00` |

## Core config (all cadences)

- **`prompt`** — the system prompt / "Anweisungen". Plain text, can include
  numbered steps. Same field as the instructions box in the UI.
- **`tools`** — array of **full MCP-tool slugs** the agent may use at runtime.
  Pass the slug exactly as it appears in this server's `tools/list` — do **not**
  abbreviate. Slugs that don't match a registered tool are silently dropped at
  run time and listed under `missing` in the job timeline.
- **`model`** — model id (the default applies if omitted).
- **`temperature`** — 0.0–2.0 ("Kreativität" slider). `0.2` for strict factual
  flows, `0.7` balanced (UI default), `1.0+` for creative drafting.

### Pickable tool slugs (`annotations.agent_pickable=true`)

`xentral_copilot` (ERP read & write) · `xentral_email` · `xentral_crm` ·
`xentral_agent_jobs` · `xentral_operations_tasks` · `xentral_agents` ·
`xentral_schedules` · `xentral_business_model` · `xentral_business_skills` ·
`xentral_business_areas` · `xentral_dashboards` · `xentral_kpi` ·
`xentral_reports` · `xentral_pdf_templates` · `xentral_connections` ·
`xentral_erp_settings` · `xentral_entities` (customizing only) ·
`xentral_fileshare` · `xentral_knowledge_base`

Common tool recipes:

- **Form agent that produces a CSV** → `['xentral_copilot', 'xentral_fileshare']`
  (Co-Pilot pulls the ERP data, Fileshare drops the CSV).
- **Chat agent for customer-service questions** →
  `['xentral_copilot', 'xentral_crm', 'xentral_knowledge_base']`.
- **Briefing agent for dashboard values** →
  `['xentral_copilot', 'xentral_kpi', 'xentral_operations_tasks']`.

## Cadence-specific meta

### `form` slots — `form_meta`

```
form_meta = {
  audience: 'external' | 'internal',   # external = public link; internal = login required
  fields: [                            # ordered, max 50
    { id, label, type, placeholder?, required? },
    ...
  ]
}
```

Field types: `text`, `textarea`, `number`, `email`, `url`, `select`,
`checkbox`, `date`, `file`. Pass all fields in **one** `custom_agent_add` call —
the slot is fully configured when it returns, no UI step needed.

### `chat` slots — `chat_meta`

```
chat_meta = {
  header_name, header_color, subtitle, welcome, bubble_teaser,
  position: 'bottom-left' | 'bottom-right',
  embed_enabled: bool,
  starters: [string, ...]   # max 12
}
```

### `email` slots — `email_meta`

```
email_meta = { auto_reply: bool, match_criteria: string }
```

For `email` cadence, `when` carries the inbox filter expression, **not** a time.

## Not (yet) configurable via this tool

- **Slot-level knowledge-file binding** (UI: "Wissen — Dateien direkt als Wissen
  anhängen"). Use `xentral_fileshare` to upload + `xentral_knowledge_base` to
  register facts.
- **Form share-link / form colour.** The link is auto-generated; colour is a
  UI-only convenience not persisted in `form_meta`.
