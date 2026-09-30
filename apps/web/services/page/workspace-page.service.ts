/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type { TDocumentPayload, TPage } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

// Workspace-level (wiki) pages: same operations as project pages, without a project in the path.
export class WorkspacePageService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private basePath(workspaceSlug: string) {
    return `/api/workspaces/${workspaceSlug}/wiki/pages`;
  }

  async fetchAll(workspaceSlug: string): Promise<TPage[]> {
    return this.get(`${this.basePath(workspaceSlug)}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchArchived(workspaceSlug: string): Promise<TPage[]> {
    return this.get(`${this.basePath(workspaceSlug)}/`, { params: { archived: true } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchById(workspaceSlug: string, pageId: string, trackVisit: boolean): Promise<TPage> {
    return this.get(`${this.basePath(workspaceSlug)}/${pageId}/`, { params: { track_visit: trackVisit } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: Partial<TPage>): Promise<TPage> {
    return this.post(`${this.basePath(workspaceSlug)}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, pageId: string, data: Partial<TPage>): Promise<TPage> {
    return this.patch(`${this.basePath(workspaceSlug)}/${pageId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateAccess(workspaceSlug: string, pageId: string, data: Pick<TPage, "access">): Promise<void> {
    return this.post(`${this.basePath(workspaceSlug)}/${pageId}/access/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug)}/${pageId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addToFavorites(workspaceSlug: string, pageId: string): Promise<void> {
    return this.post(`${this.basePath(workspaceSlug)}/${pageId}/favorite/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeFromFavorites(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug)}/${pageId}/favorite/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async archive(workspaceSlug: string, pageId: string): Promise<{ archived_at: string }> {
    return this.post(`${this.basePath(workspaceSlug)}/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restore(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug)}/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async lock(workspaceSlug: string, pageId: string): Promise<void> {
    return this.post(`${this.basePath(workspaceSlug)}/${pageId}/lock/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async unlock(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug)}/${pageId}/lock/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchDescriptionBinary(workspaceSlug: string, pageId: string): Promise<ArrayBuffer> {
    return this.get(`${this.basePath(workspaceSlug)}/${pageId}/description/`, {
      headers: {
        "Content-Type": "application/octet-stream",
      },
      responseType: "arraybuffer",
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateDescription(workspaceSlug: string, pageId: string, data: TDocumentPayload): Promise<unknown> {
    return this.patch(`${this.basePath(workspaceSlug)}/${pageId}/description/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error;
      });
  }

  async duplicate(workspaceSlug: string, pageId: string): Promise<TPage> {
    return this.post(`${this.basePath(workspaceSlug)}/${pageId}/duplicate/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
