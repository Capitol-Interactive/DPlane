/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TAgent } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class AgentsService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchRoster(workspaceSlug: string): Promise<TAgent[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/agents/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const agentsService = new AgentsService();
