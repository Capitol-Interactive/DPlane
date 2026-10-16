# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the agent roster and for bot users showing up in member lists."""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, IssueAssignee, IssueComment, Project, ProjectMember, State, User, WorkspaceMember


def _roster_url(slug):
    return f"/api/workspaces/{slug}/agents/"


def _make_user(prefix, **kwargs):
    unique = uuid.uuid4().hex[:8]
    return User.objects.create(
        email=f"{prefix}-{unique}@plane.so", username=f"{prefix}_{unique}", display_name=f"{prefix}-{unique}", **kwargs
    )


def _add_workspace_member(workspace, user, role=15):
    return WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)


@pytest.mark.contract
class TestAgentRoster:
    @pytest.mark.django_db
    def test_lists_only_bot_members_with_role_and_manager(self, session_client, workspace, create_user):
        manager = _make_user("margot", is_bot=True, bot_type="CMO")
        agent = _make_user("leonie", is_bot=True, bot_type="LinkedIn specialist", bot_reports_to=manager)
        human = _make_user("human")
        for user in (manager, agent, human):
            _add_workspace_member(workspace, user)

        response = session_client.get(_roster_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        by_id = {str(row["id"]): row for row in response.data}
        assert set(by_id) == {str(manager.id), str(agent.id)}
        assert by_id[str(agent.id)]["role"] == "LinkedIn specialist"
        assert str(by_id[str(agent.id)]["reports_to"]) == str(manager.id)
        assert by_id[str(manager.id)]["reports_to"] is None
        assert by_id[str(agent.id)]["open_work_items"] == 0
        assert by_id[str(agent.id)]["recent_comments"] == []

    @pytest.mark.django_db
    def test_reports_open_work_and_recent_comments(self, session_client, workspace, create_user):
        agent = _make_user("fiona", is_bot=True, bot_type="Finance and billing")
        _add_workspace_member(workspace, agent)
        project = Project.objects.create(name="Billing", identifier="BIL", workspace=workspace, created_by=create_user)
        open_state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
        done_state = State.objects.create(name="Done", group="completed", project=project, workspace=workspace)
        open_issue = Issue.objects.create(name="Invoice run", project=project, workspace=workspace, state=open_state)
        done_issue = Issue.objects.create(name="Old invoice", project=project, workspace=workspace, state=done_state)
        for issue in (open_issue, done_issue):
            IssueAssignee.objects.create(issue=issue, assignee=agent, project=project, workspace=workspace)
        IssueComment.objects.create(
            issue=open_issue,
            actor=agent,
            project=project,
            workspace=workspace,
            comment_stripped="Sent 3 reminders",
            comment_html="<p>Sent 3 reminders</p>",
        )

        response = session_client.get(_roster_url(workspace.slug))

        row = next(r for r in response.data if str(r["id"]) == str(agent.id))
        assert row["open_work_items"] == 1
        assert len(row["recent_comments"]) == 1
        comment = row["recent_comments"][0]
        assert comment["snippet"] == "Sent 3 reminders"
        assert comment["work_item_name"] == "Invoice run"
        assert comment["project_identifier"] == "BIL"

    @pytest.mark.django_db
    def test_excludes_bots_from_other_workspaces(self, session_client, workspace):
        agent = _make_user("elsewhere", is_bot=True)
        # not a member of `workspace`

        response = session_client.get(_roster_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert str(agent.id) not in {str(row["id"]) for row in response.data}

    @pytest.mark.django_db
    def test_requires_workspace_membership(self, workspace):
        outsider = _make_user("outsider")
        client = APIClient()
        client.force_authenticate(user=outsider)

        response = client.get(_roster_url(workspace.slug))

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.contract
class TestBotMembersVisible:
    @pytest.mark.django_db
    def test_project_member_list_includes_bot(self, session_client, workspace, create_user):
        agent = _make_user("lex", is_bot=True, bot_type="Legal drafter")
        _add_workspace_member(workspace, agent)
        project = Project.objects.create(name="Agents", identifier="AGT", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=project, workspace=workspace, member=create_user, role=20)
        ProjectMember.objects.create(project=project, workspace=workspace, member=agent, role=15)

        response = session_client.get(f"/api/workspaces/{workspace.slug}/projects/{project.id}/members/")

        assert response.status_code == status.HTTP_200_OK
        assert str(agent.id) in {str(row["member"]) for row in response.data}


@pytest.mark.contract
class TestCreateAgentCommand:
    @pytest.mark.django_db
    def test_creates_bot_member_with_role_manager_and_token(self, workspace, create_user):
        from io import StringIO

        from django.core.management import call_command

        from plane.db.models import APIToken

        out = StringIO()
        call_command(
            "create_agent",
            workspace=workspace.slug,
            email="fiona@agents.example.com",
            name="Finance Fiona",
            role="Finance and billing",
            reports_to=create_user.email,
            stdout=out,
        )

        agent = User.objects.get(email="fiona@agents.example.com")
        assert agent.is_bot and not agent.has_usable_password()
        assert agent.display_name == "Finance Fiona"
        assert agent.bot_type == "Finance and billing"
        assert agent.bot_reports_to_id == create_user.id
        assert WorkspaceMember.objects.filter(workspace=workspace, member=agent, is_active=True).exists()
        token = APIToken.objects.get(user=agent)
        assert token.user_type == 1 and token.workspace_id == workspace.id
        assert token.token in out.getvalue()

        # running it again updates the agent and does not mint a second token
        call_command(
            "create_agent",
            workspace=workspace.slug,
            email="fiona@agents.example.com",
            name="Finance Fiona",
            role="Billing",
            stdout=StringIO(),
        )
        agent.refresh_from_db()
        assert agent.bot_type == "Billing" and agent.bot_reports_to_id is None
        assert APIToken.objects.filter(user=agent).count() == 1

    @pytest.mark.django_db
    def test_refuses_to_convert_a_regular_user(self, workspace, create_user):
        from django.core.management import CommandError, call_command

        with pytest.raises(CommandError):
            call_command("create_agent", workspace=workspace.slug, email=create_user.email, name="Nope")
