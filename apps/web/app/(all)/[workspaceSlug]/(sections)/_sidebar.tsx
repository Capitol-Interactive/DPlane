/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import { useState } from "react";
import { observer } from "mobx-react";
import { useParams, usePathname } from "next/navigation";
import { SIDEBAR_WIDTH } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
// components
import { getAppSectionFromPathname } from "@/components/navigation/app-sections";
import type { TAppSectionKey } from "@/components/navigation/app-sections";
import { ResizableSidebar } from "@/components/sidebar/resizable-sidebar";
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";
import { WikiSidebar } from "@/components/wiki/sidebar/root";
// hooks
import { useAppTheme } from "@/hooks/store/use-app-theme";
// local imports
import { SectionNavPanel } from "./_nav-panel";

// Sections with their own navigation panel; the others show a placeholder until they are built
const SECTION_PANELS: Partial<Record<TAppSectionKey, ComponentType>> = {
  knowledge: WikiSidebar,
  agents: SectionNavPanel,
  strategy: SectionNavPanel,
  people: SectionNavPanel,
  clients: SectionNavPanel,
};

export const SectionSidebar = observer(function SectionSidebar() {
  // store hooks
  const { sidebarCollapsed, toggleSidebar, sidebarPeek, toggleSidebarPeek, isAnySidebarDropdownOpen } = useAppTheme();
  const { storedValue, setValue } = useLocalStorage("sidebarWidth", SIDEBAR_WIDTH);
  // states
  const [sidebarWidth, setSidebarWidth] = useState<number>(storedValue ?? SIDEBAR_WIDTH);
  // routes
  const { workspaceSlug } = useParams();
  const pathname = usePathname();
  // derived values
  const section = getAppSectionFromPathname(pathname, workspaceSlug);
  const SectionPanel = section ? SECTION_PANELS[section.key] : undefined;

  return (
    <ResizableSidebar
      showPeek={sidebarPeek}
      defaultWidth={storedValue ?? SIDEBAR_WIDTH}
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
      {SectionPanel ? (
        <SectionPanel />
      ) : (
        <SidebarWrapper title={section?.label ?? ""}>
          <p className="px-2 text-13 text-tertiary">Nothing here yet.</p>
        </SidebarWrapper>
      )}
    </ResizableSidebar>
  );
});
