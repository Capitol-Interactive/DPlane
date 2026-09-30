/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { orderBy, set, unset } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// plane imports
import { EUserPermissions } from "@plane/constants";
import type { TPage, TWikiCollection, TWikiCollectionDeleteMode, TWikiCollectionPayload } from "@plane/types";
// services
import { WikiCollectionService, WorkspacePageService } from "@/services/page";
// store
import type { CoreRootStore } from "../root.store";
import type { TWorkspacePage } from "./workspace-page";
import { WorkspacePage } from "./workspace-page";

type TLoader = "init-loader" | "mutation-loader" | undefined;

type TError = { title: string; description: string };

export type TWikiPageMove = { parent?: string | null; collection?: string | null };

export interface IWorkspacePageStore {
  // observables
  loader: TLoader;
  collectionsLoader: TLoader;
  data: Record<string, TWorkspacePage>; // pageId => Page
  collections: Record<string, TWikiCollection>; // collectionId => Collection
  error: TError | undefined;
  // computed
  isAnyPageAvailable: boolean;
  canCurrentUserCreatePage: boolean;
  sortedCollectionIds: string[];
  favoritePageIds: string[];
  myPageIds: string[];
  // helper actions
  getPageById: (pageId: string) => TWorkspacePage | undefined;
  getCollectionById: (collectionId: string) => TWikiCollection | undefined;
  getRootPageIdsByCollection: (collectionId: string) => string[];
  getChildPageIds: (parentId: string) => string[];
  getPageAncestorIds: (pageId: string) => string[];
  getRootPageId: (pageId: string) => string | undefined;
  // page actions
  fetchPagesList: (workspaceSlug: string) => Promise<TPage[] | undefined>;
  fetchPageDetails: (
    workspaceSlug: string,
    pageId: string,
    options?: { trackVisit?: boolean }
  ) => Promise<TPage | undefined>;
  createPage: (pageData: Partial<TPage>) => Promise<TPage | undefined>;
  removePage: (params: { pageId: string; shouldSync?: boolean }) => Promise<void>;
  movePage: (pageId: string, target: TWikiPageMove) => Promise<void>;
  // collection actions
  fetchCollections: (workspaceSlug: string) => Promise<TWikiCollection[] | undefined>;
  createCollection: (workspaceSlug: string, data: TWikiCollectionPayload) => Promise<TWikiCollection>;
  updateCollection: (workspaceSlug: string, collectionId: string, data: TWikiCollectionPayload) => Promise<void>;
  deleteCollection: (workspaceSlug: string, collectionId: string, options: TWikiCollectionDeleteMode) => Promise<void>;
}

// display order of pages in the tree: manual order first, then oldest first
const sortPages = (pages: TWorkspacePage[]) =>
  orderBy(pages, [(page) => page.sort_order ?? 0, (page) => new Date(page.created_at ?? 0).getTime()], ["asc", "asc"]);

export class WorkspacePageStore implements IWorkspacePageStore {
  // observables
  loader: TLoader = "init-loader";
  collectionsLoader: TLoader = "init-loader";
  data: Record<string, TWorkspacePage> = {}; // pageId => Page
  collections: Record<string, TWikiCollection> = {}; // collectionId => Collection
  error: TError | undefined = undefined;
  // service
  service: WorkspacePageService;
  collectionService: WikiCollectionService;
  rootStore: CoreRootStore;

  constructor(private store: CoreRootStore) {
    makeObservable(this, {
      // observables
      loader: observable.ref,
      collectionsLoader: observable.ref,
      data: observable,
      collections: observable,
      error: observable,
      // computed
      isAnyPageAvailable: computed,
      canCurrentUserCreatePage: computed,
      sortedCollectionIds: computed,
      favoritePageIds: computed,
      myPageIds: computed,
      // actions
      fetchPagesList: action,
      fetchPageDetails: action,
      createPage: action,
      removePage: action,
      movePage: action,
      fetchCollections: action,
      createCollection: action,
      updateCollection: action,
      deleteCollection: action,
    });
    this.rootStore = store;
    this.service = new WorkspacePageService();
    this.collectionService = new WikiCollectionService();
  }

  /**
   * @description check if any page is available
   */
  get isAnyPageAvailable() {
    if (this.loader) return true;
    return Object.keys(this.data).length > 0;
  }

