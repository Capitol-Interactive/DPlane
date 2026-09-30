/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "../common";

// A workspace-level grouping of wiki pages (Knowledge section)
export type TWikiCollection = {
  id: string;
  name: string;
  logo_props: TLogoProps | undefined;
  sort_order: number;
  owned_by: string;
  workspace: string;
  page_count?: number;
  created_at: string;
  updated_at: string;
};

export type TWikiCollectionPayload = Partial<Pick<TWikiCollection, "name" | "logo_props" | "sort_order">>;

// What to do with the pages of a collection when it is deleted
export type TWikiCollectionDeleteMode = { mode: "delete_pages" } | { mode: "transfer"; targetCollectionId: string };
