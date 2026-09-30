# Progress log

Fork-specific work on DPlane, newest first. Add an entry for each meaningful change and keep the status table
current. Feature details live in their own docs.

## Status

| Area                                                                   | Status                               | Doc                                                  |
| ---------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------- |
| App rail (Work, Agents, Strategy, Knowledge, People, Clients, More)    | Done; four sections are placeholders | [app-rail.md](app-rail.md)                           |
| Knowledge wiki: collections, nested pages, favorites, my pages, editor | Done                                 | [knowledge-wiki.md](knowledge-wiki.md)               |
| Wiki: shared with me, AI panel, publishing, comments, search           | Not started                          | [knowledge-wiki.md](knowledge-wiki.md#not-built-yet) |
| Agents, Strategy, People, Clients sections                             | Placeholders only                    | [app-rail.md](app-rail.md#known-gaps)                |
| i18n for rail and wiki sidebar labels                                  | Not started                          |                                                      |

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
