# Contributing — Xentral Agent Library

This public repo is the **single source of truth** for two consumers:

1. **The Agent OS backend** vendors `library/` and `skills/` at Docker build time
   (pinned to a release tag — no runtime/CDN fetch). These power the in-product
   library pickers and the internal Advisor / MCP `action='help'`.
2. **Customers' Claude Code** installs this repo as a **plugin marketplace** — the
   Xentral MCP connector plus all skills (see the [README](README.md)).

One source of truth, one release cadence.

## Layout

```
manifest.json            version + per-type file index + checksums
library/                 catalogue content (one folder per type, one JSON per item)
  agents/  workflows/  dashboards/  kpi/  pdf-templates/
  business-blocks/  business-plan/  connections/  charts/
skills/                  Claude Code skills (one folder per tool family)
  <xentral-...>/SKILL.md         # lean entrypoint
  <xentral-...>/reference/*.md   # detail, loaded on demand
schemas/                 JSON Schema per library type (validated in CI)
scripts/validate_library.py      # local + CI validation
.claude-plugin/          plugin.json + marketplace.json
```

## Conventions

- **Library items**: one JSON file per item under `library/<type>/`; must validate
  against `schemas/<type>.schema.json` (`python scripts/validate_library.py`).
- **Skills**: kebab-case, `xentral-` prefixed, one per tool family. Keep `SKILL.md`
  lean (< 500 lines); push detail into `reference/*.md` loaded on demand. Skills
  are authored here by hand (domain teams) — they are **not** generated. English.
- **No secrets, no tenant data.** This repo is public; CI scans every PR.
- **Releases**: production pins an explicit tag (e.g. `2026.06.2`). Cut a new tag
  when library or skill content changes and bump the backend's `LIBRARY_VERSION`.
- **Plugin version**: bump `.claude-plugin/plugin.json` `version` on each release
  you want customers to auto-receive (a fixed version means no auto-update until
  it changes).

## How it reaches each consumer

- **Backend**: `make sync-library` (or the Docker `library` stage) downloads the
  pinned tag into `backend/_vendor/{library,skills}`. `agent_guides.loader`
  resolves skill-first (assembled SKILL.md + references), falling back to legacy
  module guides for domains without a skill.
- **Customers**: the plugin tracks this repo's default branch; `/plugin update`
  pulls the latest.

See the full design in the backend repo:
`doc/LIBRARY_AND_SKILLS_EXTERNALIZATION_CONCEPT.md`.
