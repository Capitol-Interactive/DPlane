# App rail

The app rail is the narrow icon column at the far left of the workspace (Asana/Plane-style). Each item is an
"app" that swaps the contextual panel next to it. The rail is enabled for every workspace route.

## Items

| Item      | Route                    | Panel                                                |
| --------- | ------------------------ | ---------------------------------------------------- |
| Work      | `/:workspace/` (default) | The existing projects sidebar (titled "Work")        |
| Agents    | `/:workspace/agents`     | Placeholder                                          |
| Strategy  | `/:workspace/strategy`   | Placeholder                                          |
| Knowledge | `/:workspace/knowledge`  | The wiki, see [knowledge-wiki.md](knowledge-wiki.md) |
| People    | `/:workspace/people`     | Placeholder                                          |
| Clients   | `/:workspace/clients`    | Placeholder                                          |
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

## Adding a section

1. Add the item to `app-rail-hoc.tsx` and a path flag to `use-workspace-paths.ts`.
2. Add it to `APP_SECTIONS` in `app-sections.ts`.
3. Register its routes in `apps/web/app/routes/extended.ts` under the `(sections)` layout. `extended.ts` is
   the extension point for fork-only routes and is merged into `core.ts` by `app/routes/helper.ts`.
4. Give it a panel by adding an entry to `SECTION_PANELS` in
   `apps/web/app/(all)/[workspaceSlug]/(sections)/_sidebar.tsx`. Sections without one show a placeholder.

## Known gaps

- Rail labels are hardcoded English (no i18n keys yet).
- Agents, Strategy, People and Clients are placeholders.
- The More menu only holds rail options; there are no overflow apps yet.
