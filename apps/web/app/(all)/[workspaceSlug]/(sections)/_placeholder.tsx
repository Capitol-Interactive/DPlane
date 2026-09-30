/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PageHead } from "@/components/core/page-title";
import type { TAppSection } from "@/components/navigation/app-sections";

export function AppSectionPlaceholder({ section }: { section: TAppSection }) {
  return (
    <>
      <PageHead title={section.label} />
      <div className="flex size-full flex-col items-center justify-center gap-2 px-6 text-center">
        <h1 className="text-18 font-semibold text-primary">{section.label}</h1>
        <p className="max-w-md text-13 text-tertiary">{section.description}</p>
        <p className="text-13 text-placeholder">Coming soon.</p>
      </div>
    </>
  );
}
