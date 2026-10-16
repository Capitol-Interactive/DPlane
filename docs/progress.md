# Progress log

Fork-specific work on DPlane, newest first. Add an entry for each meaningful change and keep the status table
current. Feature details live in their own docs.

## Status

| Area                                                                   | Status                               | Doc                                                     |
| ---------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| App rail (Work, Agents, Strategy, Knowledge, People, Clients, More)    | Done; four sections are placeholders | [app-rail.md](app-rail.md)                              |
| Knowledge wiki: collections, nested pages, favorites, my pages, editor | Done                                 | [knowledge-wiki.md](knowledge-wiki.md)                  |
| Wiki: API token endpoints (v1)                                         | Done                                 | [knowledge-wiki.md](knowledge-wiki.md#api-token-access) |
| Wiki: shared with me, AI panel, publishing, comments, search           | Not started                          | [knowledge-wiki.md](knowledge-wiki.md#not-built-yet)    |
| Agents, Strategy, People, Clients sections                             | Nav panels done; pages placeholders  | [app-rail.md](app-rail.md#known-gaps)                   |
| i18n for rail and wiki sidebar labels                                  | Not started                          |                                                         |

## 2026-10-16 (bot users visible as members)

- Bot users (`is_bot=True`, no login, act through API tokens) now show up in workspace and project member lists,
  assignee pickers and @mention search, so agents can be assigned work and mentioned. Their comments show the
  bot's display name instead of `<first name>Bot`. Seat counts, analytics and telemetry still exclude bots.
  Changed: `app/views/project/member.py`, `app/views/workspace/member.py`, `app/views/search/base.py`,
  `workspace-member.store.ts`, `comments/card/display.tsx`.
- Agents > "Agent team" (the old "AI Teammates" placeholder) lists the workspace's bot users as cards with role,
  who they report to, open work items and recent comments. New: `User.bot_reports_to` (migration `0125`),
  `GET /api/workspaces/<slug>/agents/`, the `create_agent` management command and `docs/agents.md`.
- Verified: the 7 new contract tests pass, along with the wiki, workspace, project-member and app-sections tests,
  run against a local Postgres. `test_project_app.py` has 7 failures that also fail on `dev` (they need RabbitMQ).
  Not verified: no browser pass of the Agents page, and the agents themselves are not created yet.

## 2026-10-08 (section nav panels, Features settings, CI on dev)

- Agents, Strategy, People and Clients now have Asana-style sidebar panels (for example Agents: AI Teammates,
  then Workflow: Automations, Project templates, Forms, Custom fields). Each item has its own route
  (`/:workspace/<section>/<item>`) and a placeholder page; Knowledge is unchanged. Config lives in
  `apps/web/components/navigation/section-nav.ts`.
- Workspace settings > Developer > Features lets admins hide Agents, Strategy, People and Clients from the rail
  for the whole workspace (Work and Knowledge always on). New `Workspace.disabled_app_sections` field
  (migration `0124`), validated in `WorkSpaceSerializer`; strings translated in all locales. See
  [app-rail.md](app-rail.md#hiding-sections-settings--features).
- CI pull-request and push triggers now target `dev` and `production` instead of `preview`, so PRs into `dev`
  get the web/API build and lint checks. The `create-pull-request` skill now defaults its base to `dev`.

## 2026-09-30 (wiki API tokens)

- Added token-authenticated wiki endpoints under `/api/v1/workspaces/<slug>/wiki/` so scripts can create and edit
  Knowledge content with a Plane API token (collections, pages, archive, lock, duplicate, versions). Shared
  helpers moved to `apps/api/plane/utils/wiki.py`. Content writes clear the Yjs binary so the editor rebuilds from
  the HTML. Open editors and browsers that already opened the page can hide or merge an API edit; see
  [API token access](knowledge-wiki.md#api-token-access).

## 2026-09-30 (Knowledge load speed)

- Knowledge felt slower than Work because Work's data is loaded once at workspace startup while Knowledge fetched
  on click, and the sidebar said "No collections yet" while loading. Added a background prefetch of the wiki data
  and a loading skeleton. Page opens remain slower until `apps/live` is deployed.

## 2026-09-30 (follow-up)

- Removed the "Undock App Rail" option (More menu and right-click menu) and made the rail always render when
  enabled. Undocking unmounted the whole rail, including the only control that could re-dock it, so a user got
  stuck (the fix also restores the rail for browsers that already stored the collapsed flag).

## 2026-09-30

- Enabled the app rail and added Asana-style sections (Work, Agents, Strategy, Knowledge, People, Clients,
  More, Settings). New routes are registered through `apps/web/app/routes/extended.ts`.
- Built the Knowledge wiki on top of the existing `Page` model: `WikiCollection` model and migration `0123`,
  workspace-level API under `workspaces/<slug>/wiki/`, `workspace_page` support in the live server, workspace
  page stores/services in the web app, and the sidebar/editor UI.
- Fixed `track_page_version` reading a nonexistent `page.description`, which silently prevented page versions
  from being saved (affected project pages too).
- Verified with 21 API contract tests, live-server tests, web typecheck/lint, and a manual browser pass
  (create collection, create page in it, favorite, add sub page, delete-collection dialog). Not verified:
  two people editing the same page at once.
- Production caveat: `apps/live` is not deployed, so wiki collaboration will not work there yet. Migration
  `0123` runs automatically via the Railway `migrator` service on the next production deploy.
- Known follow-ups are listed in [knowledge-wiki.md](knowledge-wiki.md#not-built-yet).
