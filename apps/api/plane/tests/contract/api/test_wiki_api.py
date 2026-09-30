# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the token-authenticated (X-Api-Key) wiki endpoints."""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Page,
    PageVersion,
    Project,
    ProjectPage,
    User,
    WikiCollection,
    Workspace,
    WorkspaceMember,
)
from plane.utils.error_codes import ERROR_CODES

ROLE_ADMIN, ROLE_MEMBER, ROLE_GUEST = 20, 15, 5


def _pages_url(slug, page_id=None, suffix=""):
    base = f"/api/v1/workspaces/{slug}/wiki/pages/"
    return f"{base}{page_id}/{suffix}" if page_id else base


def _collections_url(slug, pk=None):
    base = f"/api/v1/workspaces/{slug}/wiki/collections/"
    return f"{base}{pk}/" if pk else base


def _make_user(prefix):
    unique = uuid.uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unique}@plane.so", username=f"{prefix}_{unique}")


def _token_client(user):
    token = APIToken.objects.create(user=user, label="wiki", token=f"plane_api_{uuid.uuid4().hex}")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    return client


def _add_member(workspace, prefix, role):
    user = _make_user(prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user, _token_client(user)


def _make_wiki_page(workspace, owner, access=Page.PUBLIC_ACCESS, **kwargs):
    return Page.objects.create(
        workspace=workspace, owned_by=owner, access=access, is_global=True, name=kwargs.pop("name", "Wiki"), **kwargs
    )


@pytest.fixture(autouse=True)
def _no_celery(mocker):
    """The views enqueue celery tasks; the tests only care about the HTTP contract."""
    tasks = {}
    for name in (
        "page_transaction",
        "track_page_version",
        "copy_s3_objects_of_description_and_assets",
    ):
        tasks[name] = mocker.patch(f"plane.api.views.wiki.{name}")
    # Soft deletes fan out to related objects through celery as well
    mocker.patch("plane.db.mixins.soft_delete_related_objects")
    return tasks


@pytest.mark.contract
class TestWikiAuthentication:
    @pytest.mark.django_db
    def test_requires_api_key(self, workspace):
        response = APIClient().get(_pages_url(workspace.slug))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_rejects_unknown_api_key(self, workspace):
        client = APIClient()
        client.credentials(HTTP_X_API_KEY="plane_api_not-a-real-token")
        # A key that fails authentication is refused the same way as every other v1 endpoint
        assert client.get(_pages_url(workspace.slug)).status_code in (401, 403)
        assert client.get(_collections_url(workspace.slug)).status_code in (401, 403)

    @pytest.mark.django_db
    def test_session_login_is_not_accepted(self, workspace, create_user):
        client = APIClient()
        client.force_login(create_user)
        assert client.get(_pages_url(workspace.slug)).status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_non_member_is_forbidden(self, workspace):
        _, outsider = (_make_user("outsider"), None)
        outsider = _token_client(_)
        assert outsider.get(_pages_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN
        assert outsider.post(_pages_url(workspace.slug), {"name": "x"}, format="json").status_code == 403
        assert outsider.get(_collections_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_workspaces_are_isolated(self, api_key_client, workspace, create_user):
        other_owner = _make_user("other-owner")
        other = Workspace.objects.create(name="Other", owner=other_owner, slug="other-workspace")
        WorkspaceMember.objects.create(workspace=other, member=other_owner, role=ROLE_ADMIN)
        foreign_page = _make_wiki_page(other, other_owner)
        foreign_collection = WikiCollection.objects.create(workspace=other, owned_by=other_owner, name="Foreign")

        # The token's user is not a member of the other workspace
        assert api_key_client.get(_pages_url(other.slug)).status_code == status.HTTP_403_FORBIDDEN
        # ...and cannot reach that workspace's records by addressing them through their own workspace
        assert api_key_client.get(_pages_url(workspace.slug, foreign_page.id)).status_code == 404
        assert api_key_client.get(_collections_url(workspace.slug, foreign_collection.id)).status_code == 404
        assert api_key_client.get(_pages_url(workspace.slug)).json()["results"] == []

    @pytest.mark.django_db
    def test_non_object_body_is_rejected(self, api_key_client, workspace):
        response = api_key_client.post(_pages_url(workspace.slug), [{"name": "x"}], format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestWikiCollections:
    @pytest.mark.django_db
    def test_create_list_and_page_count(self, api_key_client, workspace, create_user):
        first = api_key_client.post(_collections_url(workspace.slug), {"name": "Docs"}, format="json")
        second = api_key_client.post(_collections_url(workspace.slug), {"name": "Notes"}, format="json")
        assert first.status_code == second.status_code == status.HTTP_201_CREATED
        assert first.json()["owned_by"] == str(create_user.id)
        assert second.json()["sort_order"] > first.json()["sort_order"]

        _make_wiki_page(workspace, create_user, collection_id=first.json()["id"])
        _make_wiki_page(workspace, create_user, collection_id=first.json()["id"], archived_at="2024-01-01")

        listing = api_key_client.get(_collections_url(workspace.slug)).json()
        assert [c["name"] for c in listing] == ["Docs", "Notes"]
        assert listing[0]["page_count"] == 1

    @pytest.mark.django_db
    def test_name_is_required(self, api_key_client, workspace):
        response = api_key_client.post(_collections_url(workspace.slug), {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_retrieve_and_rename(self, api_key_client, workspace):
        created = api_key_client.post(_collections_url(workspace.slug), {"name": "Docs"}, format="json").json()

        assert api_key_client.get(_collections_url(workspace.slug, created["id"])).json()["name"] == "Docs"
        renamed = api_key_client.patch(
            _collections_url(workspace.slug, created["id"]), {"name": "Guides"}, format="json"
        )
        assert renamed.status_code == status.HTTP_200_OK
        assert renamed.json()["name"] == "Guides"

    @pytest.mark.django_db
    def test_only_owner_or_admin_can_change(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Mine")
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        assert member_client.get(_collections_url(workspace.slug, collection.id)).status_code == 200
        assert (
            member_client.patch(
                _collections_url(workspace.slug, collection.id), {"name": "x"}, format="json"
            ).status_code
            == 403
        )
        assert (
            member_client.delete(_collections_url(workspace.slug, collection.id) + "?mode=delete_pages").status_code
            == 403
        )

        # A workspace admin may change collections owned by someone else
        member_owned = WikiCollection.objects.create(workspace=workspace, owned_by=_make_user("m"), name="Theirs")
        assert (
            api_key_client.patch(
                _collections_url(workspace.slug, member_owned.id), {"name": "y"}, format="json"
            ).status_code
            == 200
        )

    @pytest.mark.django_db
    def test_delete_without_mode_is_refused(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        page = _make_wiki_page(workspace, create_user, collection=collection)

        response = api_key_client.delete(_collections_url(workspace.slug, collection.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert WikiCollection.objects.filter(pk=collection.id).exists()
        assert Page.objects.filter(pk=page.id).exists()

    @pytest.mark.django_db
    def test_delete_with_unknown_mode_is_refused(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        response = api_key_client.delete(_collections_url(workspace.slug, collection.id) + "?mode=nuke")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_delete_transfer_moves_pages(self, api_key_client, workspace, create_user):
        source = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Old")
        target = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="New")
        page = _make_wiki_page(workspace, create_user, collection=source)

        response = api_key_client.delete(
            _collections_url(workspace.slug, source.id) + f"?mode=transfer&target_collection={target.id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not WikiCollection.objects.filter(pk=source.id).exists()
        page.refresh_from_db()
        assert page.collection_id == target.id

    @pytest.mark.django_db
    def test_delete_transfer_needs_a_valid_target(self, api_key_client, workspace, create_user):
        source = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Old")
        other_owner = _make_user("other-owner")
        other = Workspace.objects.create(name="Other", owner=other_owner, slug="other-ws")
        foreign = WikiCollection.objects.create(workspace=other, owned_by=other_owner, name="Foreign")
        url = _collections_url(workspace.slug, source.id)

        assert api_key_client.delete(url + "?mode=transfer").status_code == status.HTTP_400_BAD_REQUEST
        assert api_key_client.delete(url + f"?mode=transfer&target_collection={source.id}").status_code == 400
        assert api_key_client.delete(url + f"?mode=transfer&target_collection={foreign.id}").status_code == 404
        assert WikiCollection.objects.filter(pk=source.id).exists()

    @pytest.mark.django_db
    def test_delete_pages_removes_collection_and_sub_pages(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        root = _make_wiki_page(workspace, create_user, collection=collection)
        child = _make_wiki_page(workspace, create_user, parent=root)
        keep = _make_wiki_page(workspace, create_user)

        response = api_key_client.delete(_collections_url(workspace.slug, collection.id) + "?mode=delete_pages")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Page.objects.filter(pk__in=[root.id, child.id]).exists()
        assert Page.objects.filter(pk=keep.id).exists()


@pytest.mark.contract
class TestWikiPages:
    @pytest.mark.django_db
    def test_create_defaults_and_content(self, api_key_client, workspace, create_user, _no_celery):
        response = api_key_client.post(
            _pages_url(workspace.slug), {"name": "Notes", "description_html": "<h1>Hi</h1><p>there</p>"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["access"] == Page.PRIVATE_ACCESS
        assert body["owned_by"] == str(create_user.id)
        assert body["description_html"] == "<h1>Hi</h1><p>there</p>"
        page = Page.objects.get(pk=body["id"])
        assert page.is_global is True
        assert page.description_binary is None
        assert not ProjectPage.objects.filter(page=page).exists()
        _no_celery["page_transaction"].delay.assert_called_once()

    @pytest.mark.django_db
    def test_create_without_content_gets_an_empty_paragraph(self, api_key_client, workspace):
        body = api_key_client.post(_pages_url(workspace.slug), {"name": "Blank"}, format="json").json()
        assert body["description_html"] == "<p></p>"

    @pytest.mark.django_db
    def test_create_in_collection_is_public_and_root(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        parent = _make_wiki_page(workspace, create_user)

        body = api_key_client.post(
            _pages_url(workspace.slug), {"name": "A", "collection": str(collection.id)}, format="json"
        ).json()
        assert body["access"] == Page.PUBLIC_ACCESS
        assert body["collection"] == str(collection.id)

        # A collection is ignored once a parent is given; the sub page inherits the parent's access
        nested = api_key_client.post(
            _pages_url(workspace.slug),
            {"name": "B", "parent": str(parent.id), "collection": str(collection.id)},
            format="json",
        ).json()
        assert nested["parent"] == str(parent.id)
        assert nested["collection"] is None
        assert nested["access"] == parent.access

    @pytest.mark.django_db
    def test_create_rejects_foreign_collection_and_parent(self, api_key_client, workspace):
        other_owner = _make_user("other-owner")
        other = Workspace.objects.create(name="Other", owner=other_owner, slug="other-ws2")
        foreign_collection = WikiCollection.objects.create(workspace=other, owned_by=other_owner, name="Foreign")
        foreign_page = _make_wiki_page(other, other_owner)

        response = api_key_client.post(
            _pages_url(workspace.slug), {"name": "x", "collection": str(foreign_collection.id)}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = api_key_client.post(
            _pages_url(workspace.slug), {"name": "x", "parent": str(foreign_page.id)}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_script_content_is_rejected_or_stripped(self, api_key_client, workspace):
        response = api_key_client.post(
            _pages_url(workspace.slug),
            {"name": "x", "description_html": "<p>ok</p><script>alert(1)</script><img src=x onerror=alert(1)>"},
            format="json",
        )
        if response.status_code == status.HTTP_201_CREATED:
            html = response.json()["description_html"]
            assert "<script" not in html
            assert "onerror" not in html
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_description_must_be_a_string(self, api_key_client, workspace):
        response = api_key_client.post(
            _pages_url(workspace.slug), {"name": "x", "description_html": {"a": 1}}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_retrieve_returns_content(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user, description_html="<p>body</p>")
        body = api_key_client.get(_pages_url(workspace.slug, page.id)).json()
        assert body["description_html"] == "<p>body</p>"
        assert "description_binary" not in body

    @pytest.mark.django_db
    def test_private_pages_are_invisible_to_other_members(self, api_key_client, workspace, create_user):
        private = _make_wiki_page(workspace, create_user, access=Page.PRIVATE_ACCESS, name="Secret")
        public = _make_wiki_page(workspace, create_user, name="Open")
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        names = [p["name"] for p in member_client.get(_pages_url(workspace.slug)).json()["results"]]
        assert names == ["Open"]
        assert member_client.get(_pages_url(workspace.slug, private.id)).status_code == 404
        assert (
            member_client.patch(_pages_url(workspace.slug, private.id), {"name": "x"}, format="json").status_code == 404
        )
        assert member_client.post(_pages_url(workspace.slug, private.id, "duplicate/")).status_code == 404
        assert member_client.get(_pages_url(workspace.slug, private.id, "versions/")).status_code == 404
        assert member_client.get(_pages_url(workspace.slug, public.id)).status_code == 200

    @pytest.mark.django_db
    def test_project_pages_never_appear(self, api_key_client, workspace, create_user):
        project = Project.objects.create(name="P", identifier="P", workspace=workspace)
        project_page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Proj", is_global=True)
        ProjectPage.objects.create(workspace=workspace, project=project, page=project_page)
        wiki_page = _make_wiki_page(workspace, create_user, name="Wiki")

        listing = api_key_client.get(_pages_url(workspace.slug)).json()["results"]
        assert [p["id"] for p in listing] == [str(wiki_page.id)]
        assert api_key_client.get(_pages_url(workspace.slug, project_page.id)).status_code == 404

    @pytest.mark.django_db
    def test_guest_sees_only_own_pages_and_cannot_write(self, workspace, create_user):
        _make_wiki_page(workspace, create_user, name="Public")
        guest, guest_client = _add_member(workspace, "guest", ROLE_GUEST)
        own = _make_wiki_page(workspace, guest, name="Mine")

        listing = guest_client.get(_pages_url(workspace.slug)).json()["results"]
        assert [p["id"] for p in listing] == [str(own.id)]
        assert guest_client.post(_pages_url(workspace.slug), {"name": "x"}, format="json").status_code == 403
        assert guest_client.patch(_pages_url(workspace.slug, own.id), {"name": "x"}, format="json").status_code == 403
        assert guest_client.post(_collections_url(workspace.slug), {"name": "x"}, format="json").status_code == 403

    @pytest.mark.django_db
    def test_list_pagination_filters_and_archived(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        root = _make_wiki_page(workspace, create_user, name="Alpha", collection=collection, sort_order=10)
        child = _make_wiki_page(workspace, create_user, name="Beta", parent=root, sort_order=20)
        loose = _make_wiki_page(workspace, create_user, name="Gamma", sort_order=30)
        archived = _make_wiki_page(workspace, create_user, name="Old", archived_at="2024-01-01")
        url = _pages_url(workspace.slug)

        def ids(query=""):
            return [p["id"] for p in api_key_client.get(url + query).json()["results"]]

        assert ids() == [str(root.id), str(child.id), str(loose.id)]
        assert ids("?archived=true") == [str(archived.id)]
        assert ids(f"?collection={collection.id}") == [str(root.id)]
        assert ids(f"?parent={root.id}") == [str(child.id)]
        assert ids("?parent=null") == [str(root.id), str(loose.id)]
        assert ids("?search=gam") == [str(loose.id)]

        first = api_key_client.get(url + "?per_page=2").json()
        assert len(first["results"]) == 2
        assert first["next_page_results"] is True
        second = api_key_client.get(url + f"?per_page=2&cursor={first['next_cursor']}").json()
        assert [p["id"] for p in second["results"]] == [str(loose.id)]

    @pytest.mark.django_db
    def test_patch_metadata_and_move(self, api_key_client, workspace, create_user):
        collection = WikiCollection.objects.create(workspace=workspace, owned_by=create_user, name="Docs")
        page = _make_wiki_page(workspace, create_user)
        parent = _make_wiki_page(workspace, create_user, name="Parent", collection=collection)

        renamed = api_key_client.patch(_pages_url(workspace.slug, page.id), {"name": "Renamed"}, format="json")
        assert renamed.status_code == status.HTTP_200_OK
        assert renamed.json()["name"] == "Renamed"

        moved = api_key_client.patch(_pages_url(workspace.slug, page.id), {"parent": str(parent.id)}, format="json")
        assert moved.json()["parent"] == str(parent.id)

        placed = api_key_client.patch(
            _pages_url(workspace.slug, page.id), {"collection": str(collection.id)}, format="json"
        )
        assert placed.json()["collection"] == str(collection.id)
        assert placed.json()["parent"] is None

    @pytest.mark.django_db
    def test_cannot_move_page_under_itself_or_a_descendant(self, api_key_client, workspace, create_user):
        root = _make_wiki_page(workspace, create_user, name="Root")
        child = _make_wiki_page(workspace, create_user, name="Child", parent=root)
        grandchild = _make_wiki_page(workspace, create_user, name="Grandchild", parent=child)

        for target in (root, child, grandchild):
            response = api_key_client.patch(
                _pages_url(workspace.slug, root.id), {"parent": str(target.id)}, format="json"
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
        root.refresh_from_db()
        assert root.parent_id is None

    @pytest.mark.django_db
    def test_content_write_clears_binary_and_records_a_version(
        self, api_key_client, workspace, create_user, _no_celery
    ):
        page = _make_wiki_page(workspace, create_user, description_html="<p>old</p>", description_binary=b"yjs-state")

        response = api_key_client.patch(
            _pages_url(workspace.slug, page.id), {"description_html": "<p>new</p>"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description_html"] == "<p>new</p>"
        page.refresh_from_db()
        assert page.description_html == "<p>new</p>"
        assert page.description_binary is None
        assert page.description_json == {}
        _no_celery["page_transaction"].delay.assert_called_once()
        kwargs = _no_celery["track_page_version"].delay.call_args.kwargs
        assert kwargs["page_id"] == page.id
        assert "old" in kwargs["existing_instance"]

    @pytest.mark.django_db
    def test_metadata_only_patch_keeps_binary(self, api_key_client, workspace, create_user, _no_celery):
        page = _make_wiki_page(workspace, create_user, description_binary=b"yjs-state")

        api_key_client.patch(_pages_url(workspace.slug, page.id), {"name": "Renamed"}, format="json")

        page.refresh_from_db()
        assert page.description_binary == b"yjs-state"
        _no_celery["track_page_version"].delay.assert_not_called()

    @pytest.mark.django_db
    def test_rejected_content_leaves_the_page_untouched(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user, description_html="<p>old</p>", description_binary=b"yjs-state")

        response = api_key_client.patch(_pages_url(workspace.slug, page.id), {"description_html": 5}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        page.refresh_from_db()
        assert page.description_html == "<p>old</p>"
        assert page.description_binary == b"yjs-state"

    @pytest.mark.django_db
    def test_locked_and_archived_pages_refuse_edits(self, api_key_client, workspace, create_user):
        locked = _make_wiki_page(workspace, create_user, is_locked=True, description_html="<p>keep</p>")
        archived = _make_wiki_page(workspace, create_user, archived_at="2024-01-01")

        response = api_key_client.patch(
            _pages_url(workspace.slug, locked.id), {"description_html": "<p>x</p>"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == ERROR_CODES["PAGE_LOCKED"]
        locked.refresh_from_db()
        assert locked.description_html == "<p>keep</p>"

        response = api_key_client.patch(_pages_url(workspace.slug, archived.id), {"name": "x"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == ERROR_CODES["PAGE_ARCHIVED"]

    @pytest.mark.django_db
    def test_only_owner_changes_access(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user, access=Page.PUBLIC_ACCESS)
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        denied = member_client.patch(
            _pages_url(workspace.slug, page.id), {"access": Page.PRIVATE_ACCESS}, format="json"
        )
        assert denied.status_code == status.HTTP_403_FORBIDDEN
        page.refresh_from_db()
        assert page.access == Page.PUBLIC_ACCESS

        # Other members may still edit the page; an unchanged access value is not a change
        allowed = member_client.patch(
            _pages_url(workspace.slug, page.id), {"name": "Edited", "access": Page.PUBLIC_ACCESS}, format="json"
        )
        assert allowed.status_code == status.HTTP_200_OK

        assert (
            api_key_client.patch(
                _pages_url(workspace.slug, page.id), {"access": Page.PRIVATE_ACCESS}, format="json"
            ).json()["access"]
            == Page.PRIVATE_ACCESS
        )

    @pytest.mark.django_db
    def test_invalid_access_value(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        response = api_key_client.patch(_pages_url(workspace.slug, page.id), {"access": 9}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestWikiArchiveAndDelete:
    @pytest.mark.django_db
    def test_archive_cascades_and_restore(self, api_key_client, workspace, create_user):
        root = _make_wiki_page(workspace, create_user, name="Root")
        child = _make_wiki_page(workspace, create_user, name="Child", parent=root)

        response = api_key_client.post(_pages_url(workspace.slug, root.id, "archive/"))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["archived_at"]
        root.refresh_from_db()
        child.refresh_from_db()
        assert root.archived_at is not None
        assert child.archived_at is not None

        restored = api_key_client.delete(_pages_url(workspace.slug, root.id, "archive/"))
        assert restored.status_code == status.HTTP_204_NO_CONTENT
        root.refresh_from_db()
        child.refresh_from_db()
        assert root.archived_at is None
        assert child.archived_at is None

    @pytest.mark.django_db
    def test_restoring_a_sub_page_of_an_archived_parent_makes_it_a_root_page(
        self, api_key_client, workspace, create_user
    ):
        root = _make_wiki_page(workspace, create_user, name="Root")
        child = _make_wiki_page(workspace, create_user, name="Child", parent=root)
        api_key_client.post(_pages_url(workspace.slug, root.id, "archive/"))

        api_key_client.delete(_pages_url(workspace.slug, child.id, "archive/"))

        child.refresh_from_db()
        root.refresh_from_db()
        assert child.parent_id is None
        assert child.archived_at is None
        assert root.archived_at is not None

    @pytest.mark.django_db
    def test_only_owner_or_admin_archives(self, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        assert member_client.post(_pages_url(workspace.slug, page.id, "archive/")).status_code == 403
        page.refresh_from_db()
        assert page.archived_at is None

    @pytest.mark.django_db
    def test_delete_requires_archive_first(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)

        assert api_key_client.delete(_pages_url(workspace.slug, page.id)).status_code == status.HTTP_400_BAD_REQUEST
        assert Page.objects.filter(pk=page.id).exists()

    @pytest.mark.django_db
    def test_delete_moves_sub_pages_to_the_root(self, api_key_client, workspace, create_user):
        root = _make_wiki_page(workspace, create_user, name="Root")
        child = _make_wiki_page(workspace, create_user, name="Child", parent=root)
        api_key_client.post(_pages_url(workspace.slug, root.id, "archive/"))

        response = api_key_client.delete(_pages_url(workspace.slug, root.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Page.objects.filter(pk=root.id).exists()
        child.refresh_from_db()
        assert child.parent_id is None

    @pytest.mark.django_db
    def test_only_owner_or_admin_deletes(self, workspace, create_user):
        page = _make_wiki_page(workspace, create_user, archived_at="2024-01-01")
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        assert member_client.delete(_pages_url(workspace.slug, page.id)).status_code == 403
        assert Page.objects.filter(pk=page.id).exists()


@pytest.mark.contract
class TestWikiLockDuplicateVersions:
    @pytest.mark.django_db
    def test_lock_and_unlock(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)

        assert api_key_client.post(_pages_url(workspace.slug, page.id, "lock/")).status_code == 204
        page.refresh_from_db()
        assert page.is_locked is True
        assert api_key_client.get(_pages_url(workspace.slug, page.id)).json()["is_locked"] is True

        assert api_key_client.delete(_pages_url(workspace.slug, page.id, "lock/")).status_code == 204
        page.refresh_from_db()
        assert page.is_locked is False

    @pytest.mark.django_db
    def test_only_owner_or_admin_locks(self, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        _, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        assert member_client.post(_pages_url(workspace.slug, page.id, "lock/")).status_code == 403
        page.refresh_from_db()
        assert page.is_locked is False

        page.is_locked = True
        page.save()
        assert member_client.delete(_pages_url(workspace.slug, page.id, "lock/")).status_code == 403

    @pytest.mark.django_db
    def test_duplicate_is_owned_by_the_caller(self, workspace, create_user, _no_celery):
        source = _make_wiki_page(
            workspace,
            create_user,
            name="Guide",
            description_html="<p>copy me</p>",
            description_binary=b"yjs-state",
            is_locked=True,
        )
        member, member_client = _add_member(workspace, "member", ROLE_MEMBER)

        response = member_client.post(_pages_url(workspace.slug, source.id, "duplicate/"))

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == "Guide (Copy)"
        assert body["owned_by"] == str(member.id)
        assert body["description_html"] == "<p>copy me</p>"
        assert body["is_locked"] is False
        assert body["id"] != str(source.id)
        copy = Page.objects.get(pk=body["id"])
        assert copy.description_binary is None
        assert copy.is_global is True
        source.refresh_from_db()
        assert source.owned_by_id == create_user.id
        assert source.is_locked is True
        _no_celery["copy_s3_objects_of_description_and_assets"].delay.assert_called_once()

    @pytest.mark.django_db
    def test_versions_list_and_detail(self, api_key_client, workspace, create_user):
        page = _make_wiki_page(workspace, create_user)
        older = PageVersion.objects.create(
            workspace=workspace,
            page=page,
            owned_by=create_user,
            description_html="<p>v1</p>",
            last_saved_at="2024-01-01T00:00:00Z",
        )
        newer = PageVersion.objects.create(
            workspace=workspace,
            page=page,
            owned_by=create_user,
            description_html="<p>v2</p>",
            last_saved_at="2024-02-01T00:00:00Z",
        )
        other_page = _make_wiki_page(workspace, create_user, name="Other")
        PageVersion.objects.create(
            workspace=workspace, page=other_page, owned_by=create_user, description_html="<p>x</p>"
        )

        listing = api_key_client.get(_pages_url(workspace.slug, page.id, "versions/")).json()
        assert [v["id"] for v in listing["results"]] == [str(newer.id), str(older.id)]
        assert "description_html" not in listing["results"][0]

        detail = api_key_client.get(_pages_url(workspace.slug, page.id, f"versions/{older.id}/"))
        assert detail.status_code == status.HTTP_200_OK
        assert detail.json()["description_html"] == "<p>v1</p>"
        assert "description_binary" not in detail.json()

        # A version is only reachable through its own page
        foreign = PageVersion.objects.filter(page=other_page).first()
        assert api_key_client.get(_pages_url(workspace.slug, page.id, f"versions/{foreign.id}/")).status_code == 404
