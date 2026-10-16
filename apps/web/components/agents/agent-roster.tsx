/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Avatar } from "@makeplane/propel/components/avatar";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";

const WORKSPACE_ROLE_LABEL: Record<number, string> = { 20: "Admin", 15: "Member", 5: "Guest" };

// Lists the workspace's bot users (is_bot) as the agent team.
export const AgentRoster = observer(function AgentRoster() {
  const { workspaceSlug } = useParams();
  const {
    getUserDetails,
    workspace: { getWorkspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();

  const agents = getWorkspaceMemberIds(workspaceSlug?.toString() ?? "")
    .map((memberId) => ({ details: getUserDetails(memberId), membership: getWorkspaceMemberDetails(memberId) }))
    .filter(({ details }) => details?.is_bot);

  if (agents.length === 0) {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 px-6 text-center">
        <h1 className="text-18 font-semibold text-primary">No agents yet</h1>
        <p className="max-w-md text-13 text-tertiary">
          Agents are bot users in this workspace. Once one is added, it shows up here and can be assigned work and
          mentioned in comments.
        </p>
      </div>
    );
  }

  return (
    <div className="flex size-full flex-col gap-4 overflow-y-auto p-6">
      <div>
        <h1 className="text-18 font-semibold text-primary">Agents</h1>
        <p className="text-13 text-tertiary">{agents.length} agents in this workspace.</p>
      </div>
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {agents.map(({ details, membership }) => (
          <li key={details!.id} className="flex items-center gap-3 rounded-lg border border-subtle p-3">
            <Avatar src={getFileURL(details!.avatar_url ?? "")} alt={details!.display_name} size="lg" />
            <div className="min-w-0">
              <p className="truncate text-14 font-medium text-primary">{details!.display_name}</p>
              <p className="text-12 text-tertiary">
                {membership ? (WORKSPACE_ROLE_LABEL[membership.role] ?? "Member") : "Member"}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
});
