/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import useSWR from "swr";
import { AddPageOutline, HomeOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// components
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { WIKI_COLLECTIONS_KEY, WIKI_PAGES_KEY } from "../swr-keys";
import { useCreateWikiPage } from "../hooks/use-create-wiki-page";
import { WikiCollectionsSection } from "./collections-section";
import { WikiFavoritesSection, WikiMyPagesSection } from "./personal-sections";

export const WikiSidebar = observer(function WikiSidebar() {
  // router
  const { workspaceSlug } = useParams();
  const pathname = usePathname();
  // store hooks
  const { fetchPagesList, fetchCollections, canCurrentUserCreatePage } = usePageStore(EPageStoreType.WORKSPACE);
  const { createWikiPage, isCreating } = useCreateWikiPage();
  const { t } = useTranslation();
  // derived values
  const slug = workspaceSlug?.toString();
  const homeHref = `/${slug}/knowledge`;
  const isHomeActive = pathname.replace(/\/$/, "") === homeHref;

  // fetch what the tree needs
  useSWR(slug ? WIKI_PAGES_KEY(slug) : null, slug ? () => fetchPagesList(slug) : null, {
    revalidateOnFocus: true,
  });
  useSWR(slug ? WIKI_COLLECTIONS_KEY(slug) : null, slug ? () => fetchCollections(slug) : null, {
    revalidateOnFocus: true,
  });

  return (
    <SidebarWrapper
      title="Wiki"
      quickActions={
        canCurrentUserCreatePage ? (
          <button
            type="button"
            disabled={isCreating}
            onClick={() => createWikiPage()}
            className="flex w-full items-center gap-2 rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-13 font-medium text-secondary hover:bg-layer-1 disabled:opacity-60"
          >
            <AddPageOutline className="size-4 text-icon-tertiary" />
            New page
          </button>
        ) : undefined
      }
    >
      <div className="flex flex-col gap-4">
        <Link
          href={homeHref}
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-13 font-medium text-secondary hover:bg-layer-transparent-hover",
            { "bg-layer-transparent-selected text-primary": isHomeActive }
          )}
        >
          <HomeOutline className="size-4 text-icon-tertiary" />
          {t("sidebar.home")}
        </Link>
        <WikiCollectionsSection />
        <WikiFavoritesSection />
        <WikiMyPagesSection />
      </div>
    </SidebarWrapper>
  );
});
