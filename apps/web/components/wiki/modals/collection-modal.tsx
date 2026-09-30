/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { FormEvent } from "react";
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
import { InputField } from "@makeplane/propel/components/input-field";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TWikiCollection } from "@plane/types";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type TWikiCollectionModalProps = {
  isOpen: boolean;
  onClose: () => void;
  // when provided the modal renames this collection, otherwise it creates a new one
  collection?: TWikiCollection;
};

const MAX_NAME_LENGTH = 255;

export const WikiCollectionModal = observer(function WikiCollectionModal(props: TWikiCollectionModalProps) {
  const { isOpen, onClose, collection } = props;
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { createCollection, updateCollection } = usePageStore(EPageStoreType.WORKSPACE);
  const { t } = useTranslation();
  // states
  const [name, setName] = useState(collection?.name ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  // derived values
  const isEditing = !!collection;
  const trimmedName = name.trim();
  const isNameTooLong = trimmedName.length > MAX_NAME_LENGTH;

  useEffect(() => {
    if (isOpen) setName(collection?.name ?? "");
  }, [isOpen, collection?.name]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!workspaceSlug || !trimmedName || isNameTooLong) return;
    setIsSubmitting(true);
    try {
      if (collection) await updateCollection(workspaceSlug.toString(), collection.id, { name: trimmedName });
      else await createCollection(workspaceSlug.toString(), { name: trimmedName });
      setToast({
        type: "success",
        title: "Success!",
        message: t(isEditing ? "wiki_collections.toasts.renamed" : "wiki_collections.toasts.created"),
      });
      onClose();
    } catch {
      setToast({
        type: "error",
        title: "Error!",
        message: t(isEditing ? "wiki_collections.toasts.rename_error" : "wiki_collections.toasts.create_error"),
      });
    } finally {
      setIsSubmitting(false);
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
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>
                  {t(isEditing ? "wiki_collections.edit_modal.title" : "wiki_collections.create_modal.title")}
                </DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody tabIndex={0}>
              <InputField
                id="name"
                type="text"
                size="2xl"
                orientation="vertical"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t(
                  isEditing
                    ? "wiki_collections.form.name_placeholder_edit"
                    : "wiki_collections.form.name_placeholder_create"
                )}
                error={isNameTooLong ? t("wiki_collections.form.name_max_length") : undefined}
                required
                // the name is the dialog's only field; focus it on open
                // oxlint-disable-next-line jsx_a11y/no-autofocus
                autoFocus
              />
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={onClose} />
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              type="submit"
              label={t(isEditing ? "save" : "wiki_collections.create_modal.submit")}
              loading={isSubmitting}
              disabled={!trimmedName || isNameTooLong}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
});