  /**
   * @description returns true if the current logged in user can create a page
   */
  get canCurrentUserCreatePage() {
    const { workspaceSlug } = this.store.router;
    if (!workspaceSlug) return false;
    const role = this.store.user.permission.getWorkspaceRoleByWorkspaceSlug(workspaceSlug);
    return !!role && role >= EUserPermissions.MEMBER;
  }

  /**
   * @description collection ids in display order
   */
  get sortedCollectionIds() {
    return orderBy(Object.values(this.collections), "sort_order").map((collection) => collection.id);
  }

  private get activePages() {
    return Object.values(this.data).filter((page) => !!page.id && !page.archived_at);
  }

  /**
   * @description pages the current user favorited
   */
  get favoritePageIds() {
    return sortPages(this.activePages.filter((page) => page.is_favorite)).map((page) => page.id as string);
  }

  /**
   * @description root pages owned by the current user that are not part of any collection
   */
  get myPageIds() {
    const currentUserId = this.store.user.data?.id;
    if (!currentUserId) return [];
    return sortPages(
      this.activePages.filter((page) => !page.parent && !page.collection && page.owned_by === currentUserId)
    ).map((page) => page.id as string);
  }

  getPageById = computedFn((pageId: string) => this.data?.[pageId] || undefined);

  getCollectionById = computedFn((collectionId: string) => this.collections?.[collectionId] || undefined);

  /**
   * @description root pages of a collection, in display order
   */
  getRootPageIdsByCollection = computedFn((collectionId: string) =>
    sortPages(this.activePages.filter((page) => !page.parent && page.collection === collectionId)).map(
      (page) => page.id as string
    )
  );

  /**
   * @description nested pages of a page, in display order
   */
  getChildPageIds = computedFn((parentId: string) =>
    sortPages(this.activePages.filter((page) => page.parent === parentId)).map((page) => page.id as string)
  );

  /**
   * @description ids of the pages above the given page, from the root down to its direct parent
   */
  getPageAncestorIds = computedFn((pageId: string) => {
    const ancestors: string[] = [];
    const visited = new Set<string>([pageId]);
    let current = this.data[pageId]?.parent;
    while (current && !visited.has(current)) {
      ancestors.unshift(current);
      visited.add(current);
      current = this.data[current]?.parent;
    }
    return ancestors;
  });

  /**
   * @description the root page of the tree the page belongs to (the page itself if it has no parent)
   */
  getRootPageId = computedFn((pageId: string) => this.getPageAncestorIds(pageId)[0] ?? this.data[pageId]?.id);

  private upsertPage = (page: TPage, options?: { shouldUpdateName?: boolean }) => {
    if (!page?.id) return;
    const instance = this.data[page.id];
    if (instance) instance.mutateProperties(page, options?.shouldUpdateName ?? false);
    else set(this.data, [page.id], new WorkspacePage(this.store, page));
  };

