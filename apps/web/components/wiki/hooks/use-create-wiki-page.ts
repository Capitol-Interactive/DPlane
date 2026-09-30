/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { setToast } from "@plane/blocks/toast";
import type { TPage } from "@plane/types";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import { useAppRouter } from "@/hooks/use-app-router";

/**
 * Creates a wiki page (optionally nested under a page or placed in a collection) and opens it.
 */
export const useCreateWikiPage = () => {
  // router
  const router = useAppRouter();
  const { workspaceSlug } = useParams();
  // store hooks
  const { createPage } = usePageStore(EPageStoreType.WORKSPACE);
  // states
  const [isCreating, setIsCreating] = useState(false);

  const createWikiPage = useCallback(
    async (payload: Partial<TPage> = {}) => {
      if (!workspaceSlug) return;
      setIsCreating(true);
      try {
        const page = await createPage(payload);
        if (page?.id) router.push(`/${workspaceSlug}/knowledge/${page.id}`);
        return page;
      } catch (error) {
        setToast({
          type: "error",
          title: "Error!",
          message: (error as { error?: string } | undefined)?.error ?? "Page could not be created. Please try again.",
        });
      } finally {
        setIsCreating(false);
      }
    },
    [createPage, router, workspaceSlug]
  );

  return { createWikiPage, isCreating };
};
