/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { WikiPageTreeItem } from "./page-tree-item";
import { WikiSidebarSection } from "./section";

export const WikiFavoritesSection = observer(function WikiFavoritesSection() {
  const { favoritePageIds } = usePageStore(EPageStoreType.WORKSPACE);

  // nothing to show until the user favorites a page
  if (favoritePageIds.length === 0) return null;

  return (
    <WikiSidebarSection title="Favorites" storageKey="wiki_sidebar_favorites_open">
      {favoritePageIds.map((pageId) => (
        <WikiPageTreeItem key={pageId} pageId={pageId} depth={0} showChildren={false} />
      ))}
    </WikiSidebarSection>
  );
});

export const WikiMyPagesSection = observer(function WikiMyPagesSection() {
  const { myPageIds } = usePageStore(EPageStoreType.WORKSPACE);

  if (myPageIds.length === 0) return null;

  return (
    <WikiSidebarSection title="My pages" storageKey="wiki_sidebar_my_pages_open">
      {myPageIds.map((pageId) => (
        <WikiPageTreeItem key={pageId} pageId={pageId} depth={0} />
      ))}
    </WikiSidebarSection>
  );
});
