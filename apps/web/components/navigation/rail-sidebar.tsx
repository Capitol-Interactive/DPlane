/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { SIDEBAR_WIDTH } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import { cn } from "@plane/utils";
// components
import { ResizableSidebar } from "@/components/sidebar/resizable-sidebar";
import { SidebarNavItem } from "@/components/sidebar/sidebar-navigation";
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";
// hooks
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { useActiveRail } from "@/hooks/use-active-rail";
// lib
import { getRailItemPath } from "@/lib/app-rail/sections";

const SectionHeading = ({ children }: { children: React.ReactNode }) => (
  <span className="px-2 pb-1 text-11 font-semibold text-placeholder">{children}</span>
);

const RailSidebarContent = observer(function RailSidebarContent() {
  const { workspaceSlug } = useParams();
  const { section, item: activeItem } = useActiveRail();

  if (!section) return null;

  return (
    <SidebarWrapper title={section.sidebarTitle}>
      {section.groups.map((group) => (
        <div key={group.key} className="flex flex-col gap-0.5">
          {group.title && <SectionHeading>{group.title}</SectionHeading>}
          {group.items.map((item) => {
            const Icon = item.icon;
            const isActive = activeItem?.key === item.key;
            return (
              <Link key={item.key} href={`/${workspaceSlug}/${getRailItemPath(section, item)}`}>
                <SidebarNavItem isActive={isActive}>
                  <div className="flex items-center gap-1.5 py-[1px]">
                    <Icon className={cn("size-4 flex-shrink-0", { "text-icon-primary": isActive })} />
                    <p className="text-13 leading-5 font-medium">{item.label}</p>
                  </div>
                </SidebarNavItem>
              </Link>
            );
          })}
          {group.items.length === 0 && group.emptyLabel && (
            <p className="px-2 py-1 text-13 text-tertiary">{group.emptyLabel}</p>
          )}
        </div>
      ))}
      {section.recentEmptyLabel && (
        <div className="flex flex-col gap-2">
          <SectionHeading>Recent</SectionHeading>
          <p className="px-2 text-center text-12 text-tertiary">{section.recentEmptyLabel}</p>
        </div>
      )}
    </SidebarWrapper>
  );
});

/** Secondary sidebar for the non-project rails (agents, strategy, knowledge, people, clients) */
export const RailSidebar = observer(function RailSidebar() {
  // store hooks
  const { sidebarCollapsed, toggleSidebar, sidebarPeek, toggleSidebarPeek, isAnySidebarDropdownOpen } = useAppTheme();
  const { storedValue, setValue } = useLocalStorage("sidebarWidth", SIDEBAR_WIDTH);
  // states
  const [sidebarWidth, setSidebarWidth] = useState<number>(storedValue ?? SIDEBAR_WIDTH);

  return (
    <ResizableSidebar
      showPeek={sidebarPeek}
      defaultWidth={storedValue ?? 250}
      width={sidebarWidth}
      setWidth={setSidebarWidth}
      defaultCollapsed={sidebarCollapsed}
      peekDuration={1500}
      onWidthChange={setValue}
      onCollapsedChange={toggleSidebar}
      isCollapsed={sidebarCollapsed}
      toggleCollapsed={toggleSidebar}
      togglePeek={toggleSidebarPeek}
      isAnySidebarDropdownOpen={isAnySidebarDropdownOpen}
    >
      <RailSidebarContent />
    </ResizableSidebar>
  );
});
