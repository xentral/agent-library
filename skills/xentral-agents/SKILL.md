---
name: xentral-agents
description: >
  Pick, configure, and schedule the AI workers that act inside a Xentral instance
  with the `xentral_agents` tool. Covers when an agent beats a workflow, the
  cadence/trigger model (manual, form, chat, email, event, and the time-based
  schedules), starting from the agent library instead of a blank prompt, the
  full configuration surface (prompt, tools, model, form/chat/email meta), and
  public form/chat shares. Use when the user wants to enable, create, tune, or
  schedule a background agent — a return-intake form, a helpdesk chat bot, a
  daily sales briefing, an inbox handler — not to run a single task once (that's
  the Co-Pilot) or to define a brand-new agent type in code.
examples:
  - "Add a public form so customers can submit a delivery-address change."
  - "Set up a daily 09:00 sales briefing agent."
  - "Turn on a helpdesk chat bot embedded on our website."
---

# Xentral agents

## Purpose

An **agent** is a focused LLM worker bound to a **trigger**: it wakes on an
event (incoming mail, a scheduled tick, a submitted form, a chat turn, an ERP
change), uses MCP tools, writes outcomes back, and leaves a job record. The
`xentral_agents` tool lists the agents available in an instance and manages their
**custom-agent calendar slots** — the per-instance configuration of *which* agent
runs, *when*, and *how*.

What it is **not**:

- It is **not the Co-Pilot.** The Co-Pilot is the user-facing chat; agents are
  background workers. To run one task once ("refund THIS order"), use the
  Co-Pilot, not an agent.
- It is **not a workflow.** A workflow is a deterministic step list; an agent
  decides at runtime based on content. See the split below.
- It is **not where you define new agent *types*.** A new flavour (a WhatsApp
  refund handler, a custom DATEV exporter) is a code change, not a config — flag
  and route it.

## Agent vs. workflow — pick the right layer

| If the decision is… | Build a… |
|---|---|
| **Always the same** ("every day at 09:00 cancel unpaid prepayment orders") | **workflow** (`xentral_workflows`) — deterministic, auditable, idempotent |
| **Dependent on the content** (classify a mail, route a request, draft a reply) | **agent** (`xentral_agents`) — the LLM decides each run |

If you can explain it as "step 1, then step 2, then …" → workflow. If the right
answer depends on what came in → agent.

## Cadence IS the trigger type

The single most important choice is `cadence` — it is **not** "how often it
runs", it is **what kind of agent** this is. Picking the wrong cadence builds
the wrong agent. When the user describes intent in plain words, call
**`action='agent_types'`** first — it's the canonical intent→cadence mapping.

- **User-triggered** (`when` stays empty): `manual` (run-now button), `form`
  (recipient fills a structured form → agent processes the submission), `chat`
  (interactive Q&A surface).
- **System-triggered** (`when` is a match expression, not a time): `email`
  (fires on matching inbox mail), `event` (fires on an ERP data change).
- **Time-based** (`when` is required, format per cadence): `appointment`,
  `daily`, `weekly`, `monthly`, `quarterly`, `yearly`. All times Europe/Berlin.

The classic mistake: building a `manual` slot when the user wants a `form`, or
conflating `chat` (open Q&A) with `form` (structured one-shot). See
[reference/cadences-and-config.md](reference/cadences-and-config.md).

## Start from the agent library, not a blank prompt

Before writing a prompt from scratch, check the shipped templates — they cover
the common ERP-classic agents (address change, B2B quote, complaint triage,
cockpit KPI writer, …). Each library item is a **prefill**: a ready cadence,
tool set, model, and a tested instruction prompt, in DE and EN. Clone the
closest one and adapt it; the prefill maps field-for-field onto the
`custom_agent_add` params, so cloning is faster and safer than hand-assembling.
Hand-build only when no template is close. See
[reference/library-and-recipes.md](reference/library-and-recipes.md).

## The workflow (every task)

1. `action: help` — the live manual for this tool version. Read once per session.
2. `action: agent_types` — when the user described intent in words, confirm the
   right cadence before creating anything.
3. `action: list` — the built-in agents already enabled in the instance (assign
   a slot to one of these by its exact slug, or pick a tool target for a job).
4. `action: custom_agent_list` / `custom_agent_schedule` — see existing slots
   and "who runs next?".
5. **Create / change:** `custom_agent_add` (required: `cadence`, `when`,
   `agent`, `area`, `note`), `custom_agent_update` (by `slot_id` — **the id
   changes after every successful update**, it's a content hash; use the new id
   next), `custom_agent_move` (drag-drop convenience), `custom_agent_remove`.

Everything the Agent-Konfiguration UI exposes is also a tool param — never tell
the user "you have to do that in the UI". Pass `prompt`, `tools`, `model`,
`temperature`, and the cadence-specific `form_meta` / `chat_meta` / `email_meta`
directly on `custom_agent_add`.

## Which reference to read

Read the file that matches the task — don't load all of them:

- **Cadences & the full configuration surface** — every cadence's `when`
  format, the `prompt`/`tools`/`model`/`temperature` core, the pickable MCP-tool
  slugs, and `form_meta` / `chat_meta` / `email_meta` shapes →
  [reference/cadences-and-config.md](reference/cadences-and-config.md)
- **The library prefill, the create recipes, naming & anti-patterns** — how a
  library item maps onto `custom_agent_add`, first-enable / tune / audit / retry
  flows, the `agent`-title naming rule →
  [reference/library-and-recipes.md](reference/library-and-recipes.md)
- **Public form & chat shares** — public `/f/` and `/c/` links, tokens, rate
  limits, captcha state, and embedding a slot inside a dashboard →
  [reference/public-shares.md](reference/public-shares.md)

## Don'ts

- Don't pick `manual` when the user wants a recipient-fillable form — use `form`
  + `form_meta.fields`.
- Don't pass a slug like `product_data_capture` as the `agent` title — that
  field is the human-readable display label ("Produktdaten erfassen"). Slugs are
  only for assigning a slot to a **built-in** agent from `action='list'`.
- Don't tell the user fields must be configured in the UI — pass
  `form_meta={fields:[…]}` on `custom_agent_add`.
- Don't reuse a stale `slot_id` after an update — it always changes.
- Don't throw work away below the confidence threshold — agents create a
  `requires_intervention` job so a human can review.
