/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TAgentComment = {
  id: string;
  created_at: string;
  snippet: string;
  work_item_id: string;
  work_item_name: string;
  project_id: string;
  project_identifier: string;
  sequence_id: number;
};

// One agent (a bot user) on the workspace's Agents page
export type TAgent = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  // job title, stored in the user's bot_type
  role: string | null;
  workspace_role: number;
  // user id of the person or agent this agent reports to
  reports_to: string | null;
  open_work_items: number;
  recent_comments: TAgentComment[];
};
