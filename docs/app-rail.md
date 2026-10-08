# App rail

The app rail is the narrow icon column at the far left of the workspace (Asana/Plane-style). Each item is an
"app" that swaps the contextual panel next to it. The rail is enabled for every workspace route.

## Items

| Item      | Route                    | Panel                                                |
| --------- | ------------------------ | ---------------------------------------------------- |
| Work      | `/:workspace/` (default) | The existing projects sidebar (titled "Work")        |
| Agents    | `/:workspace/agents`     | Nav panel, placeholder pages                         |
| Strategy  | `/:workspace/strategy`   | Nav panel, placeholder pages                         |
| Knowledge | `/:workspace/knowledge`  | The wiki, see [knowledge-wiki.md](knowledge-wiki.md) |
| People    | `/:workspace/people`     | Nav panel, placeholder pages                         |
| Clients   | `/:workspace/clients`    | Nav panel, placeholder pages                         |
| More      | (menu)                   | Rail display mode (icon only / icon + name)          |
| Settings  | `/:workspace/settings`   | Workspace settings                                   |

## Where things live

- `apps/web/app/(all)/[workspaceSlug]/layout.tsx` turns the rail on (`<AppRailVisibilityProvider isEnabled>`).
  The rail is always shown when enabled and cannot be hidden by the user: nothing outside the rail could bring
  it back, and a stored "collapsed" flag from the old undock option is ignored (`apps/web/lib/app-rail/provider.tsx`).
- `apps/web/components/navigation/app-rail-hoc.tsx` defines the items (label, icon, href, active check).
- `apps/web/components/navigation/app-rail-root.tsx` renders the rail; `app-rail-more-menu.tsx` is the More menu.
- `apps/web/hooks/use-workspace-paths.ts` decides which item is active. Add an `isXPath` flag here for a new
  section **and** exclude it from `isProjectsPath`, otherwise "Work" stays highlighted.
- `apps/web/components/navigation/app-sections.ts` lists the non-project sections (`APP_SECTIONS`).

## Hiding sections (Settings > Features)

Workspace admins can hide Agents, Strategy, People and Clients from the rail for everyone in the workspace under
**Workspace settings > Developer > Features**. Work and Knowledge are always on.

- Stored on the workspace as `Workspace.disabled_app_sections` (JSON list, migration `0124`), saved through the
  existing admin-only `PATCH /api/workspaces/<slug>/`. The serializer rejects any key outside
  `TOGGLEABLE_APP_SECTIONS` (`apps/api/plane/app/serializers/workspace.py`) and stores keys once, in rail order.
- The web side mirrors that list in `TOGGLEABLE_APP_SECTION_KEYS` (`app-sections.ts`); keep the two in sync.
  `app-rail-hoc.tsx` sets `shouldRender` from `isAppSectionEnabled`.
- Hiding only removes the rail item. The section's URL still opens if someone goes to it directly.

## Adding a section

1. Add the item to `app-rail-hoc.tsx` and a path flag to `use-workspace-paths.ts`.
2. Add it to `APP_SECTIONS` in `app-sections.ts`.
3. Register its routes in `apps/web/app/routes/extended.ts` under the `(sections)` layout. `extended.ts` is
   the extension point for fork-only routes and is merged into `core.ts` by `app/routes/helper.ts`.
4. Give it a panel by adding an entry to `SECTION_PANELS` in
   `apps/web/app/(all)/[workspaceSlug]/(sections)/_sidebar.tsx`. Sections without one show a placeholder.
   For a plain list of links, add the section to `SECTION_NAV` in
   `apps/web/components/navigation/section-nav.ts` and register `SectionNavPanel`: it renders the groups, a
   "Recent" block, and links to `/:workspace/<section>/<item>`. The section's page (`_placeholder.tsx`) shows
   the selected item's copy; an unknown or missing item falls back to the first one.

## Known gaps

- Rail labels are hardcoded English (no i18n keys yet).
- Agents, Strategy, People and Clients have nav panels (Asana-style) but every item page is a placeholder.
- The More menu only holds rail options; there are no overflow apps yet.
