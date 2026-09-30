/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams, usePathname } from "next/navigation";
import { getRailSection, getRailSectionItems } from "@/lib/app-rail/sections";

/**
 * Resolves the rail section and item for the current URL
 * (`/:workspaceSlug/:section/:item?`). An unknown or missing item falls back to the section's first item.
 */
export const useActiveRail = () => {
  const { workspaceSlug } = useParams();
  const pathname = usePathname();

  const [sectionKey, itemKey] = (pathname.split(`/${workspaceSlug}/`)[1] ?? "").split("/");
  const section = getRailSection(sectionKey);
  const items = section ? getRailSectionItems(section) : [];
  const item = items.find((navItem) => navItem.key === itemKey) ?? items[0];

  return { section, item };
};
