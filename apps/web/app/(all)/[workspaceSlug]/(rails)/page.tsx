/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { Header } from "@plane/blocks/layout";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { AppHeader } from "@/components/core/app-header";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useActiveRail } from "@/hooks/use-active-rail";

function RailPage() {
  const { section, item } = useActiveRail();

  if (!section || !item) return null;

  const Icon = item.icon;

  return (
    <>
      <PageHead title={`${item.label} - ${section.sidebarTitle}`} />
      <AppHeader
        header={
          <Header>
            <Header.LeftItem>
              <Breadcrumbs>
                <Breadcrumbs.Item
                  component={<BreadcrumbLink label={item.label} icon={<Icon className="size-4 text-secondary" />} />}
                />
              </Breadcrumbs>
            </Header.LeftItem>
          </Header>
        }
      />
      <div className="flex size-full flex-col items-center justify-center gap-3 px-6 pb-16 text-center">
        <div className="flex size-14 items-center justify-center rounded-xl bg-layer-transparent-selected">
          <Icon className="size-7 text-icon-secondary" />
        </div>
        <h2 className="text-18 font-semibold text-primary">{item.emptyTitle}</h2>
        <p className="max-w-md text-14 text-secondary">{item.emptyDescription}</p>
        <span className="rounded-full border border-subtle px-2.5 py-0.5 text-11 font-medium text-tertiary">
          Coming soon
        </span>
      </div>
    </>
  );
}

export default observer(RailPage);
