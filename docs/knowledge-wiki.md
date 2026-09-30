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

## Live (collaboration) server

`apps/live` supports the `workspace_page` document type: `WorkspacePageService`
(`apps/live/src/services/page/workspace-page.service.ts`) talks to `/api/workspaces/<slug>/wiki` and needs only a
workspace slug and the user's cookie. The web app connects with `documentType: "workspace_page"` and no
`projectId`.

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

- API: `apps/api/plane/tests/contract/app/test_wiki_app.py` (21 tests).
- Live: `apps/live/tests/services/page/handler.test.ts`.
- The web app has no unit test setup; the UI was verified by typecheck, lint and a manual browser pass.

### Running the API tests without Docker

Docker was not available in some sandboxes. Equivalent local setup: a virtualenv with `requirements/test.txt`
(swap `psycopg-c` for `psycopg[binary]` if you have no `libpq-dev`), a local Postgres and Redis, and:

```bash
export DATABASE_URL=postgresql://postgres@localhost:5433/plane REDIS_URL=redis://localhost:6380/
export SECRET_KEY=test DJANGO_SETTINGS_MODULE=plane.settings.test LIVE_SERVER_SECRET_KEY=secret-key
export AMQP_URL=memory://   # avoids needing RabbitMQ for tasks that fire on soft delete
cd apps/api && python -m pytest plane/tests/contract/app/test_wiki_app.py
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
