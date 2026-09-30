/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { orderBy } from "lodash-es";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { AddPageOutline, PagesOutline } from "@makeplane/propel/icons";
import { Button } from "@makeplane/propel/components/button";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { getPageName } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { useCreateWikiPage } from "@/components/wiki/hooks/use-create-wiki-page";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

const RECENT_PAGES_LIMIT = 12;

function KnowledgePage() {
  // router
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  // store hooks
  const { data, loader, fetchPagesList, canCurrentUserCreatePage } = usePageStore(EPageStoreType.WORKSPACE);
  const { createWikiPage, isCreating } = useCreateWikiPage();
  // the sidebar fetches with the same key, so this shares its request
  useSWR(slug ? `WIKI_PAGES_${slug}` : null, slug ? () => fetchPagesList(slug) : null, { revalidateOnFocus: true });
  // derived values
  // computed on render: `data` is a MobX observable, so a memo keyed on it would never refresh
  const recentPages = orderBy(
    Object.values(data).filter((page) => page.id && !page.archived_at),
    (page) => new Date(page.updated_at ?? 0).getTime(),
    "desc"
  ).slice(0, RECENT_PAGES_LIMIT);

  return (
    <>
      <PageHead title="Wiki" />
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-10">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-20 font-semibold text-primary">Wiki</h1>
            <p className="text-13 text-tertiary">Docs, playbooks and everything your team needs to know.</p>
          </div>
          {canCurrentUserCreatePage && (
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              label="New page"
              loading={isCreating}
              onClick={() => createWikiPage()}
            />
          )}
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-13 font-semibold text-placeholder">Recently updated</h2>
          {recentPages.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-subtle px-6 py-12 text-center">
              <AddPageOutline className="size-6 text-icon-tertiary" />
              <p className="text-13 text-tertiary">
                {loader ? "Loading pages…" : "No pages yet. Create your first page to get started."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle">
              {recentPages.map((page) => (
                <Link
                  key={page.id}
                  href={`/${slug}/knowledge/${page.id}`}
                  className="flex items-center gap-3 px-4 py-2.5 text-13 text-secondary hover:bg-layer-1"
                >
                  {page.logo_props?.in_use ? (
                    <Logo logo={page.logo_props} size={16} type="lucide" />
                  ) : (
                    <PagesOutline className="size-4 text-icon-tertiary" />
                  )}
                  <span className="flex-1 truncate font-medium text-primary">{getPageName(page.name)}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default observer(KnowledgePage);
