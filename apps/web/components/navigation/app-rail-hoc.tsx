/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// hoc/withDockItems.tsx
import React from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import {
  AgentOutline,
  CustomersOutline,
  InitiativeOutline,
  LibraryOutline,
  MembersOutline,
  Work,
} from "@makeplane/propel/icons";
import type { AppSidebarItemData } from "@/components/sidebar/sidebar-item";
import { useWorkspacePaths } from "@/hooks/use-workspace-paths";

type WithDockItemsProps = {
  dockItems: (AppSidebarItemData & { shouldRender: boolean })[];
};

export function withDockItems<P extends WithDockItemsProps>(WrappedComponent: React.ComponentType<P>) {
  const ComponentWithDockItems = observer(function ComponentWithDockItems(props: Omit<P, keyof WithDockItemsProps>) {
    const { workspaceSlug } = useParams();
    const {
      isProjectsPath,
      isNotificationsPath,
      isAgentsPath,
      isStrategyPath,
      isKnowledgePath,
      isPeoplePath,
      isClientsPath,
    } = useWorkspacePaths();

    const dockItems: (AppSidebarItemData & { shouldRender: boolean })[] = [
      {
        label: "Work",
        icon: <Work className="size-5" />,
        href: `/${workspaceSlug}/`,
        isActive: isProjectsPath && !isNotificationsPath,
        shouldRender: true,
      },
      {
        label: "Agents",
        icon: <AgentOutline className="size-5" />,
        href: `/${workspaceSlug}/agents`,
        isActive: isAgentsPath,
        shouldRender: true,
      },
      {
        label: "Strategy",
        icon: <InitiativeOutline className="size-5" />,
        href: `/${workspaceSlug}/strategy`,
        isActive: isStrategyPath,
        shouldRender: true,
      },
      {
        label: "Knowledge",
        icon: <LibraryOutline className="size-5" />,
        href: `/${workspaceSlug}/knowledge`,
        isActive: isKnowledgePath,
        shouldRender: true,
      },
      {
        label: "People",
        icon: <MembersOutline className="size-5" />,
        href: `/${workspaceSlug}/people`,
        isActive: isPeoplePath,
        shouldRender: true,
      },
      {
        label: "Clients",
        icon: <CustomersOutline className="size-5" />,
        href: `/${workspaceSlug}/clients`,
        isActive: isClientsPath,
        shouldRender: true,
      },
    ];

    return <WrappedComponent {...(props as P)} dockItems={dockItems} />;
  });

  return ComponentWithDockItems;
}
