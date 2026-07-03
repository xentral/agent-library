# Public form & chat shares

`form` and `chat` slots can be **shared publicly without login** — a "request a
return" form for end customers, or a pre-sales chat bot embedded on the company
website. Enable in the slot editor under "Öffentlicher Link": the backend mints
a `share_id` (12 URL-safe chars, ~72 bits of entropy). Activation is a separate
flag; deactivating returns `404` until reactivated. `share_id` + token are
preserved on deactivation — **rotating** mints a new id and invalidates the old
URL immediately.

## Form cadence (`cadence=form`)

- **URL**: `/f/{share_id}` — a server-rendered HTML form (no SPA). Fields come
  from `slot.form_meta.fields`.
- **POST** to the same URL submits the form and queues **one job** for the
  referenced agent — same path as an authenticated submission.
- **Audience**: `form_meta.audience` = `internal` (auth required) or `external`
  (public). Only `external` is served at `/f/`.
- **Captcha**: for `audience=external` the endpoint checks an `X-Form-Captcha`
  header — currently a **stub** (any non-empty value passes). Replace with
  hCaptcha / Turnstile before production.
- **File upload**: the schema accepts `type=file` and the public HTML renders
  the input, but multipart handling is a v1 stub. Form slots that need files
  should stay internal for now.
- **Rate limit**: 12 submissions / 60 s per `share_id`, in-process sliding
  window (multiplies by worker count in a multi-worker setup). Over the limit →
  `429`.

## Chat cadence (`cadence=chat`)

- **URLs**:
  - `/c/{share_id}` — standalone full-page chat widget.
  - `GET /public/chat/{share_id}/meta` — slot metadata (title, greeting, brand
    colour).
  - `POST /public/chat/{share_id}/message` — send a user turn; the response
    streams (SSE).
  - `/chat-widget.js` — embed snippet for the customer's website.
- **Stateless**: the client sends the **full conversation history** every turn
  (no per-session server state). Reload = reset.
- **Caps per request**: max 60 messages (≈30 turns, older trimmed), max 4000
  chars per message.
- **Rate limit**: 30 messages / 5 min per (client-IP, share_id). The IP tuple
  is required because a public chat URL is easier to abuse than a form.
- **CORS**: open, so the widget can be embedded on any domain.

## Token, opaque 404s, auth context

- **Token**: optional (max 128 chars, constant-time comparison), passed as
  `?token=…`. A second gate; link-only shares are allowed. For a mass-mailed
  link, set a token and rotate it after the campaign.
- **Opaque 404s**: unknown `share_id`, wrong token, deactivated share — all map
  to an identical `404` so a share's existence stays opaque.
- **Synthetic AuthUser**: public submissions/turns run under
  `user_id="form-public-share"` / `"chat-public-share"`, no real JWT. Instance
  isolation comes from the share record — there is no path through a public link
  into another instance.

## Embedding a slot inside a dashboard

Every `form` / `chat` / `manual` slot can ALSO be embedded inline in a dashboard
via the `xentral_dashboards` widget catalogue's **`Agent`** widget. Add an
`Agent` widget with `config.agents[]` referencing the slot's `agent_name`; the
widget renders form-shape / chat-shape / button-shape automatically based on the
slot's cadence. So "can I add a form to my dashboard?" → **yes**: create the
form slot here, then attach it via `xentral_dashboards` (see its `action='help'`,
section "Interactive — let the user trigger an agent from the dashboard").

> Chat slots are **not** rendered on *public* dashboards — only form slots are.
