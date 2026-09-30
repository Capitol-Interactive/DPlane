/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane types
import { API_BASE_URL } from "@plane/constants";
import type { TWikiCollection, TWikiCollectionDeleteMode, TWikiCollectionPayload } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class WikiCollectionService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchAll(workspaceSlug: string): Promise<TWikiCollection[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/collections/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: TWikiCollectionPayload): Promise<TWikiCollection> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/collections/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, collectionId: string, data: TWikiCollectionPayload): Promise<TWikiCollection> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/collections/${collectionId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, collectionId: string, options: TWikiCollectionDeleteMode): Promise<void> {
    const params =
      options.mode === "transfer"
        ? { mode: options.mode, target_collection: options.targetCollectionId }
        : { mode: options.mode };
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/collections/${collectionId}/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
