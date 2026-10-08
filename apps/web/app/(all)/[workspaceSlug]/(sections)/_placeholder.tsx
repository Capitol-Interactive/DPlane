/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import { PageHead } from "@/components/core/page-title";
import type { TAppSection } from "@/components/navigation/app-sections";
import { getSectionNavItem, SECTION_NAV } from "@/components/navigation/section-nav";

export function AppSectionPlaceholder({ section }: { section: TAppSection }) {
  const { itemKey } = useParams();
  // the item selected in the section's sidebar panel, if the section has one
  const item = getSectionNavItem(SECTION_NAV[section.key], itemKey?.toString());

  return (
    <>
      <PageHead title={item ? `${item.label} - ${section.label}` : section.label} />
      <div className="flex size-full flex-col items-center justify-center gap-2 px-6 text-center">
        <h1 className="text-18 font-semibold text-primary">{item?.title ?? section.label}</h1>
        <p className="max-w-md text-13 text-tertiary">{item?.description ?? section.description}</p>
        <p className="text-13 text-placeholder">Coming soon.</p>
      </div>
    </>
  );
}
