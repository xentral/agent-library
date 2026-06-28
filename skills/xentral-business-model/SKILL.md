---
name: xentral-business-model
description: >
  Read and maintain a tenant's Business Model — the canonical description of how
  the business actually runs (model, sales channels, fulfillment, automation,
  target market, pain points) — with the `xentral_business_model` tool. Covers
  the 6-dimension strict-enum profile that every other agent reads first, the
  markdown sections, starting from a library template, and the read/write/
  apply_template/profile_set workflow. Use when onboarding a tenant, when the
  user describes a strategic change ("we opened a B2C shop", "we moved to a
  3PL"), or when another agent needs business context before acting — not to log
  day-to-day operations (Jobs) or track metrics (Dashboards).
examples:
  - "Set up the business model for a new B2B wholesale tenant."
  - "We just launched a French webshop — update the business model."
  - "Classify this tenant's profile so the other agents behave correctly."
---

# Xentral Business Model

## Purpose

The Business Model is the **canonical description of how this tenant actually
runs**: business model, sales channels, fulfillment posture, automation level,
target market, pain points. It is the source of truth every other AI feature
reads first to behave appropriately for *this* operator. The
`xentral_business_model` tool reads and maintains it.

What it is **not**:

- **Not a financial plan / P&L.** It describes the business, not its forecast —
  no per-quarter numbers.
- **Not a marketing brochure.** Concrete facts an agent can act on, no fluff.
- **Not an operations log.** Day-to-day decisions go to Jobs / System Events;
  step-by-step process definitions go to Bausteine.

## The profile is the contract

The single most important part is the **profile** — a 6-dimension strict-enum
classification that every other agent keys off to pick behavior. Get it right
first; everything downstream depends on it.

| Field | Type | Drives |
|---|---|---|
| `business_model` | single | `b2c`, `b2b`, `d2c`, `marketplace`, `manufacturer`, `wholesale`, `mixed` — invoice phrasing, payment-term defaults |
| `sales_channels` | multi | `ecommerce`, `marketplaces`, `pos`, `field_sales`, `wholesale`, `distributors` — expected integrations |
| `fulfillment` | single | `in_house`, `3pl`, `dropshipping`, `mixed` — shipping-doc layout, returns flow |
| `automation` | single | `low`, `mid`, `high` — how aggressively agents auto-act vs. ask |
| `size` | single | `small`, `mid`, `upper`, `enterprise` — feature/plan suggestions |
| `complexity` | single | `simple`, `medium`, `complex` — how detailed agent explanations are |

**Always set the profile via `profile_set`, never via `write`.** The `write`
path doesn't enforce the enums and lets a typo through silently, breaking every
downstream agent. Read the live enum list (`profile_get` / the tool's enum
schema) before setting — invalid values are rejected.

## Start from a library template

For a fresh tenant, seed the sections from a starter template instead of writing
each from scratch. The library ships business-model templates (b2b_wholesale,
d2c, ecommerce_boutique, manufacturer, multi_channel, generic, …), each paired
with a `_configuration`. Apply one with `apply_template`, then refine. The three
skeleton flavours are `classic`, `agents`, `ai_first`.

## The workflow (every task)

1. `action: help` — the live manual (section semantics, profile enum values).
   Read once per session; pass `locale='de'` for German.
2. `action: profile_get` — read the 6-dimension profile (and the valid enums).
3. `action: read` — without `slug`: list all sections with metadata; with
   `slug`: one section's markdown. **Always read before a `replace` write.**
4. **Seed / classify:** `apply_template` (`classic|agents|ai_first`,
   `overwrite=false` by default — non-destructive), then `profile_set` for the
   six dimensions.
5. **Edit:** `write` a section — `mode='replace'` (default) or `mode='append'`
   (incremental adds). Never `write` the `profile` section.

## Which reference to read

- **Profile enums, the section catalogue, recipes & pitfalls** — the full
  section list (mission, target_market, channels, operations, pain_points,
  tone, …), invariants, and the onboarding / strategic-update / quick-add flows →
  [reference/profile-and-sections.md](reference/profile-and-sections.md)

## Don'ts

- Don't write the `profile` section via `write` — use `profile_set` (enum-safe).
- Don't `replace` a section without `read`ing it first in the same turn — you'll
  clobber the user's work.
- Don't `apply_template(overwrite=true)` without explicit user consent — the
  default `false` protects edited sections.
- Don't fill every section eagerly at onboarding — empty sections legitimately
  mean "not relevant yet".
- Don't paste chat or marketing copy into a section — distill actual operations;
  every section is read by other agents like a public API.
