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
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useWorkspacePaths } from "@/hooks/use-workspace-paths";
import { isAppSectionEnabled } from "./app-sections";

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
    const { currentWorkspace } = useWorkspace();
    // sections an admin turned off in Settings > Features
    const disabledSections = currentWorkspace?.disabled_app_sections;

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
        shouldRender: isAppSectionEnabled("agents", disabledSections),
      },
      {
        label: "Strategy",
        icon: <InitiativeOutline className="size-5" />,
        href: `/${workspaceSlug}/strategy`,
        isActive: isStrategyPath,
        shouldRender: isAppSectionEnabled("strategy", disabledSections),
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
        shouldRender: isAppSectionEnabled("people", disabledSections),
      },
      {
        label: "Clients",
        icon: <CustomersOutline className="size-5" />,
        href: `/${workspaceSlug}/clients`,
        isActive: isClientsPath,
        shouldRender: isAppSectionEnabled("clients", disabledSections),
      },
    ];

    return <WrappedComponent {...(props as P)} dockItems={dockItems} />;
  });

  return ComponentWithDockItems;
}
