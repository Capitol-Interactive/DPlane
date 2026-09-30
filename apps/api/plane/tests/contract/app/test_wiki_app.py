# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the workspace-level wiki (Knowledge) endpoints."""

import json
import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.page_version_task import track_page_version
from plane.db.models import (
    Page,
    PageVersion,
    Project,
    ProjectPage,
    User,
    UserFavorite,
    WikiCollection,
    Workspace,
    WorkspaceMember,
)


def _pages_url(slug, page_id=None, suffix=""):
    base = f"/api/workspaces/{slug}/wiki/pages/"
    return f"{base}{page_id}/{suffix}" if page_id else base


def _collections_url(slug, pk=None):
    base = f"/api/workspaces/{slug}/wiki/collections/"
    return f"{base}{pk}/" if pk else base


def _make_user(prefix):
    unique = uuid.uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unique}@plane.so", username=f"{prefix}_{unique}")


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _add_member(workspace, prefix, role):
    user = _make_user(prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user, _client_for(user)


def _make_wiki_page(workspace, owner, access=Page.PUBLIC_ACCESS, **kwargs):
    return Page.objects.create(
        workspace=workspace, owned_by=owner, access=access, is_global=True, name=kwargs.pop("name", "Wiki"), **kwargs
    )


@pytest.fixture(autouse=True)
def _no_celery(mocker):
    """The views enqueue celery tasks; the tests only care about the HTTP contract."""
    for name in (
        "page_transaction",
        "track_page_version",
        "recent_visited_task",
        "copy_s3_objects_of_description_and_assets",
    ):
        mocker.patch(f"plane.app.views.wiki.base.{name}")
    # Soft deletes fan out to related objects through celery as well
    mocker.patch("plane.db.mixins.soft_delete_related_objects")


@pytest.mark.contract
class TestWikiPages:
    @pytest.mark.django_db
    def test_created_page_is_private_workspace_page(self, session_client, workspace, create_user):
        response = session_client.post(_pages_url(workspace.slug), {"name": "Notes"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["access"] == Page.PRIVATE_ACCESS
        assert body["owned_by"] == str(create_user.id)
        assert body["collection"] is None
        page = Page.objects.get(pk=body["id"])
        assert page.is_global is True
        assert not ProjectPage.objects.filter(page=page).exists()

    @pytest.mark.django_db
    def test_private_pages_are_hidden_from_other_members(self, session_client, workspace, create_user):
        _, other_client = _add_member(workspace, "member", 15)
        private = _make_wiki_page(workspace, create_user, Page.PRIVATE_ACCESS, name="Private")
        public = _make_wiki_page(workspace, create_user, Page.PUBLIC_ACCESS, name="Public")

        listed = {item["id"] for item in other_client.get(_pages_url(workspace.slug)).json()}

        assert str(public.id) in listed
        assert str(private.id) not in listed
        assert other_client.get(_pages_url(workspace.slug, private.id)).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_guest_only_sees_own_pages_and_cannot_write(self, workspace, create_user):
        guest, guest_client = _add_member(workspace, "guest", 5)
        public = _make_wiki_page(workspace, create_user, Page.PUBLIC_ACCESS)
        own = _make_wiki_page(workspace, guest, Page.PUBLIC_ACCESS, name="Guest page")

        listed = {item["id"] for item in guest_client.get(_pages_url(workspace.slug)).json()}

        assert listed == {str(own.id)}
        assert guest_client.get(_pages_url(workspace.slug, public.id)).status_code == status.HTTP_404_NOT_FOUND
        response = guest_client.post(_pages_url(workspace.slug), {"name": "Nope"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_other_workspace_members_have_no_access(self, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        outsider = _make_user("outsider")
        other_workspace = Workspace.objects.create(name="Other", owner=outsider, slug="other-workspace")
        WorkspaceMember.objects.create(workspace=other_workspace, member=outsider, role=20)
        client = _client_for(outsider)

        assert client.get(_pages_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN
        # The page id must not resolve through the attacker's own workspace either
        assert client.get(_pages_url(other_workspace.slug, page.id)).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_project_pages_are_not_wiki_pages(self, session_client, workspace, create_user):
        project = Project.objects.create(name="Proj", identifier="PRJ", workspace=workspace)
        project_page = _make_wiki_page(workspace, create_user, name="In project")
        ProjectPage.objects.create(workspace=workspace, project=project, page=project_page)
        plain_project_page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Plain")
        ProjectPage.objects.create(workspace=workspace, project=project, page=plain_project_page)

        assert session_client.get(_pages_url(workspace.slug)).json() == []
        assert (
            session_client.get(_pages_url(workspace.slug, plain_project_page.id)).status_code
            == status.HTTP_404_NOT_FOUND
        )

    @pytest.mark.django_db
    def test_nesting_and_cycle_protection(self, session_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Eng")
        root = session_client.post(
            _pages_url(workspace.slug), {"name": "Root", "collection": str(collection.id)}, format="json"
        ).json()
        assert root["access"] == Page.PUBLIC_ACCESS

        child = session_client.post(
            _pages_url(workspace.slug),
            {"name": "Child", "parent": root["id"], "collection": str(collection.id)},
            format="json",
        ).json()
        # nested pages inherit the collection from their root page
        assert child["parent"] == root["id"]
        assert child["collection"] is None

        response = session_client.patch(_pages_url(workspace.slug, root["id"]), {"parent": child["id"]}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response = session_client.patch(_pages_url(workspace.slug, root["id"]), {"parent": root["id"]}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_moving_page_into_collection_makes_it_a_root_page(self, session_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Eng")
        parent = _make_wiki_page(workspace, create_user)
        child = _make_wiki_page(workspace, create_user, parent=parent)

        response = session_client.patch(
            _pages_url(workspace.slug, child.id), {"collection": str(collection.id)}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["parent"] is None
        assert response.json()["collection"] == str(collection.id)

    @pytest.mark.django_db
    def test_collection_from_another_workspace_is_rejected(self, session_client, workspace, create_user):
        other_owner = _make_user("owner")
        other_workspace = Workspace.objects.create(name="Other", owner=other_owner, slug="other-ws")
        foreign = WikiCollection.objects.create(workspace=other_workspace, owned_by=other_owner, name="Foreign")

        response = session_client.post(
            _pages_url(workspace.slug), {"name": "X", "collection": str(foreign.id)}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_only_owner_can_change_access(self, workspace, create_user):
        member, member_client = _add_member(workspace, "member", 15)
        page = _make_wiki_page(workspace, create_user, Page.PUBLIC_ACCESS)

        response = member_client.post(_pages_url(workspace.slug, page.id, "access/"), {"access": 1}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        page.refresh_from_db()
        assert page.access == Page.PUBLIC_ACCESS

    @pytest.mark.django_db
    def test_lock_blocks_updates(self, session_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)

        assert session_client.post(_pages_url(workspace.slug, page.id, "lock/")).status_code == 204
        assert (
            session_client.patch(_pages_url(workspace.slug, page.id), {"name": "x"}, format="json").status_code == 400
        )
        assert (
            session_client.patch(
                _pages_url(workspace.slug, page.id, "description/"),
                {"description_html": "<p>x</p>"},
                format="json",
            ).status_code
            == 400
        )
        assert session_client.delete(_pages_url(workspace.slug, page.id, "lock/")).status_code == 204
        assert (
            session_client.patch(_pages_url(workspace.slug, page.id), {"name": "x"}, format="json").status_code == 200
        )

    @pytest.mark.django_db
    def test_archive_then_delete(self, workspace, create_user):
        member, member_client = _add_member(workspace, "member", 15)
        admin_client = _client_for(create_user)
        page = _make_wiki_page(workspace, member, name="Mine")
        child = _make_wiki_page(workspace, member, parent=page, name="Child")

        # must be archived before it can be deleted
        assert member_client.delete(_pages_url(workspace.slug, page.id)).status_code == status.HTTP_400_BAD_REQUEST
        assert member_client.post(_pages_url(workspace.slug, page.id, "archive/")).status_code == 200
        child.refresh_from_db()
        assert child.archived_at is not None
        archived = {p["id"] for p in member_client.get(_pages_url(workspace.slug) + "?archived=true").json()}
        assert archived == {str(page.id), str(child.id)}

        assert member_client.delete(_pages_url(workspace.slug, page.id, "archive/")).status_code == 204
        page.refresh_from_db()
        assert page.archived_at is None

        assert admin_client.post(_pages_url(workspace.slug, page.id, "archive/")).status_code == 200
        assert admin_client.delete(_pages_url(workspace.slug, page.id)).status_code == 204
        assert not Page.objects.filter(pk=page.id).exists()
        child.refresh_from_db()
        assert child.parent_id is None

    @pytest.mark.django_db
    def test_non_owner_member_cannot_archive(self, workspace, create_user):
        _, member_client = _add_member(workspace, "member", 15)
        page = _make_wiki_page(workspace, create_user)

        response = member_client.post(_pages_url(workspace.slug, page.id, "archive/"))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_favorites(self, session_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        url = _pages_url(workspace.slug, page.id, "favorite/")

        assert session_client.post(url).status_code == 204
        assert session_client.post(url).status_code == 204  # idempotent
        assert UserFavorite.objects.filter(entity_identifier=page.id, user=create_user).count() == 1
        listed = session_client.get(_pages_url(workspace.slug)).json()
        assert listed[0]["is_favorite"] is True

        assert session_client.delete(url).status_code == 204
        assert session_client.get(_pages_url(workspace.slug)).json()[0]["is_favorite"] is False

    @pytest.mark.django_db
    def test_duplicate_creates_owned_copy(self, workspace, create_user):
        member, member_client = _add_member(workspace, "member", 15)
        page = _make_wiki_page(workspace, create_user, Page.PUBLIC_ACCESS, name="Spec", is_locked=True)

        response = member_client.post(_pages_url(workspace.slug, page.id, "duplicate/"))

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == "Spec (Copy)"
        assert body["owned_by"] == str(member.id)
        assert body["is_locked"] is False
        assert Page.objects.get(pk=body["id"]).is_global is True

    @pytest.mark.django_db
    def test_description_round_trip_and_versions(self, session_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        url = _pages_url(workspace.slug, page.id, "description/")

        response = session_client.patch(url, {"description_html": "<p>hello</p>"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        page.refresh_from_db()
        assert page.description_html == "<p>hello</p>"
        assert session_client.get(url).status_code == status.HTTP_200_OK

        # private pages' versions are not reachable by other members
        version = PageVersion.objects.create(
            workspace=workspace, page=page, owned_by=create_user, description_html="<p>v</p>"
        )
        _, other_client = _add_member(workspace, "member", 15)
        page.access = Page.PRIVATE_ACCESS
        page.save()
        assert other_client.get(_pages_url(workspace.slug, page.id, "versions/")).status_code == 404
        listed = session_client.get(_pages_url(workspace.slug, page.id, "versions/")).json()
        assert [v["id"] for v in listed] == [str(version.id)]
        detail = session_client.get(_pages_url(workspace.slug, page.id, f"versions/{version.id}/"))
        assert detail.json()["description_html"] == "<p>v</p>"


@pytest.mark.contract
class TestWikiCollections:
    @pytest.mark.django_db
    def test_crud_and_page_count(self, session_client, workspace, create_user):
        created = session_client.post(
            _collections_url(workspace.slug), {"name": "Product", "logo_props": {"in_use": "emoji"}}, format="json"
        )
        assert created.status_code == status.HTTP_201_CREATED
        collection_id = created.json()["id"]
        second = session_client.post(_collections_url(workspace.slug), {"name": "Eng"}, format="json").json()
        assert second["sort_order"] > created.json()["sort_order"]

        _make_wiki_page(workspace, create_user, collection_id=collection_id)
        _make_wiki_page(workspace, create_user, Page.PRIVATE_ACCESS, collection_id=collection_id)
        listed = {c["id"]: c for c in session_client.get(_collections_url(workspace.slug)).json()}
        assert listed[collection_id]["page_count"] == 2

        renamed = session_client.patch(_collections_url(workspace.slug, collection_id), {"name": "Prod"}, format="json")
        assert renamed.status_code == 200 and renamed.json()["name"] == "Prod"

    @pytest.mark.django_db
    def test_only_owner_or_admin_can_edit(self, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Eng")
        _, member_client = _add_member(workspace, "member", 15)

        assert (
            member_client.patch(
                _collections_url(workspace.slug, collection.id), {"name": "x"}, format="json"
            ).status_code
            == 403
        )
        assert member_client.delete(_collections_url(workspace.slug, collection.id)).status_code == 403
        assert member_client.post(_collections_url(workspace.slug), {"name": "Mine"}, format="json").status_code == 201

    @pytest.mark.django_db
    def test_delete_with_transfer(self, session_client, workspace, create_user):
        source = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Src")
        target = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Dst")
        page = _make_wiki_page(workspace, create_user, collection=source)

        missing_target = session_client.delete(_collections_url(workspace.slug, source.id) + "?mode=transfer")
        assert missing_target.status_code == status.HTTP_400_BAD_REQUEST

        response = session_client.delete(
            _collections_url(workspace.slug, source.id) + f"?mode=transfer&target_collection={target.id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        page.refresh_from_db()
        assert page.collection_id == target.id
        assert not WikiCollection.objects.filter(pk=source.id).exists()

    @pytest.mark.django_db
    def test_delete_with_pages_removes_descendants(self, session_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Src")
        root = _make_wiki_page(workspace, create_user, collection=collection)
        child = _make_wiki_page(workspace, create_user, parent=root)
        keep = _make_wiki_page(workspace, create_user, name="Keep")
        UserFavorite.objects.create(
            workspace=workspace, user=create_user, entity_type="page", entity_identifier=child.id
        )

        response = session_client.delete(_collections_url(workspace.slug, collection.id) + "?mode=delete_pages")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Page.objects.filter(pk__in=[root.id, child.id]).exists()
        assert Page.objects.filter(pk=keep.id).exists()
        assert not UserFavorite.objects.filter(entity_identifier=child.id).exists()

    @pytest.mark.django_db
    def test_transfer_target_must_be_in_same_workspace(self, session_client, workspace, create_user):
        source = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Src")
        other_owner = _make_user("owner")
        other_workspace = Workspace.objects.create(name="Other", owner=other_owner, slug="other-ws2")
        foreign = WikiCollection.objects.create(workspace=other_workspace, owned_by=other_owner, name="Foreign")

        response = session_client.delete(
            _collections_url(workspace.slug, source.id) + f"?mode=transfer&target_collection={foreign.id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert WikiCollection.objects.filter(pk=source.id).exists()


@pytest.mark.contract
class TestPageVersionTask:
    @pytest.mark.django_db
    def test_saving_a_description_creates_a_version(self, workspace, create_user):
        """Regression: the task used to read the nonexistent `page.description` and swallow the error."""
        page = _make_wiki_page(workspace, create_user, description_html="<p>new</p>", description_json={"type": "doc"})

        track_page_version(
            page_id=page.id,
            existing_instance=json.dumps({"description_html": "<p>old</p>"}),
            user_id=create_user.id,
        )

        version = PageVersion.objects.get(page=page)
        assert version.description_html == "<p>new</p>"
        assert version.description_json == {"type": "doc"}
