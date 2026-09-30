/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { FolderOutline, LibraryOutline, PagesOutline } from "@makeplane/propel/icons";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { Header } from "@plane/blocks/layout";
import { getPageName } from "@plane/utils";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { PageHeaderActions } from "@/components/pages/header/actions";
import { PageSyncingBadge } from "@/components/pages/header/syncing-badge";
// hooks
import { EPageStoreType, usePage, usePageStore } from "@/hooks/store";

const storeType = EPageStoreType.WORKSPACE;

export const WikiHeader = observer(function WikiHeader() {
  // router
  const { workspaceSlug, pageId } = useParams();
  // store hooks
  const { getPageAncestorIds, getPageById, getCollectionById, getRootPageId } = usePageStore(storeType);
  const page = usePage({ pageId: pageId?.toString() ?? "", storeType });
  // derived values
  const homeHref = `/${workspaceSlug}/knowledge`;
  const ancestorIds = pageId ? getPageAncestorIds(pageId.toString()) : [];
  const rootPageId = pageId ? getRootPageId(pageId.toString()) : undefined;
  const collection = rootPageId ? getCollectionById(getPageById(rootPageId)?.collection ?? "") : undefined;

  return (
    <Header>
      <Header.LeftItem>
        <div>
          <Breadcrumbs>
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink
                  label="Wiki"
                  href={homeHref}
                  icon={<LibraryOutline className="size-4 text-tertiary" />}
                />
              }
              isLast={!page}
            />
            {page && collection && (
              <Breadcrumbs.Item
                component={
                  <BreadcrumbLink label={collection.name} icon={<FolderOutline className="size-4 text-tertiary" />} />
                }
              />
            )}
            {page &&
              ancestorIds.map((ancestorId) => (
                <Breadcrumbs.Item
                  key={ancestorId}
                  component={
                    <BreadcrumbLink
                      label={getPageName(getPageById(ancestorId)?.name)}
                      href={`/${workspaceSlug}/knowledge/${ancestorId}`}
                      icon={<PagesOutline className="size-4 text-tertiary" />}
                    />
                  }
                />
              ))}
            {page && (
              <Breadcrumbs.Item
                component={
                  <BreadcrumbLink
                    label={getPageName(page.name)}
                    href={`/${workspaceSlug}/knowledge/${page.id}`}
                    icon={<PagesOutline className="size-4 text-tertiary" />}
                  />
                }
                isLast
              />
            )}
          </Breadcrumbs>
        </div>
      </Header.LeftItem>
      {page && (
        <Header.RightItem>
          <PageSyncingBadge syncStatus={page.isSyncingWithServer} />
          <PageHeaderActions page={page} storeType={storeType} />
        </Header.RightItem>
      )}
    </Header>
  );
});
