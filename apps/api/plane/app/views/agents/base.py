# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db.models import Count

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import IssueAssignee, IssueComment, WorkspaceMember

OPEN_STATE_GROUPS = ["backlog", "unstarted", "started"]
RECENT_COMMENT_LIMIT = 3
COMMENT_SNIPPET_LENGTH = 160


class AgentRosterEndpoint(BaseAPIView):
    """The workspace's agents (bot users) with their role, manager and recent activity."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        members = list(
            WorkspaceMember.objects.filter(workspace__slug=slug, is_active=True, member__is_bot=True)
            .select_related("member", "member__avatar_asset")
            .order_by("member__display_name")
        )
        agent_ids = [m.member_id for m in members]

        open_counts = dict(
            IssueAssignee.objects.filter(
                workspace__slug=slug,
                assignee_id__in=agent_ids,
                issue__state__group__in=OPEN_STATE_GROUPS,
                issue__archived_at__isnull=True,
                issue__is_draft=False,
            )
            .values_list("assignee_id")
            .annotate(total=Count("id"))
        )

        agents = []
        for membership in members:
            agent = membership.member
            comments = (
                IssueComment.objects.filter(workspace__slug=slug, actor=agent, access="INTERNAL")
                .select_related("issue", "issue__project")
                .order_by("-created_at")[:RECENT_COMMENT_LIMIT]
            )
            agents.append(
                {
                    "id": agent.id,
                    "display_name": agent.display_name,
                    "avatar_url": agent.avatar_url,
                    "role": agent.bot_type,
                    "workspace_role": membership.role,
                    "reports_to": agent.bot_reports_to_id,
                    "open_work_items": open_counts.get(agent.id, 0),
                    "recent_comments": [
                        {
                            "id": comment.id,
                            "created_at": comment.created_at,
                            "snippet": comment.comment_stripped[:COMMENT_SNIPPET_LENGTH],
                            "work_item_id": comment.issue_id,
                            "work_item_name": comment.issue.name,
                            "project_id": comment.project_id,
                            "project_identifier": comment.issue.project.identifier,
                            "sequence_id": comment.issue.sequence_id,
                        }
                        for comment in comments
                    ],
                }
            )
        return Response(agents, status=status.HTTP_200_OK)
