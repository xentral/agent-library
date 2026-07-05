# The library prefill, create recipes, naming & anti-patterns

## How a library item maps onto `custom_agent_add`

A `library/agents/*.json` item is a **prefill** — a tested starting point, not a
finished slot. Its shape maps field-for-field onto `custom_agent_add`:

| Library item | `custom_agent_add` param |
|---|---|
| `prefill.agent_type` | `cadence` |
| `prefill.tools` | `tools` |
| `prefill.model` | `model` |
| `prefill.temperature` | `temperature` |
| `locales.<lng>.prefill.name` | `agent` (the display title) |
| `locales.<lng>.prefill.area` | `area` |
| `locales.<lng>.prefill.description` | `note` |
| `locales.<lng>.prefill.instructions` | `prompt` |
| `locales.<lng>.prefill.form_meta` | `form_meta` |

So the flow is: pick the closest library item → read its prefill in the user's
language → adapt the instructions and fields to the instance → call
`custom_agent_add` with the mapped params. Hand-write a prompt from scratch only
when no library item is close.

## Naming the `agent` field

When `custom_agent_add` defines a NEW agent (the slot carries its own `prompt`),
`agent` is the **display title** shown in the sidebar, schedule view and slot
list. Use a short, capitalised, human-readable label in the user's language —
`Produktdaten erfassen`, `Lieferanten-Onboarding`, `Tägliches Verkaufs-Briefing`.

**Never** pass `snake_case`, `kebab-case`, lowercase slugs or technical ids
here — the UI renders the string verbatim. Slug form is only correct when
assigning a slot to a **built-in** agent listed by `action='list'`; then the
slug must match exactly.

## Recipes

### First agent enable
- Read `business_model.profile` — routing and defaults key off `business_model`,
  `automation`, `tone`.
- List candidates filtered by plan + category. Recommend one to start
  (often a return/refund form for B2C, an inbox handler for finance-heavy).
- Explain each setting in plain language; keep the confidence gate high
  (0.85+) for the first weeks.
- Save, then tell the operator where to monitor jobs.

### Settings tune
- Read the current slot.
- Read the last ~20 jobs of this agent — note the confidence distribution and
  any `requires_intervention` pattern.
- Propose threshold / trigger / prompt changes with one-line justifications,
  then save. Remember the `slot_id` changes after the update.

### Health audit
- List enabled agents. For each, count jobs in the last 30 days by status.
  High `error` rate = a bug; high `requires_intervention` = a config/prompt
  problem; low overall count = under-utilisation.
- Produce a short report with actionable suggestions.

### Retry a bad job
- Read the job's `originalRequest` and the timeline / error.
- Config issue → fix settings, then retry. Malformed input → don't retry
  blindly; confirm or fix the input with the operator first.

## Anti-patterns

- Building a `manual` slot when the user wants a form → use `form` +
  `form_meta.fields`.
- Passing `agent='product_data_capture'`-style slugs for a custom agent → use a
  proper title.
- Telling the user "fields must be configured in the UI" → pass `form_meta`
  directly.
- Dropping a CSV into Fileshare and calling it a "form template" → Fileshare is
  file storage, not a fillable UI. For recipient-fillable forms create a `form`
  cadence agent.
- Conflating `chat` (interactive Q&A) with `form` (structured one-shot
  submission).

## Constraints & invariants

- **Settings are per-instance.** No global override; the catalog default is the
  only fallback. Agents never act across instances.
- **Confidence gates auto-action, not auto-creation.** Below threshold the agent
  still creates a `requires_intervention` job — never throw the work away.
- **Retry preserves context** — the original request + previous timeline are
  passed back; don't restart from scratch.
- **Agents must not silently mutate config** (Business Model, Business Skills). They
  write a task/job for the operator instead.
- Slot data lives in its own namespace (`custom_agents/<license>/agents.*`),
  decoupled from the business model.
