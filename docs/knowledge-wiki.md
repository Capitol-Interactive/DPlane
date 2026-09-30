# Knowledge wiki

The Knowledge section of the [app rail](app-rail.md) is a workspace-level wiki: pages that belong to the
workspace instead of a project, grouped into collections, with nested sub pages and real-time collaboration.

## Model

- A **wiki page** is a `Page` with `is_global=True` and **no** `ProjectPage` rows. There is no separate table.
- `WikiCollection` (`apps/api/plane/db/models/page.py`, table `wiki_collections`) groups root pages.
  `Page.collection` is a nullable FK that is only set on root pages; sub pages inherit through `parent`.
  Migration: `0123_wikicollection_page_collection`.
- Sidebar sections are derived, not stored:
  - **Collections**: root pages with a collection, plus their sub pages.
  - **My pages**: pages you own that have no parent and no collection (created private by default).
  - **Favorites**: `UserFavorite(entity_type="page")` rows for wiki pages.
- Access follows project pages: public pages are visible to every workspace member, private pages only to the
  owner. **Guests only see their own pages.** Only the owner can change a page's access.

## API

All endpoints live under `workspaces/<slug>/wiki/` (`apps/api/plane/app/urls/wiki.py`, views in
`apps/api/plane/app/views/wiki/base.py`). Permission class: `WorkspaceEntityPermission`
(any member reads, admin/member writes) plus per-page visibility rules.

| Endpoint                                  | Methods            | Notes                                                                                             |
| ----------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------- |
| `collections/`                            | GET, POST          | `page_count` counts pages visible to the caller                                                   |
| `collections/<id>/`                       | PATCH, DELETE      | Owner or workspace admin. Delete: `?mode=transfer&target_collection=<id>` or `?mode=delete_pages` |
| `pages/`                                  | GET, POST          | GET is flat (client builds the tree); `?archived=true` for archived                               |
| `pages/<id>/`                             | GET, PATCH, DELETE | DELETE requires the page to be archived first; sub pages move to the root                         |
| `pages/<id>/favorite/`                    | POST, DELETE       | Wiki favorites do not use the generic `user-favorites/` API                                       |
| `pages/<id>/archive/`, `lock/`, `access/` | POST, DELETE       | Archive cascades to sub pages                                                                     |
| `pages/<id>/description/`                 | GET, PATCH         | Binary Yjs document; used by the editor and live server                                           |
| `pages/<id>/versions/[<version_id>/]`     | GET                |                                                                                                   |
| `pages/<id>/duplicate/`                   | POST               | The caller becomes the owner of the copy                                                          |

Hierarchy rules enforced server-side: parent and collection must belong to the same workspace, a page cannot be
moved under itself or its descendants, placing a page in a collection makes it a root page, and setting a
parent clears the collection.

## API token access

The endpoints above need a browser session. For scripts and integrations there is a second set that accepts a Plane
API token (`X-Api-Key: plane_api_...`, created under Profile settings, API tokens) under
`/api/v1/workspaces/<slug>/wiki/` (`apps/api/plane/api/views/wiki.py`, `api/urls/wiki.py`,
`api/serializers/wiki.py`). It shares the visibility and hierarchy rules of the session endpoints through
`apps/api/plane/utils/wiki.py`, so the two cannot drift. Interactive docs are in the "Wiki" tag of the v1 OpenAPI
schema.

| Endpoint                              | Methods            | Notes                                                                                                 |
| ------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------- |
| `collections/`                        | GET, POST          |                                                                                                       |
| `collections/<id>/`                   | GET, PATCH, DELETE | DELETE **requires** `?mode=transfer&target_collection=<id>` or `?mode=delete_pages` (else 400)        |
| `pages/`                              | GET, POST          | GET is paginated (`per_page`, `cursor`) with `archived`, `collection`, `parent` (or `null`), `search` |
| `pages/<id>/`                         | GET, PATCH, DELETE | GET includes `description_html`; DELETE requires the page to be archived first                        |
| `pages/<id>/archive/`                 | POST, DELETE       | Archive (cascades to sub pages) and restore                                                           |
| `pages/<id>/lock/`                    | POST, DELETE       | Lock and unlock; owner or workspace admin                                                             |
| `pages/<id>/duplicate/`               | POST               | The token's user owns the copy                                                                        |
| `pages/<id>/versions/[<version_id>/]` | GET                | List is paginated and omits content                                                                   |

Differences from the session API:

- Collection delete has no default mode, so a script that forgets the parameter cannot wipe a collection's pages.
- Lock and unlock are limited to the owner or a workspace admin (the session endpoint lets any member call them; the
  UI hides the button).
- `access` is a plain integer: `0` public, `1` private. Only the owner can change it (403 otherwise).
- Favorites are not exposed (per-user UI state).
- Access is by workspace membership of the token's user, as for every v1 endpoint; a token is not restricted to the
  workspace it was created in. Guests see only their own pages and cannot write.

### Writing content

Send `description_html` on `POST pages/` or `PATCH pages/<id>/`. It is sanitized with the same allow-list as the
editor (`validate_html_content`), and a non-string or oversized value is a 400. Locked and archived pages refuse all
edits (`error_code` 4701 / 4702).

The editor stores its document as a Yjs binary (`description_binary`) and only rebuilds it from `description_html`
when the binary is empty (`apps/live/src/extensions/database.ts`). So a content write also sets
`description_binary = NULL` and `description_json = {}`, records a page version, and enqueues `page_transaction`.
Metadata-only patches leave the binary alone.

### Caveats for open editors

Verified in a browser: after an API write the editor shows the new content on the next load, with these exceptions.

