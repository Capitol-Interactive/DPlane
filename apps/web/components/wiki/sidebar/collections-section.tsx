/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import {
  AddOutline,
  DeleteOutline,
  EditOutline,
  FolderOutline,
  MoreHorizontalOutline,
  AddPageOutline,
} from "@makeplane/propel/icons";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { useTranslation } from "@plane/i18n";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import { useUser, useUserPermissions } from "@/hooks/store/user";
// local imports
import { useCreateWikiPage } from "../hooks/use-create-wiki-page";
import { WikiCollectionModal } from "../modals/collection-modal";
import { WikiDeleteCollectionModal } from "../modals/delete-collection-modal";
import { WikiPageTreeItem } from "./page-tree-item";
import { WikiSidebarSection } from "./section";
import { WikiTreeRow } from "./tree-row";

const WikiCollectionItem = observer(function WikiCollectionItem({ collectionId }: { collectionId: string }) {
  // router
  const { pageId: activePageId } = useParams();
  // store hooks
  const { getCollectionById, getRootPageIdsByCollection, getRootPageId, getPageById, canCurrentUserCreatePage } =
    usePageStore(EPageStoreType.WORKSPACE);
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();
  const { createWikiPage, isCreating } = useCreateWikiPage();
  // states
  const [isOpen, setIsOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  // derived values
  const collection = getCollectionById(collectionId);
  const rootPageIds = getRootPageIdsByCollection(collectionId);
  const activeRootPageId = activePageId ? getRootPageId(activePageId.toString()) : undefined;
  const containsActivePage = !!activeRootPageId && getPageById(activeRootPageId)?.collection === collectionId;
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const canManage = !!collection && (collection.owned_by === currentUser?.id || isAdmin);
  const { t } = useTranslation();

  // keep the collection of the open page expanded
  useEffect(() => {
    if (containsActivePage) setIsOpen(true);
  }, [containsActivePage]);

  if (!collection) return null;

  const handleAddPage = async () => {
    const created = await createWikiPage({ collection: collectionId });
    if (created) setIsOpen(true);
  };

  return (
    <>
      <WikiCollectionModal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} collection={collection} />
      <WikiDeleteCollectionModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        collection={collection}
      />
      <WikiTreeRow
        depth={0}
        label={collection.name}
        icon={
          collection.logo_props?.in_use ? (
            <Logo logo={collection.logo_props} size={16} type="lucide" />
          ) : (
            <FolderOutline className="size-4 text-icon-tertiary" />
          )
        }
        isExpandable
        isOpen={isOpen}
        onToggle={() => setIsOpen((prev) => !prev)}
        actions={
          <>
            {canCurrentUserCreatePage && (
              <Tooltip label="New page">
                <IconButton
                  variant="ghost"
                  size="xs"
                  aria-label="New page in collection"
                  disabled={isCreating}
                  onClick={handleAddPage}
                  icon={<Icon icon={AddOutline} />}
                />
              </Tooltip>
            )}
            {canManage && (
              <Menu>
                <MenuTrigger
                  render={
                    <button
                      type="button"
                      aria-label={t("wiki_collections.menu.collection_options")}
                      className="grid size-6 place-items-center rounded-sm text-icon-tertiary hover:bg-layer-transparent-active"
                    >
                      <MoreHorizontalOutline className="size-4" />
                    </button>
                  }
                />
                <MenuContent side="bottom" align="end">
                  {canCurrentUserCreatePage && (
                    <MenuItem
                      icon={<Icon icon={AddPageOutline} tint="secondary" />}
                      label={t("wiki_collections.menu.create_new_page")}
                      onClick={handleAddPage}
                    />
                  )}
                  <MenuItem
                    icon={<Icon icon={EditOutline} tint="secondary" />}
                    label={t("wiki_collections.menu.edit_collection")}
                    onClick={() => setIsEditModalOpen(true)}
                  />
                  <MenuItem
                    icon={<Icon icon={DeleteOutline} tint="secondary" />}
                    label={t("delete")}
                    onClick={() => setIsDeleteModalOpen(true)}
                  />
                </MenuContent>
              </Menu>
            )}
          </>
        }
      />
      {isOpen &&
        (rootPageIds.length > 0 ? (
          rootPageIds.map((pageId) => <WikiPageTreeItem key={pageId} pageId={pageId} depth={1} />)
        ) : (
          <span className="px-3 py-1 text-12 text-placeholder" style={{ paddingLeft: 4 + 16 + 20 }}>
            {t("wiki_collections.list.no_pages_title")}
          </span>
        ))}
    </>
  );
});

export const WikiCollectionsSection = observer(function WikiCollectionsSection() {
  // store hooks
  const { sortedCollectionIds, canCurrentUserCreatePage } = usePageStore(EPageStoreType.WORKSPACE);
  const { t } = useTranslation();
  // states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  return (
    <>
      <WikiCollectionModal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} />
      <WikiSidebarSection
        title="Collections"
        storageKey="wiki_sidebar_collections_open"
        trailing={
          canCurrentUserCreatePage ? (
            <Tooltip label={t("wiki_collections.create_modal.title")}>
              <IconButton
                variant="ghost"
                size="xs"
                aria-label={t("wiki_collections.create_modal.title")}
                onClick={() => setIsCreateModalOpen(true)}
                icon={<Icon icon={AddOutline} />}
              />
            </Tooltip>
          ) : undefined
        }
      >
        {sortedCollectionIds.length === 0 ? (
          <span className="px-2 py-1 text-12 font-medium text-placeholder">No collections yet</span>
        ) : (
          sortedCollectionIds.map((collectionId) => (
            <WikiCollectionItem key={collectionId} collectionId={collectionId} />
          ))
        )}
      </WikiSidebarSection>
    </>
  );
});
