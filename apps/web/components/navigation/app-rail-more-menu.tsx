/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useState } from "react";
import { observer } from "mobx-react";
import { MoreHorizontalOutline } from "@makeplane/propel/icons";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@makeplane/propel/components/menu";
// components
import { AppSidebarItem } from "@/components/sidebar/sidebar-item";
// hooks
import { useAppRailPreferences } from "@/hooks/use-navigation-preferences";
import { useAppRailVisibility } from "@/lib/app-rail/context";

export const AppRailMoreMenu = observer(function AppRailMoreMenu({ showLabel }: { showLabel: boolean }) {
  // states
  const [isOpen, setIsOpen] = useState(false);
  // hooks
  const { preferences, updateDisplayMode } = useAppRailPreferences();
  const { toggleAppRail } = useAppRailVisibility();

  return (
    <Menu onOpenChange={setIsOpen}>
      {/* The trigger is a plain button wearing the rail item chrome (see help-section/root.tsx). */}
      <MenuTrigger
        render={
          <button
            type="button"
            className="group flex flex-col items-center justify-center gap-0.5 text-tertiary"
            aria-label="More"
          >
            <AppSidebarItem.Icon icon={<MoreHorizontalOutline className="size-5" />} highlight={isOpen} />
            {showLabel && <AppSidebarItem.Label label="More" highlight={isOpen} />}
          </button>
        }
      />
      <MenuContent side="right" align="start">
        <MenuItem
          label="Icon only"
          onClick={() => updateDisplayMode("icon_only")}
          selected={preferences.displayMode === "icon_only"}
        />
        <MenuItem
          label="Icon with name"
          onClick={() => updateDisplayMode("icon_with_label")}
          selected={preferences.displayMode === "icon_with_label"}
        />
        <MenuSeparator />
        <MenuItem label="Undock App Rail" onClick={toggleAppRail} />
      </MenuContent>
    </Menu>
  );
});
