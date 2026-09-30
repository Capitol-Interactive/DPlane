/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TWikiCollection, TWikiCollectionDeleteMode } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type TDeleteCollectionModalProps = {
  isOpen: boolean;
  onClose: () => void;
  collection: TWikiCollection;
  // called after the collection was deleted
  onDeleted?: () => void;
};

type TDeleteOption = { key: TWikiCollectionDeleteMode["mode"]; title: string; description: string };

export const WikiDeleteCollectionModal = observer(function WikiDeleteCollectionModal(
  props: TDeleteCollectionModalProps
) {
  const { isOpen, onClose, collection, onDeleted } = props;
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { deleteCollection, sortedCollectionIds, getCollectionById } = usePageStore(EPageStoreType.WORKSPACE);
  const { t } = useTranslation();
  // derived values
  const otherCollections = sortedCollectionIds
    .filter((id) => id !== collection.id)
    .map((id) => getCollectionById(id))
    .filter((item): item is TWikiCollection => !!item);
  const pageCount = collection.page_count ?? 0;
  const canTransfer = otherCollections.length > 0;
  // states
  const [mode, setMode] = useState<TWikiCollectionDeleteMode["mode"]>("delete_pages");
  const [targetId, setTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setMode(pageCount > 0 && canTransfer ? "transfer" : "delete_pages");
    setTargetId(null);
  }, [isOpen, pageCount, canTransfer]);

  const options: TDeleteOption[] = [
    ...(canTransfer
      ? [
          {
            key: "transfer" as const,
            title: t("wiki_collections.delete_modal.transfer_title"),
            description: t("wiki_collections.delete_modal.transfer_description"),
          },
        ]
      : []),
    {
      key: "delete_pages",
      title: t("wiki_collections.delete_modal.delete_with_pages_title"),
      description: t("wiki_collections.delete_modal.delete_with_pages_description"),
    },
  ];

  const handleDelete = async () => {
    if (!workspaceSlug) return;
    if (mode === "transfer" && !targetId) {
      setToast({ type: "error", title: "Error!", message: t("wiki_collections.toasts.target_required") });
      return;
    }
    setIsDeleting(true);
    try {
      await deleteCollection(
        workspaceSlug.toString(),
        collection.id,
        mode === "transfer" && targetId ? { mode, targetCollectionId: targetId } : { mode: "delete_pages" }
      );
      setToast({
        type: "success",
        title: "Success!",
        message: t(
          mode === "transfer"
            ? "wiki_collections.toasts.transferred_deleted"
            : "wiki_collections.toasts.deleted_with_pages"
        ),
      });
      onClose();
      onDeleted?.();
    } catch {
      setToast({ type: "error", title: "Error!", message: t("wiki_collections.toasts.delete_error") });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="md">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("wiki_collections.delete_modal.title")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody tabIndex={0}>
            <div className="flex flex-col gap-4">
              <p className="text-13 text-secondary">
                <span className="font-medium text-primary">{collection.name}</span>
                {pageCount > 0 && <> — {t("wiki_collections.delete_modal.page_count", { pageCount })}</>}
              </p>
              {pageCount > 0 && (
                <div className="flex flex-col gap-2" role="radiogroup">
                  {options.map((option) => (
                    <div
                      key={option.key}
                      className={cn("flex items-start gap-3 rounded-md border border-subtle p-3 hover:bg-layer-1", {
                        "border-strong bg-layer-1": mode === option.key,
                      })}
                    >
                      <input
                        id={`wiki-collection-delete-${option.key}`}
                        type="radio"
                        name="wiki-collection-delete-mode"
                        className="mt-0.5"
                        checked={mode === option.key}
                        onChange={() => setMode(option.key)}
                      />
                      <label
                        htmlFor={`wiki-collection-delete-${option.key}`}
                        className="flex cursor-pointer flex-col gap-0.5"
                      >
                        <span className="text-13 font-medium text-primary">{option.title}</span>
                        <span className="text-12 text-tertiary">{option.description}</span>
                      </label>
                    </div>
                  ))}
                </div>
              )}
              {mode === "transfer" && pageCount > 0 && (
                <div className="flex flex-col gap-2">
                  <span className="text-13 font-medium text-secondary">
                    {t("wiki_collections.delete_modal.transfer_target_label")}
                  </span>
                  <Select<string> value={targetId} onValueChange={(next) => setTargetId(next ?? null)}>
                    <SelectTrigger
                      size="lg"
                      placeholder={t("wiki_collections.delete_modal.transfer_target_placeholder")}
                    />
                    <SelectContent side="bottom" align="start">
                      <SelectList>
                        {otherCollections.map((item) => (
                          <SelectItem key={item.id} value={item.id} size="lg" label={item.name} />
                        ))}
                      </SelectList>
                    </SelectContent>
                  </Select>
                  <span className="text-12 text-tertiary">{t("wiki_collections.delete_modal.transfer_warning")}</span>
                </div>
              )}
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={onClose} />
          <Button
            variant="danger"
            size="md"
            stretch="auto"
            label={t("wiki_collections.delete_modal.submit")}
            loading={isDeleting}
            onClick={handleDelete}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});