- **An editor that has the page open keeps its in-memory copy** and can overwrite the API change the next time it
  saves. The live server also holds a document in memory for a short time after the last tab closes, and writes it
  back when it unloads, so an API edit made in that window is lost. Edit pages nobody is working on, or lock the
  page first.
- **A browser that opened the page before keeps a local copy** (`y-indexeddb`, keyed by page id,
  `packages/editor/src/hooks/use-yjs-setup.ts`). When it loads the rebuilt document it merges the two, and the page
  shows the old text and the new text together. A browser with no history for the page (a new profile, another
  device, or cleared site data) shows only the API content. A proper fix would change the editor's local
  persistence key when the server resets the binary; it is not done.

## Live (collaboration) server

`apps/live` supports the `workspace_page` document type: `WorkspacePageService`
(`apps/live/src/services/page/workspace-page.service.ts`) talks to `/api/workspaces/<slug>/wiki` and needs only a
workspace slug and the user's cookie. The web app connects with `documentType: "workspace_page"` and no
`projectId`.

### Load speed

- The wiki pages and collections are prefetched in the background about 1.5 s after the workspace opens
  (`apps/web/components/wiki/wiki-data-prefetch.tsx`, mounted in `WorkspaceContentWrapper`), so the first visit
  to Knowledge finds them already in the store. Members and admins only; guests only see their own pages.
  The sidebar, the Wiki home and the prefetch share the SWR keys in `apps/web/components/wiki/swr-keys.ts`.
- While the first load is running the Collections section shows skeleton rows instead of "No collections yet".
- With 2 s of simulated API latency, click-to-tree went from 2.9 s to 1.0 s (dev server, so absolute numbers are
  inflated). Server time itself is small: production `GET /wiki/pages/` and `/wiki/collections/` took 29-51 ms.
- Opening a page is still slower than the Knowledge home: it loads the editor bundle and then tries the live
  websocket, which fails when `apps/live` is not deployed and falls back to loading the saved content. Deploying
  the live server is the real fix.

### Deployment note

Real-time collaboration needs `apps/live` running and `VITE_LIVE_BASE_URL` (baked into the web build) pointing
at it. As of 2026-09-30 the live server is not deployed in production (see `docs/deployment-brief.md`), so wiki
pages there can be listed, created and opened, but not edited collaboratively until it is.

## Web app

- Services: `apps/web/services/page/{workspace-page,workspace-page-version,wiki-collection}.service.ts`.
- Stores: `WorkspacePageStore` and `WorkspacePage` in `apps/web/store/pages/` (root store field `workspacePages`,
  hook `usePageStore(EPageStoreType.WORKSPACE)`). Permissions come from the workspace role. Tree helpers:
  `getRootPageIdsByCollection`, `getChildPageIds`, `getPageAncestorIds`, `favoritePageIds`, `myPageIds`.
- `TPage` gained optional `parent`, `collection` and `sort_order` (via `TPageExtended`).
  `BasePage` accepts optional `addToFavorites`/`removeFromFavorites` service hooks so wiki pages can use their
  own favorite endpoints.
- UI: `apps/web/components/wiki/` (sidebar, collection modals, header) and the routes under
  `apps/web/app/(all)/[workspaceSlug]/(sections)/knowledge/` (`page.tsx` = Wiki home, `[pageId]/page.tsx` =
  editor). The page editor is the shared `PageRoot`; only the services/handlers are swapped.
- Project-only page list components narrow `storeType` to `EPageStoreType.PROJECT`.

## Testing

- API (session): `apps/api/plane/tests/contract/app/test_wiki_app.py` (21 tests).
- API (token): `apps/api/plane/tests/contract/api/test_wiki_api.py` (44 tests: authentication, workspace isolation,
  guests, visibility, CRUD, filters and pagination, hierarchy, collection delete modes, sanitizing, binary clearing,
  lock, duplicate, versions).
- Live: `apps/live/tests/services/page/handler.test.ts`.
- The web app has no unit test setup; the UI was verified by typecheck, lint and a manual browser pass.

### Running the API tests without Docker

Docker was not available in some sandboxes. Equivalent local setup: a virtualenv with `requirements/test.txt`
(swap `psycopg-c` for `psycopg[binary]` if you have no `libpq-dev`), a local Postgres and Redis, and:

```bash
export DATABASE_URL=postgresql://postgres@localhost:5433/plane REDIS_URL=redis://localhost:6380/
export SECRET_KEY=test DJANGO_SETTINGS_MODULE=plane.settings.test LIVE_SERVER_SECRET_KEY=secret-key
export AMQP_URL=memory://   # avoids needing RabbitMQ for tasks that fire on soft delete
cd apps/api && python -m pytest plane/tests/contract/app/test_wiki_app.py plane/tests/contract/api/test_wiki_api.py
```

`test_project_app.py::test_delete_project_success_workspace_admin` fails without a RabbitMQ broker
(`AMQP_URL=memory://` is not enough); it fails the same way without the wiki changes.

## Not built yet

- **Shared with me**: there is no per-user page sharing model.
- The AI assistant panel, publishing pages, comments, and wiki search (global search only surfaces `is_global`
  pages reachable through a project, so wiki pages are excluded).
- Version restore: the API has no restore endpoint, so the editor's restore handler is a no-op.
- Sidebar labels ("Collections", "My pages", "New page") are hardcoded English; the collection dialogs reuse the
  existing `wiki_collections` translations.
- Drag-and-drop reordering and moving pages between collections from the UI (the API supports `parent`,
  `collection` and `sort_order` updates).
- The web pages list page (`/projects/:id/pages`) is unchanged and still project-only.
