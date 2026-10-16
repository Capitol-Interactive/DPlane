# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bot users (agents) have no notification preferences. A bot subscriber or a mentioned bot must not stop
the notification task from notifying everyone else on the work item."""

import json
import uuid

import pytest

from plane.bgtasks.notification_task import notifications
from plane.db.models import (
    EmailNotificationLog,
    Issue,
    IssueSubscriber,
    Notification,
    Project,
    ProjectMember,
    State,
    User,
    UserNotificationPreference,
    WorkspaceMember,
)


def _make_user(prefix, **kwargs):
    unique = uuid.uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unique}@plane.so", username=f"{prefix}_{unique}", **kwargs)


def _add_member(workspace, project, user):
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=15)


@pytest.fixture
def work_item(workspace, create_user):
    project = Project.objects.create(name="Agents", identifier="AGN", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20)
    state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
    issue = Issue.objects.create(
        name="Invoice run", project=project, workspace=workspace, state=state, created_by=create_user
    )
    return project, issue


def _activity(issue, actor, field="priority"):
    return json.dumps(
        [
            {
                "id": str(uuid.uuid4()),
                "issue_detail": {"id": str(issue.id)},
                "field": field,
                "verb": "updated",
                "old_value": "none",
                "new_value": "high",
                "actor": str(actor.id),
                "comment": f"updated the {field} to",
            }
        ]
    )


@pytest.mark.unit
class TestNotificationsWithBots:
    @pytest.mark.django_db
    def test_bot_subscriber_does_not_block_human_notifications(self, workspace, create_user, work_item):
        project, issue = work_item
        actor = _make_user("actor")
        agent = _make_user("agent", is_bot=True)
        for user in (actor, agent):
            _add_member(workspace, project, user)
        assert not UserNotificationPreference.objects.filter(user=agent).exists()
        for user in (create_user, agent):
            IssueSubscriber.objects.create(issue=issue, project=project, workspace=workspace, subscriber=user)

        notifications(
            type="issue.activity.updated",
            issue_id=str(issue.id),
            project_id=str(project.id),
            actor_id=str(actor.id),
            subscriber=False,
            issue_activities_created=_activity(issue, actor),
            requested_data=json.dumps({"priority": "high"}),
            current_instance=json.dumps({"priority": "none"}),
        )

        assert Notification.objects.filter(receiver=create_user, entity_identifier=issue.id).exists()
        assert not Notification.objects.filter(receiver=agent).exists()

    @pytest.mark.django_db
    def test_mentioned_bot_does_not_block_human_mentions(self, workspace, create_user, work_item):
        project, issue = work_item
        actor = _make_user("actor")
        agent = _make_user("agent", is_bot=True)
        human = _make_user("human")
        for user in (actor, agent, human):
            _add_member(workspace, project, user)

        def mention(user):
            return f'<mention-component entity_name="user_mention" entity_identifier="{user.id}"></mention-component>'

        notifications(
            type="issue.activity.updated",
            issue_id=str(issue.id),
            project_id=str(project.id),
            actor_id=str(actor.id),
            subscriber=False,
            issue_activities_created=_activity(issue, actor, field="description"),
            requested_data=json.dumps({"description_html": f"<p>{mention(agent)} {mention(human)}</p>"}),
            current_instance=json.dumps({"description_html": "<p></p>"}),
        )

        assert Notification.objects.filter(receiver=human, sender__contains="mention").exists()
        assert not Notification.objects.filter(receiver=agent).exists()
        # the mention email goes to the person who was mentioned
        assert EmailNotificationLog.objects.filter(receiver=human).exists()
