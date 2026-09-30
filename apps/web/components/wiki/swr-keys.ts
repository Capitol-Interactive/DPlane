/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// SWR keys for the wiki data. The sidebar, the Wiki home page and the prefetch all read the same
// keys, so a prefetched request is reused instead of fetched again.
export const WIKI_PAGES_KEY = (workspaceSlug: string) => `WIKI_PAGES_${workspaceSlug}`;
export const WIKI_COLLECTIONS_KEY = (workspaceSlug: string) => `WIKI_COLLECTIONS_${workspaceSlug}`;
