# Component catalogue

Each component is `{ "id", "type", "props", "children?" }`. `children` only
applies to container (layout) types. This catalogue is the single source of
truth mirrored from `frontend/src/components/Workspace/Studio/jsonrender/catalog.js`.

## Layout (containers — hold `children`)

| Type | Props |
|---|---|
| `section` | `text` (optional title) |
| `box` | — |
| `row` | — (horizontal flow) |
| `column` | — (vertical flow) |
| `grid` | `columns` = `"1"`…`"4"` |
| `actionbar` | `align` = `left` \| `center` \| `right` |
| `tabs` | children are `tab` nodes |
| `tab` | `label` |

## Text

| Type | Props |
|---|---|
| `heading` | `text` |
| `text` | `text` |
| `divider` | — |

## Input

| Type | Props |
|---|---|
| `formfield` | `label`, `fieldType` (`text` \| `number` \| `date` \| `select` \| `textarea` \| `toggle` \| `checkbox`), `placeholder`, `options` (comma-separated, for `select`), `dataSource` (entity key to bind against) |

> Legacy input aliases `input` / `number` / `date` / `select` / `textarea` /
> `toggle` / `checkbox` still render, but prefer **one** `formfield` with the
> matching `fieldType`.

## Data

| Type | Props |
|---|---|
| `table` | `label`, `columns` (comma-separated), `dataSource` (entity key → live grid) |
| `entitypicker` | `label`, `dataSource` |
| `kpibox` | `label`, `value`, `delta`, `tone` (`up` \| `down` \| `neutral`), `kpiKey` (binds a real KPI) |
| `statusbadge` | `text`, `tone` (`neutral` \| `success` \| `warning` \| `danger`) |
| `timeline` | `label`, `items` (comma-separated steps) |
| `opstasks` | `label`, `categories` (comma-separated keys; empty = all) — surfaces the instance's real action-items list |

## Agents

| Type | Props |
|---|---|
| `formagent` | `label`, `agent` (agent id) — a structured intake form wired to an agent |
| `chatagent` | `label`, `agent` — a multi-turn chat assistant |

## Action

| Type | Props |
|---|---|
| `button` | `text`, `variant` (`primary` \| `secondary`), `action` |

## Bindings

`dataSource` / `agent` / `kpiKey` must reference a real value from the allowed
catalogues. An unknown value is **dropped on save** — the element falls back to a
mock, so it never errors at render, but it also won't be live. Bind only to
values that exist (entities from `list_entities`, registered KPI keys, real
agent ids).

## Button actions (`props.action`)

- `screen:<id>` — navigate to a screen
- `dialog:<id>` — open a dialog (modal)
- `tool:<name>` — call one of the app's MCP tools (the tool's logic is defined
  separately, not in the screen JSON)
