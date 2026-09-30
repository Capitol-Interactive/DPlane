/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { layout, route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

export const extendedRoutes: RouteConfigEntry[] = [
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      // App rail sections (Agents, Strategy, Knowledge, People, Clients)
      layout("./(all)/[workspaceSlug]/(sections)/layout.tsx", [
        route(":workspaceSlug/agents", "./(all)/[workspaceSlug]/(sections)/agents/page.tsx"),
        route(":workspaceSlug/strategy", "./(all)/[workspaceSlug]/(sections)/strategy/page.tsx"),
        route(":workspaceSlug/knowledge", "./(all)/[workspaceSlug]/(sections)/knowledge/page.tsx"),
        route(":workspaceSlug/people", "./(all)/[workspaceSlug]/(sections)/people/page.tsx"),
        route(":workspaceSlug/clients", "./(all)/[workspaceSlug]/(sections)/clients/page.tsx"),
      ]),
    ]),
  ]),
];
