# Xentral Agent Library

Public catalogue for the **Xentral Agent Hub**. This single repo serves two consumers:

1. **The Agent Hub backend** vendors `library/` and `skills/` at Docker build time (pinned to a
   release tag — no runtime/CDN fetch). These power the in-product Library Pickers.
2. **Customers' Claude Code** installs this repo as a **plugin marketplace**, getting the
   Xentral MCP connector and all skills in two commands.

One source of truth, one release cadence.

## Install (Claude Code)

```
/plugin marketplace add xentral/agent-library
/plugin install xentral-connector@xentral
```

That's it. The MCP connector is wired up and every `xentral-*` skill becomes available. OAuth
runs automatically on the first tool call. Update later with `/plugin update`.

## Layout

```
manifest.json            version + per-type file index + checksums
library/                 catalogue content (one folder per type, one JSON per item)
  agents/
  workflows/
  dashboards/
  kpi/
  pdf-templates/
  business-blocks/
  business-plan/
  connections/
skills/                  Claude Code skills (one folder per tool family)
  <xentral-...>/SKILL.md
schemas/                 JSON Schema per library type (validated in CI)
.claude-plugin/          plugin + marketplace manifests
```

## Conventions

- **Library items**: one JSON file per item under `library/<type>/`. Must validate against
  `schemas/<type>.schema.json`.
- **Skills**: kebab-case, `xentral-` prefixed (e.g. `xentral-pdf-templates`), one per tool
  family with real "how to" knowledge.
- **No secrets, no tenant data.** This repo is public; CI scans every PR.
- **Releases**: production pins an explicit tag (e.g. `2026.06.0`); `manifest.json` version
  bumps on every release.

## License

TODO: choose a permissive content license before the first public release — customers copy from
this catalogue.

---

See the design concept in the backend repo: `doc/LIBRARY_AND_SKILLS_EXTERNALIZATION_CONCEPT.md`.
