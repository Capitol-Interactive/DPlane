# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for hiding app rail sections per workspace (Workspace.disabled_app_sections)."""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import User, Workspace, WorkspaceMember


def _url(slug):
    return f"/api/workspaces/{slug}/"


def _member_client(workspace, role):
    unique = uuid.uuid4().hex[:8]
    user = User.objects.create(email=f"member-{unique}@plane.so", username=f"member_{unique}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.contract
class TestWorkspaceAppSections:
    @pytest.mark.django_db
    def test_defaults_to_no_disabled_sections(self, session_client, workspace):
        response = session_client.get("/api/users/me/workspaces/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["disabled_app_sections"] == []

    @pytest.mark.django_db
    def test_admin_can_disable_sections(self, session_client, workspace):
        response = session_client.patch(
            _url(workspace.slug), {"disabled_app_sections": ["clients", "agents", "clients"]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        # de-duplicated and stored in rail order
        assert response.data["disabled_app_sections"] == ["agents", "clients"]
        workspace.refresh_from_db()
        assert workspace.disabled_app_sections == ["agents", "clients"]

    @pytest.mark.django_db
    def test_admin_can_re_enable_all_sections(self, session_client, workspace):
        Workspace.objects.filter(pk=workspace.pk).update(disabled_app_sections=["people"])

        response = session_client.patch(_url(workspace.slug), {"disabled_app_sections": []}, format="json")

        assert response.status_code == status.HTTP_200_OK
        workspace.refresh_from_db()
        assert workspace.disabled_app_sections == []

    @pytest.mark.django_db
    @pytest.mark.parametrize("value", [["knowledge"], ["work"], ["unknown"], "agents", [1]])
    def test_rejects_sections_that_cannot_be_disabled(self, session_client, workspace, value):
        response = session_client.patch(_url(workspace.slug), {"disabled_app_sections": value}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        workspace.refresh_from_db()
        assert workspace.disabled_app_sections == []

    @pytest.mark.django_db
    def test_member_cannot_change_sections(self, workspace):
        client = _member_client(workspace, role=15)

        response = client.patch(_url(workspace.slug), {"disabled_app_sections": ["agents"]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        workspace.refresh_from_db()
        assert workspace.disabled_app_sections == []
