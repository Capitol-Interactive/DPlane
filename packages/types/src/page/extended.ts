/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Fields only meaningful for nested / grouped (wiki) pages. Project pages leave them unset.
export type TPageExtended = {
  parent?: string | null;
  collection?: string | null;
  sort_order?: number;
};
