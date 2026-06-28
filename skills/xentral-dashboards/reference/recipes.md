# Dashboards — recipes

## Recipes (common flows)

1. **First-time dashboards setup.**
   - Read `business_model.profile`.
   - List built-ins matched to the profile (e.g. for `b2b` +
     `wholesale` → "Open orders", "Customer credit risk",
     "Supplier deliveries").
   - Walk the operator through, enable the relevant ones, hide
     the rest.

2. **Custom dashboard for a specific role.**
   - Ask the operator: "what would this person check first in
     the morning?" — three to five concrete questions.
   - For each question, propose one widget from the catalog.
   - Place KPI tiles top, tables / charts below.
   - Pick a stable, descriptive slug.

3. **Audit existing dashboards.**
   - List custom dashboards.
   - For each, sample-render and check: any widget data sources
     broken (404/500), any zero-utility tile (always 0, always
     N/A).
   - Propose removing or fixing.

4. **Hide an unused built-in.**
   - List enabled built-ins.
   - For each, count views in the last 90 days (if you have
     telemetry) — propose hiding ones nobody looks at.

5. **Create a Co-Pilot chart from a prompt.**
   - User describes the question ("Revenue per month last year").
   - In the widget editor set `dataSource=prompt`, type the prompt,
     "Vorschlag generieren" → SQL + chart-type suggestion arrives.
   - Optional "Testdaten prüfen" for a sanity check.
   - On "Übernehmen" the report is auto-created in the "Agent Hub
     — generated" collection and linked to the widget.
   - Accept the cache-mode recommendation, or override deliberately.

6. **Nightly refresh for all data widgets on a dashboard.**
   - Via cron / agent schedule, call the MCP action
     `xentral_dashboards.refresh_all_widgets` with the dashboard
     slug.
   - Returns a summary `{refreshed_count, skipped_count,
     failed_count, …}`. `skipped` contains widgets without a
     `reportId` (presets, unsaved prompts) — expected, not an error.

