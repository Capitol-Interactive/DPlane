/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { Avatar } from "@makeplane/propel/components/avatar";
import type { TAgentComment } from "@plane/types";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { agentsService } from "@/services/agents.service";

// Lists the workspace's agents (bot users) with their role, manager and recent activity.
export const AgentRoster = observer(function AgentRoster() {
  const { workspaceSlug } = useParams();
  const { getUserDetails } = useMember();

  const slug = workspaceSlug?.toString();
  const {
    data: agents,
    error,
    isLoading,
  } = useSWR(slug ? `AGENT_ROSTER_${slug}` : null, () => agentsService.fetchRoster(slug!));

  if (isLoading) {
    return <div className="p-6 text-13 text-tertiary">Loading agents...</div>;
  }

  if (error) {
    return <div className="p-6 text-13 text-tertiary">Could not load the agents. Refresh to try again.</div>;
  }

  if (!agents || agents.length === 0) {
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

  // an agent reports to another agent or to a person
  const managerName = (managerId: string | null) => {
    if (!managerId) return null;
    return (
      agents.find((agent) => agent.id === managerId)?.display_name ?? getUserDetails(managerId)?.display_name ?? null
    );
  };

  return (
    <div className="flex size-full flex-col gap-4 overflow-y-auto p-6">
      <div>
        <h1 className="text-18 font-semibold text-primary">Agent team</h1>
        <p className="text-13 text-tertiary">{agents.length} agents in this workspace.</p>
      </div>
      <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-3">
        {agents.map((agent) => {
          const manager = managerName(agent.reports_to);
          return (
            <li key={agent.id} className="flex flex-col gap-3 rounded-lg border border-subtle p-4">
              <div className="flex items-center gap-3">
                <Avatar src={getFileURL(agent.avatar_url ?? "")} alt={agent.display_name} size="lg" />
                <div className="min-w-0">
                  <p className="truncate text-14 font-medium text-primary">{agent.display_name}</p>
                  <p className="truncate text-12 text-tertiary">
                    {agent.role ?? "Agent"}
                    {manager ? ` · reports to ${manager}` : ""}
                  </p>
                </div>
              </div>
              <p className="text-12 text-secondary">
                {agent.open_work_items} open work item{agent.open_work_items === 1 ? "" : "s"}
              </p>
              {agent.recent_comments.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {agent.recent_comments.map((comment: TAgentComment) => (
                    <li key={comment.id} className="text-12">
                      <Link
                        href={`/${slug}/projects/${comment.project_id}/issues/${comment.work_item_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {comment.project_identifier}-{comment.sequence_id} {comment.work_item_name}
                      </Link>
                      <p className="line-clamp-2 text-tertiary">{comment.snippet}</p>
                      <p className="text-placeholder">{new Date(comment.created_at).toLocaleDateString()}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-12 text-placeholder">No comments yet.</p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
});
