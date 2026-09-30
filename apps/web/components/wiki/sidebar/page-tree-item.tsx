/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { AddOutline, PagesOutline } from "@makeplane/propel/icons";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Icon } from "@makeplane/propel/components/icon";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { getPageName } from "@plane/utils";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { useCreateWikiPage } from "../hooks/use-create-wiki-page";
import { WikiTreeRow } from "./tree-row";

type TWikiPageTreeItemProps = {
  pageId: string;
  depth: number;
  // false renders the page as a flat row (favorites), true nests its sub pages underneath
  showChildren?: boolean;
};

export const WikiPageTreeItem = observer(function WikiPageTreeItem(props: TWikiPageTreeItemProps) {
  const { pageId, depth, showChildren = true } = props;
  // router
  const { workspaceSlug, pageId: activePageId } = useParams();
  // store hooks
  const { getPageById, getChildPageIds, getPageAncestorIds, canCurrentUserCreatePage } = usePageStore(
    EPageStoreType.WORKSPACE
  );
  const { createWikiPage, isCreating } = useCreateWikiPage();
  // states
  const [isOpen, setIsOpen] = useState(false);
  // derived values
  const page = getPageById(pageId);
  const childPageIds = showChildren ? getChildPageIds(pageId) : [];
  const isActive = activePageId === pageId;
  const containsActivePage = activePageId ? getPageAncestorIds(activePageId.toString()).includes(pageId) : false;

  // keep the branch of the open page expanded
  useEffect(() => {
    if (containsActivePage) setIsOpen(true);
  }, [containsActivePage]);

  if (!page) return null;

  const handleAddSubPage = async () => {
    const created = await createWikiPage({ parent: pageId });
    if (created) setIsOpen(true);
  };

  return (
    <>
      <WikiTreeRow
        depth={depth}
        label={getPageName(page.name)}
        icon={
          page.logo_props?.in_use ? (
            <Logo logo={page.logo_props} size={16} type="lucide" />
          ) : (
            <PagesOutline className="size-4 text-icon-tertiary" />
          )
        }
        href={`/${workspaceSlug}/knowledge/${pageId}`}
        isActive={isActive}
        isExpandable={childPageIds.length > 0}
        isOpen={isOpen}
        onToggle={() => setIsOpen((prev) => !prev)}
        actions={
          showChildren &&
          canCurrentUserCreatePage &&
          !page.is_locked && (
            <Tooltip label="Add a sub page">
              <IconButton
                variant="ghost"
                size="xs"
                aria-label="Add a sub page"
                disabled={isCreating}
                onClick={handleAddSubPage}
                icon={<Icon icon={AddOutline} />}
              />
            </Tooltip>
          )
        }
      />
      {isOpen && childPageIds.map((childId) => <WikiPageTreeItem key={childId} pageId={childId} depth={depth + 1} />)}
    </>
  );
});