  /**
   * @description fetch the (non archived) wiki pages the current user can see
   */
  fetchPagesList = async (workspaceSlug: string) => {
    try {
      if (!workspaceSlug) return undefined;
      runInAction(() => {
        this.loader = Object.keys(this.data).length > 0 ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });

      const pages = await this.service.fetchAll(workspaceSlug);

      runInAction(() => {
        const fetchedIds = new Set<string>();
        pages.forEach((page) => {
          if (page.id) fetchedIds.add(page.id);
          this.upsertPage(page);
        });
        // pages that are no longer returned were deleted, archived or hidden from this user
        Object.values(this.data).forEach((page) => {
          if (page.id && !fetchedIds.has(page.id) && !page.archived_at) unset(this.data, [page.id]);
        });
        this.loader = undefined;
      });

      return pages;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: "Failed",
          description: "Failed to fetch the pages, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description fetch the details of a page
   */
  fetchPageDetails = async (workspaceSlug: string, pageId: string, options?: { trackVisit?: boolean }) => {
    try {
      if (!workspaceSlug || !pageId) return undefined;

      runInAction(() => {
        this.error = undefined;
      });

      const page = await this.service.fetchById(workspaceSlug, pageId, options?.trackVisit ?? true);
      runInAction(() => {
        this.upsertPage(page);
      });

      return page;
    } catch (error) {
      runInAction(() => {
        this.error = {
          title: "Failed",
          description: "Failed to fetch the page, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description create a page. Use `parent` to nest it and `collection` to place it in a collection.
   */
  createPage = async (pageData: Partial<TPage>) => {
    try {
      const { workspaceSlug } = this.store.router;
      if (!workspaceSlug) return undefined;

      runInAction(() => {
        this.loader = "mutation-loader";
        this.error = undefined;
      });

      const page = await this.service.create(workspaceSlug, pageData);
      runInAction(() => {
        this.upsertPage(page);
        this.loader = undefined;
      });

      return page;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: "Failed",
          description: "Failed to create a page, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description delete a page. Its sub pages move up to the root.
   */
  removePage = async ({ pageId }: { pageId: string; shouldSync?: boolean }) => {
    try {
      const { workspaceSlug } = this.store.router;
      if (!workspaceSlug || !pageId) return undefined;

      await this.service.remove(workspaceSlug, pageId);
      runInAction(() => {
        Object.values(this.data).forEach((page) => {
          if (page.parent === pageId) page.mutateProperties({ parent: null });
        });
        unset(this.data, [pageId]);
      });
    } catch (error) {
      runInAction(() => {
        this.error = {
          title: "Failed",
          description: "Failed to delete a page, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description move a page under another page or into a collection (or back to the root with null values)
   */
  movePage = async (pageId: string, target: TWikiPageMove) => {
    const { workspaceSlug } = this.store.router;
    const page = this.data[pageId];
    if (!workspaceSlug || !page) return;

    const previous = { parent: page.parent, collection: page.collection };
    runInAction(() => {
      page.mutateProperties({
        parent: target.parent ?? null,
        collection: target.parent ? null : (target.collection ?? null),
      });
    });
    try {
      const updated = await this.service.update(workspaceSlug, pageId, target);
      runInAction(() => {
        page.mutateProperties(
          { parent: updated.parent ?? null, collection: updated.collection ?? null, sort_order: updated.sort_order },
          false
        );
      });
    } catch (error) {
      runInAction(() => {
        page.mutateProperties(previous);
      });
      throw error;
    }
  };

  /**
   * @description fetch the wiki collections of the workspace
   */
  fetchCollections = async (workspaceSlug: string) => {
    try {
      if (!workspaceSlug) return undefined;
      runInAction(() => {
        this.collectionsLoader = Object.keys(this.collections).length > 0 ? "mutation-loader" : "init-loader";
      });
      const collections = await this.collectionService.fetchAll(workspaceSlug);
      runInAction(() => {
        this.collections = collections.reduce(
          (acc, collection) => {
            acc[collection.id] = collection;
            return acc;
          },
          {} as Record<string, TWikiCollection>
        );
        this.collectionsLoader = undefined;
      });
      return collections;
    } catch (error) {
      runInAction(() => {
        this.collectionsLoader = undefined;
      });
      throw error;
    }
  };

  createCollection = async (workspaceSlug: string, data: TWikiCollectionPayload) => {
    const collection = await this.collectionService.create(workspaceSlug, data);
    runInAction(() => {
      set(this.collections, [collection.id], collection);
    });
    return collection;
  };

  updateCollection = async (workspaceSlug: string, collectionId: string, data: TWikiCollectionPayload) => {
    const collection = await this.collectionService.update(workspaceSlug, collectionId, data);
    runInAction(() => {
      set(this.collections, [collectionId], collection);
    });
  };

  deleteCollection = async (workspaceSlug: string, collectionId: string, options: TWikiCollectionDeleteMode) => {
    await this.collectionService.remove(workspaceSlug, collectionId, options);
    runInAction(() => {
      const rootPages = Object.values(this.data).filter((page) => page.collection === collectionId);
      if (options.mode === "transfer") {
        rootPages.forEach((page) => page.mutateProperties({ collection: options.targetCollectionId }));
      } else {
        // remove the collection's pages together with everything nested under them
        const removed = new Set<string>(rootPages.map((page) => page.id as string));
        let added = true;
        while (added) {
          added = false;
          Object.values(this.data).forEach((page) => {
            if (page.id && page.parent && removed.has(page.parent) && !removed.has(page.id)) {
              removed.add(page.id);
              added = true;
            }
          });
        }
        removed.forEach((pageId) => unset(this.data, [pageId]));
      }
      unset(this.collections, [collectionId]);
    });
  };
}
