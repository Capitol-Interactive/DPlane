/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { computed, makeObservable } from "mobx";
import { computedFn } from "mobx-utils";
// constants
import { EPageAccess, EUserPermissions } from "@plane/constants";
import type { TPage } from "@plane/types";
// plane web store
import type { RootStore } from "@/store/root.store";
// services
import { WorkspacePageService } from "@/services/page";
// store
import { BasePage } from "./base-page";
import type { TPageInstance } from "./base-page";

const workspacePageService = new WorkspacePageService();

export type TWorkspacePage = TPageInstance;

/**
 * A wiki page: a page that lives in the workspace instead of a project. Permissions come from the
 * workspace role, and every request goes through the workspace wiki API.
 */
export class WorkspacePage extends BasePage implements TWorkspacePage {
  constructor(store: RootStore, page: TPage) {
    // required fields for API calls
    const { workspaceSlug } = store.router;
    const getRequiredFields = () => {
      if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
      return { slug: workspaceSlug, pageId: page.id };
    };
    // initialize base instance
    super(store, page, {
      update: async (payload) => {
        const { slug, pageId } = getRequiredFields();
        return await workspacePageService.update(slug, pageId, payload);
      },
      updateDescription: async (document) => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.updateDescription(slug, pageId, document);
      },
      updateAccess: async (payload) => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.updateAccess(slug, pageId, payload);
      },
      lock: async () => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.lock(slug, pageId);
      },
      unlock: async () => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.unlock(slug, pageId);
      },
      archive: async () => {
        const { slug, pageId } = getRequiredFields();
        return await workspacePageService.archive(slug, pageId);
      },
      restore: async () => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.restore(slug, pageId);
      },
      duplicate: async () => {
        const { slug, pageId } = getRequiredFields();
        return await workspacePageService.duplicate(slug, pageId);
      },
      addToFavorites: async () => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.addToFavorites(slug, pageId);
      },
      removeFromFavorites: async () => {
        const { slug, pageId } = getRequiredFields();
        await workspacePageService.removeFromFavorites(slug, pageId);
      },
    });
    makeObservable(this, {
      // computed
      canCurrentUserAccessPage: computed,
      canCurrentUserEditPage: computed,
      canCurrentUserDuplicatePage: computed,
      canCurrentUserLockPage: computed,
      canCurrentUserChangeAccess: computed,
      canCurrentUserArchivePage: computed,
      canCurrentUserDeletePage: computed,
      canCurrentUserFavoritePage: computed,
      canCurrentUserMovePage: computed,
      isContentEditable: computed,
    });
  }

  private get currentUserWorkspaceRole() {
    const { workspaceSlug } = this.rootStore.router;
    if (!workspaceSlug) return undefined;
    return this.rootStore.user.permission.getWorkspaceRoleByWorkspaceSlug(workspaceSlug);
  }

  private get isMemberOrAbove() {
    const role = this.currentUserWorkspaceRole;
    return !!role && role >= EUserPermissions.MEMBER;
  }

  private get isAdmin() {
    return this.currentUserWorkspaceRole === EUserPermissions.ADMIN;
  }

  /**
   * @description returns true if the current logged in user can access the page
   */
  get canCurrentUserAccessPage() {
    return this.access === EPageAccess.PUBLIC || this.isCurrentUserOwner;
  }

  /**
   * @description returns true if the current logged in user can edit the page
   */
  get canCurrentUserEditPage() {
    return this.isMemberOrAbove && this.canCurrentUserAccessPage;
  }

  /**
   * @description returns true if the current logged in user can create a duplicate the page
   */
  get canCurrentUserDuplicatePage() {
    return this.isMemberOrAbove;
  }

  /**
   * @description returns true if the current logged in user can lock the page
   */
  get canCurrentUserLockPage() {
    return this.isCurrentUserOwner || this.isAdmin;
  }

  /**
   * @description returns true if the current logged in user can change the access of the page.
   * The API only lets the owner change access.
   */
  get canCurrentUserChangeAccess() {
    return this.isCurrentUserOwner;
  }

  /**
   * @description returns true if the current logged in user can archive the page
   */
  get canCurrentUserArchivePage() {
    return this.isCurrentUserOwner || this.isAdmin;
  }

  /**
   * @description returns true if the current logged in user can delete the page
   */
  get canCurrentUserDeletePage() {
    return this.isCurrentUserOwner || this.isAdmin;
  }

  /**
   * @description returns true if the current logged in user can favorite the page
   */
  get canCurrentUserFavoritePage() {
    return this.isMemberOrAbove;
  }

  /**
   * @description returns true if the current logged in user can move the page
   */
  get canCurrentUserMovePage() {
    return this.canCurrentUserEditPage;
  }

  /**
   * @description returns true if the page can be edited
   */
  get isContentEditable() {
    return !this.archived_at && !this.is_locked && this.canCurrentUserEditPage;
  }

  getRedirectionLink = computedFn(() => {
    const { workspaceSlug } = this.rootStore.router;
    return `/${workspaceSlug}/knowledge/${this.id}`;
  });
}
