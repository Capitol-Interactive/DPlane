/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams, usePathname } from "next/navigation";
import { SIDEBAR_WIDTH } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
// components
import { getAppSectionFromPathname } from "@/components/navigation/app-sections";
import { ResizableSidebar } from "@/components/sidebar/resizable-sidebar";
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";
// hooks
import { useAppTheme } from "@/hooks/store/use-app-theme";

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
      <SidebarWrapper title={section?.label ?? ""}>
        <p className="px-2 text-13 text-tertiary">Nothing here yet.</p>
      </SidebarWrapper>
    </ResizableSidebar>
  );
});
