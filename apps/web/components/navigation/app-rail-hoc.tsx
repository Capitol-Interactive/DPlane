/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// hoc/withDockItems.tsx
import React from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Projects } from "@makeplane/propel/icons";
import type { AppSidebarItemData } from "@/components/sidebar/sidebar-item";
import { useWorkspacePaths } from "@/hooks/use-workspace-paths";
import { getRailSectionHref, RAIL_SECTIONS } from "@/lib/app-rail/sections";

type WithDockItemsProps = {
  dockItems: (AppSidebarItemData & { shouldRender: boolean })[];
};

export function withDockItems<P extends WithDockItemsProps>(WrappedComponent: React.ComponentType<P>) {
  const ComponentWithDockItems = observer(function ComponentWithDockItems(props: Omit<P, keyof WithDockItemsProps>) {
    const { workspaceSlug } = useParams();
    const { isProjectsPath, isNotificationsPath, activeRailSectionKey } = useWorkspacePaths();

    const dockItems: (AppSidebarItemData & { shouldRender: boolean })[] = [
      {
        label: "Work",
        icon: <Projects className="size-5" />,
        href: `/${workspaceSlug}/`,
        isActive: isProjectsPath && !isNotificationsPath,
        shouldRender: true,
      },
      ...RAIL_SECTIONS.map((section) => {
        const SectionIcon = section.icon;
        return {
          label: section.label,
          icon: <SectionIcon className="size-5" />,
          href: getRailSectionHref(workspaceSlug?.toString() ?? "", section),
          isActive: activeRailSectionKey === section.key,
          shouldRender: true,
        };
      }),
    ];

    return <WrappedComponent {...(props as P)} dockItems={dockItems} />;
  });

  return ComponentWithDockItems;
}
