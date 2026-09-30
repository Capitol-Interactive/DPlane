/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { WIKI_COLLECTIONS_KEY, WIKI_PAGES_KEY } from "./swr-keys";

// Wait until the workspace has finished its own startup requests so the prefetch never competes with them.
const PREFETCH_DELAY_MS = 1500;

/**
 * Loads the wiki pages and collections in the background shortly after the workspace opens, so the first
 * visit to Knowledge finds them already in the store instead of fetching on click. Renders nothing.
 */
export const WikiDataPrefetch = observer(function WikiDataPrefetch() {
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { fetchPagesList, fetchCollections } = usePageStore(EPageStoreType.WORKSPACE);
  const { allowPermissions } = useUserPermissions();
  // states
  const [isReady, setIsReady] = useState(false);
  // derived values
  const slug = workspaceSlug?.toString();
  // guests only see their own wiki pages, so they are not worth a background request
  const canPrefetch =
    !!slug && allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE);

  useEffect(() => {
    const timer = setTimeout(() => setIsReady(true), PREFETCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, []);

  const shouldFetch = isReady && canPrefetch && !!slug;
  useSWR(shouldFetch ? WIKI_PAGES_KEY(slug) : null, shouldFetch ? () => fetchPagesList(slug) : null, {
    revalidateOnFocus: false,
    revalidateIfStale: false,
  });
  useSWR(shouldFetch ? WIKI_COLLECTIONS_KEY(slug) : null, shouldFetch ? () => fetchCollections(slug) : null, {
    revalidateOnFocus: false,
    revalidateIfStale: false,
  });

  return null;
});
