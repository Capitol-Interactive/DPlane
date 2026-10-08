/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { cn } from "@plane/utils";
// components
import { getAppSectionFromPathname } from "@/components/navigation/app-sections";
import { getSectionNavItem, SECTION_NAV } from "@/components/navigation/section-nav";
import { SidebarNavItem } from "@/components/sidebar/sidebar-navigation";
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";

function GroupHeading({ children }: { children: React.ReactNode }) {
  return <span className="px-2 pb-1 text-11 font-semibold text-placeholder">{children}</span>;
}

/** Sidebar panel for a section described in SECTION_NAV (Agents, Strategy, People, Clients) */
export const SectionNavPanel = observer(function SectionNavPanel() {
  const { workspaceSlug, itemKey } = useParams();
  const pathname = usePathname();
  // derived values
  const section = getAppSectionFromPathname(pathname, workspaceSlug);
  const nav = section ? SECTION_NAV[section.key] : undefined;
  const activeItem = getSectionNavItem(nav, itemKey?.toString());

  if (!section || !nav) return null;

  return (
    <SidebarWrapper title={nav.title}>
      {nav.groups.map((group) => (
        <div key={group.key} className="flex flex-col gap-0.5">
          {group.title && <GroupHeading>{group.title}</GroupHeading>}
          {group.items.map((item) => {
            const isActive = activeItem?.key === item.key;
            return (
              <Link key={item.key} href={`/${workspaceSlug}/${section.key}/${item.key}`}>
                <SidebarNavItem isActive={isActive}>
                  <div className="flex items-center gap-1.5 py-[1px]">
                    <item.icon className={cn("size-4 flex-shrink-0", { "text-icon-primary": isActive })} />
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
      {nav.recentEmptyLabel && (
        <div className="flex flex-col gap-2">
          <GroupHeading>Recent</GroupHeading>
          <p className="px-2 text-center text-12 text-tertiary">{nav.recentEmptyLabel}</p>
        </div>
      )}
    </SidebarWrapper>
  );
});
