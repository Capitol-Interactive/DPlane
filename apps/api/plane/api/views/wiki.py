# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Max, Q
from django.utils import timezone

# Third party imports
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiRequest, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.api.serializers import (
    WikiCollectionSerializer,
    WikiPageDetailSerializer,
    WikiPageSerializer,
    WikiPageVersionDetailSerializer,
    WikiPageVersionSerializer,
)
from plane.api.views.base import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.page.base import unarchive_archive_page_and_descendants
from plane.bgtasks.copy_s3_object import copy_s3_objects_of_description_and_assets
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version
from plane.db.models import Page, PageVersion, UserFavorite, UserRecentVisit, WikiCollection, Workspace
from plane.utils.content_validator import validate_html_content
from plane.utils.error_codes import ERROR_CODES
from plane.utils.openapi import DELETED_RESPONSE, create_paginated_response
from plane.utils.openapi.decorators import wiki_docs
from plane.utils.wiki import (
    SORT_ORDER_STEP,
    get_descendant_ids,
    is_workspace_admin,
    visible_wiki_pages,
    would_create_cycle,
)

# Token-authenticated (X-Api-Key) access to the workspace wiki. It shares the visibility and
# hierarchy rules of the session endpoints in `plane.app.views.wiki` through `plane.utils.wiki`.

PAGE_ORDERING = ("sort_order", "-created_at", "id")


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _page_state_error(error_name):
    return Response(
        {"error_code": ERROR_CODES[error_name], "error_message": error_name},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _body_error(request):
    if not isinstance(request.data, dict):
        return _error("Request body must be a JSON object.")
    return None


def _clean_description(description_html):
    """Sanitize a `description_html` value. Returns (clean_html, error_response)."""
    if not isinstance(description_html, str):
        return None, _error("description_html must be a string")
    is_valid, error_message, clean_html = validate_html_content(description_html)
    if not is_valid:
        return None, _error(error_message)
    return clean_html or "<p></p>", None


def _dump_html(description_html):
    return json.dumps({"description_html": description_html}, cls=DjangoJSONEncoder)


def _can_archive_or_delete(request, slug, page):
    return page.owned_by_id == request.user.id or is_workspace_admin(request.user, slug)


class WikiCollectionListCreateAPIEndpoint(BaseAPIView):
    """List and create wiki collections."""

    permission_classes = [WorkspaceEntityPermission]
    serializer_class = WikiCollectionSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            WikiCollection.objects.filter(workspace__slug=self.workspace_slug)
            .annotate(
                page_count=Count(
                    "pages",
                    filter=Q(pages__archived_at__isnull=True, pages__deleted_at__isnull=True)
                    & (Q(pages__access=Page.PUBLIC_ACCESS) | Q(pages__owned_by=user)),
                    distinct=True,
                )
            )
            .order_by("sort_order", "-created_at")
        )

    @wiki_docs(
        operation_id="list_wiki_collections",
        summary="List wiki collections",
        description="List the wiki collections of the workspace, including how many pages you can see in each.",
        responses={200: OpenApiResponse(description="Wiki collections", response=WikiCollectionSerializer(many=True))},
    )
    def get(self, request, slug):
        return Response(WikiCollectionSerializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="create_wiki_collection",
        summary="Create a wiki collection",
        description="Create a wiki collection. It is added after the existing collections.",
        request=OpenApiRequest(request=WikiCollectionSerializer),
        responses={201: OpenApiResponse(description="Wiki collection created", response=WikiCollectionSerializer)},
    )
    def post(self, request, slug):
        if error := _body_error(request):
            return error
        workspace = Workspace.objects.get(slug=slug)
        serializer = WikiCollectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        last = WikiCollection.objects.filter(workspace=workspace).aggregate(last=Max("sort_order"))["last"]
        collection = serializer.save(
            workspace=workspace,
            owned_by=request.user,
            sort_order=serializer.validated_data.get("sort_order", (last if last is not None else 0) + SORT_ORDER_STEP),
        )
        return Response(
            WikiCollectionSerializer(self.get_queryset().get(pk=collection.pk)).data, status=status.HTTP_201_CREATED
        )


class WikiCollectionDetailAPIEndpoint(BaseAPIView):
    """Retrieve, rename and delete a wiki collection."""

    permission_classes = [WorkspaceEntityPermission]
    serializer_class = WikiCollectionSerializer

    def get_queryset(self):
        return WikiCollectionListCreateAPIEndpoint.get_queryset(self)

    def _get_editable(self, request, slug, pk):
        collection = self.get_queryset().get(pk=pk)
        if collection.owned_by_id != request.user.id and not is_workspace_admin(request.user, slug):
            return collection, _error(
                "Only the collection owner or a workspace admin can change this collection",
                status.HTTP_403_FORBIDDEN,
            )
        return collection, None

    @wiki_docs(
        operation_id="retrieve_wiki_collection",
        summary="Retrieve a wiki collection",
        description="Retrieve a wiki collection by ID.",
        responses={200: OpenApiResponse(description="Wiki collection", response=WikiCollectionSerializer)},
    )
    def get(self, request, slug, pk):
        return Response(WikiCollectionSerializer(self.get_queryset().get(pk=pk)).data, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="update_wiki_collection",
        summary="Update a wiki collection",
        description="Rename or reorder a wiki collection. Only its owner or a workspace admin can do this.",
        request=OpenApiRequest(request=WikiCollectionSerializer),
        responses={200: OpenApiResponse(description="Wiki collection updated", response=WikiCollectionSerializer)},
    )
    def patch(self, request, slug, pk):
        if error := _body_error(request):
            return error
        collection, error = self._get_editable(request, slug, pk)
        if error:
            return error
        serializer = WikiCollectionSerializer(collection, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(WikiCollectionSerializer(self.get_queryset().get(pk=pk)).data, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="delete_wiki_collection",
        summary="Delete a wiki collection",
        description=(
            "Delete a wiki collection. You must say what happens to its pages: `mode=transfer` moves them into "
            "`target_collection`, `mode=delete_pages` deletes them (and their sub pages) with the collection."
        ),
        parameters=[
            OpenApiParameter(
                name="mode",
                description="`transfer` or `delete_pages`. Required.",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="target_collection",
                description="Collection that receives the pages when `mode=transfer`.",
                required=False,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={204: DELETED_RESPONSE},
    )
    def delete(self, request, slug, pk):
        collection, error = self._get_editable(request, slug, pk)
        if error:
            return error

        # There is no default: a script that forgets the mode must not wipe a collection's pages
        mode = request.query_params.get("mode")
        pages = Page.objects.filter(collection_id=collection.id, workspace__slug=slug)

        if mode == "transfer":
            target_id = request.query_params.get("target_collection")
            if not target_id or str(target_id) == str(collection.id):
                return _error("A different target_collection is required for mode=transfer")
            target = WikiCollection.objects.filter(pk=target_id, workspace__slug=slug).first()
            if target is None:
                return _error("Target collection not found", status.HTTP_404_NOT_FOUND)
            pages.update(collection=target)
        elif mode == "delete_pages":
            page_ids = set()
            for root_id in pages.values_list("id", flat=True):
                page_ids.update(get_descendant_ids(root_id))
            UserFavorite.objects.filter(
                workspace__slug=slug, entity_type="page", entity_identifier__in=page_ids
            ).delete(soft=False)
            UserRecentVisit.objects.filter(
                workspace__slug=slug, entity_name="page", entity_identifier__in=page_ids
            ).delete(soft=False)
            Page.objects.filter(pk__in=page_ids).delete()
        else:
            return _error("mode is required and must be `transfer` or `delete_pages`")

        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageBaseEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]
    serializer_class = WikiPageSerializer

    def get_queryset(self):
        return visible_wiki_pages(self.request.user, self.workspace_slug).select_related("workspace", "owned_by")

    def get_page(self, page_id):
        return self.get_queryset().get(pk=page_id)

    def validate_relations(self, slug, data, page=None):
        """Check that parent/collection belong to this workspace and keep the hierarchy sane."""
        parent_id = data.get("parent")
        collection_id = data.get("collection")

        if parent_id:
            parent = self.get_queryset().filter(pk=parent_id, archived_at__isnull=True).first()
            if parent is None:
                return _error("Parent page not found", status.HTTP_404_NOT_FOUND)
            if page is not None and would_create_cycle(page.id, parent.id):
                return _error("A page cannot be moved under itself or one of its sub pages")
            # Nested pages inherit the collection from their root page
            data["collection"] = None
        elif collection_id:
            if not WikiCollection.objects.filter(pk=collection_id, workspace__slug=slug).exists():
                return _error("Collection not found", status.HTTP_404_NOT_FOUND)
            # A page placed straight into a collection becomes a root page
            data["parent"] = None
        return None


class WikiPageListCreateAPIEndpoint(WikiPageBaseEndpoint):
    """List and create wiki pages."""

    @wiki_docs(
        operation_id="list_wiki_pages",
        summary="List wiki pages",
        description=(
            "List the wiki pages you can see, without their content. Private pages of other members never appear."
        ),
        parameters=[
            OpenApiParameter(
                name="archived",
                description="`true` lists archived pages instead of active ones.",
                required=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="collection",
                description="Only root pages placed directly in this collection.",
                required=False,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="parent",
                description="Only sub pages of this page, or `null` for pages that have no parent.",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="search",
                description="Case-insensitive match on the page name.",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: create_paginated_response(
                WikiPageSerializer, "PaginatedWikiPageResponse", "Paginated wiki pages", "Paginated Wiki Pages"
            )
        },
    )
    def get(self, request, slug):
        params = request.query_params
        queryset = self.get_queryset()

        if params.get("archived", "false").lower() == "true":
            queryset = queryset.filter(archived_at__isnull=False)
        else:
            queryset = queryset.filter(archived_at__isnull=True)

        if collection := params.get("collection"):
            queryset = queryset.filter(collection_id=collection)
        if parent := params.get("parent"):
            queryset = queryset.filter(parent__isnull=True) if parent == "null" else queryset.filter(parent_id=parent)
        if search := params.get("search"):
            queryset = queryset.filter(name__icontains=search)

        return self.paginate(
            request=request,
            queryset=queryset.order_by(*PAGE_ORDERING),
            on_results=lambda pages: WikiPageSerializer(pages, many=True).data,
            default_per_page=20,
            max_per_page=100,
        )

    @wiki_docs(
        operation_id="create_wiki_page",
        summary="Create a wiki page",
        description=(
            "Create a wiki page you own. `description_html` is sanitized before it is stored. A page created in a "
            "collection is public unless you say otherwise; without a collection it is private. A sub page inherits "
            "its parent's access."
        ),
        request=OpenApiRequest(request=WikiPageSerializer),
        responses={201: OpenApiResponse(description="Wiki page created", response=WikiPageDetailSerializer)},
    )
    def post(self, request, slug):
        if error := _body_error(request):
            return error
        workspace = Workspace.objects.get(slug=slug)
        data = request.data.copy()

        description_html = "<p></p>"
        if "description_html" in data:
            description_html, error = _clean_description(data["description_html"])
            if error:
                return error

        if error := self.validate_relations(slug, data):
            return error

        if "access" not in data:
            parent = self.get_queryset().filter(pk=data["parent"]).first() if data.get("parent") else None
            if parent is not None:
                data["access"] = parent.access
            else:
                data["access"] = Page.PUBLIC_ACCESS if data.get("collection") else Page.PRIVATE_ACCESS

        serializer = WikiPageSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # The editor rebuilds its document from the HTML while the binary is empty
        page = serializer.save(
            workspace=workspace,
            owned_by=request.user,
            is_global=True,
            description_json={},
            description_html=description_html,
            description_binary=None,
        )
        page_transaction.delay(new_description_html=description_html, old_description_html=None, page_id=page.id)
        return Response(WikiPageDetailSerializer(self.get_page(page.id)).data, status=status.HTTP_201_CREATED)


class WikiPageDetailAPIEndpoint(WikiPageBaseEndpoint):
    """Retrieve, update and delete a wiki page."""

    @wiki_docs(
        operation_id="retrieve_wiki_page",
        summary="Retrieve a wiki page",
        description="Retrieve a wiki page including its HTML content.",
        responses={200: OpenApiResponse(description="Wiki page", response=WikiPageDetailSerializer)},
    )
    def get(self, request, slug, page_id):
        return Response(WikiPageDetailSerializer(self.get_page(page_id)).data, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="update_wiki_page",
        summary="Update a wiki page",
        description=(
            "Update a wiki page's fields and/or replace its content with `description_html`. Locked and archived "
            "pages cannot be edited. Only the owner can change `access`.\n\n"
            "If someone has the page open in the editor when you replace its content, their editor keeps its "
            "in-memory copy and can overwrite your change the next time it saves. A browser that opened the page "
            "before also keeps a local copy and may show the old and new text together."
        ),
        request=OpenApiRequest(request=WikiPageSerializer),
        responses={200: OpenApiResponse(description="Wiki page updated", response=WikiPageDetailSerializer)},
    )
    def patch(self, request, slug, page_id):
        if error := _body_error(request):
            return error
        page = self.get_page(page_id)

        if page.is_locked:
            return _page_state_error("PAGE_LOCKED")
        if page.archived_at:
            return _page_state_error("PAGE_ARCHIVED")

        data = request.data.copy()

        clean_html = None
        if "description_html" in data:
            clean_html, error = _clean_description(data["description_html"])
            if error:
                return error

        if error := self.validate_relations(slug, data, page=page):
            return error

        old_description_html = page.description_html
        serializer = WikiPageSerializer(page, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_access = serializer.validated_data.get("access", page.access)
        if new_access != page.access and page.owned_by_id != request.user.id:
            return _error("Access can only be changed by the page owner", status.HTTP_403_FORBIDDEN)

        if clean_html is not None:
            # Dropping the binary makes the live editor rebuild its document from the new HTML
            serializer.save(description_html=clean_html, description_json={}, description_binary=None)
            page_transaction.delay(
                new_description_html=clean_html, old_description_html=old_description_html, page_id=page.id
            )
            track_page_version.delay(
                page_id=page.id,
                existing_instance=_dump_html(old_description_html),
                user_id=request.user.id,
            )
        else:
            serializer.save()
        return Response(WikiPageDetailSerializer(self.get_page(page_id)).data, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="delete_wiki_page",
        summary="Delete a wiki page",
        description=(
            "Permanently delete an archived wiki page. Archive it first. Its sub pages move up to the top level. "
            "Only the owner or a workspace admin can do this."
        ),
        responses={204: DELETED_RESPONSE},
    )
    def delete(self, request, slug, page_id):
        page = self.get_page(page_id)

        if page.archived_at is None:
            return _error("The page should be archived before deleting")
        if not _can_archive_or_delete(request, slug, page):
            return _error("Only the owner or a workspace admin can delete the page", status.HTTP_403_FORBIDDEN)

        # Sub pages move up to the root instead of being deleted with their parent
        Page.objects.filter(parent_id=page_id, workspace__slug=slug).update(parent=None)

        page.delete()
        UserFavorite.objects.filter(workspace__slug=slug, entity_identifier=page_id, entity_type="page").delete(
            soft=False
        )
        UserRecentVisit.objects.filter(workspace__slug=slug, entity_identifier=page_id, entity_name="page").delete(
            soft=False
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageArchiveAPIEndpoint(WikiPageBaseEndpoint):
    """Archive and restore a wiki page together with its sub pages."""

    @wiki_docs(
        operation_id="archive_wiki_page",
        summary="Archive a wiki page",
        description="Archive a wiki page and all of its sub pages. Only the owner or a workspace admin can do this.",
        responses={200: OpenApiResponse(description="Wiki page archived")},
    )
    def post(self, request, slug, page_id):
        page = self.get_page(page_id)
        if not _can_archive_or_delete(request, slug, page):
            return _error("Only the owner or a workspace admin can archive the page", status.HTTP_403_FORBIDDEN)

        descendant_ids = get_descendant_ids(page_id)
        UserFavorite.objects.filter(
            workspace__slug=slug, entity_type="page", entity_identifier__in=descendant_ids
        ).delete(soft=False)

        archived_at = timezone.now().date()
        unarchive_archive_page_and_descendants(page_id, archived_at)
        return Response({"archived_at": archived_at}, status=status.HTTP_200_OK)

    @wiki_docs(
        operation_id="unarchive_wiki_page",
        summary="Restore a wiki page",
        description=(
            "Restore an archived wiki page and its sub pages. "
            "If its parent is still archived it becomes a top level page."
        ),
        responses={204: OpenApiResponse(description="Wiki page restored")},
    )
    def delete(self, request, slug, page_id):
        page = self.get_page(page_id)
        if not _can_archive_or_delete(request, slug, page):
            return _error("Only the owner or a workspace admin can restore the page", status.HTTP_403_FORBIDDEN)

        # If the parent is still archived the page is restored as a root page
        if page.parent_id and page.parent.archived_at:
            page.parent = None
            page.save(update_fields=["parent"])

        unarchive_archive_page_and_descendants(page_id, None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageLockAPIEndpoint(WikiPageBaseEndpoint):
    """Lock and unlock a wiki page. A locked page cannot be edited."""

    def _set_lock(self, request, slug, page_id, locked):
        page = self.get_page(page_id)
        if not _can_archive_or_delete(request, slug, page):
            return _error("Only the owner or a workspace admin can lock or unlock the page", status.HTTP_403_FORBIDDEN)
        page.is_locked = locked
        page.save(update_fields=["is_locked", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @wiki_docs(
        operation_id="lock_wiki_page",
        summary="Lock a wiki page",
        description="Lock a wiki page so it cannot be edited. Only the owner or a workspace admin can do this.",
        responses={204: OpenApiResponse(description="Wiki page locked")},
    )
    def post(self, request, slug, page_id):
        return self._set_lock(request, slug, page_id, True)

    @wiki_docs(
        operation_id="unlock_wiki_page",
        summary="Unlock a wiki page",
        description="Unlock a wiki page. Only the owner or a workspace admin can do this.",
        responses={204: OpenApiResponse(description="Wiki page unlocked")},
    )
    def delete(self, request, slug, page_id):
        return self._set_lock(request, slug, page_id, False)


class WikiPageDuplicateAPIEndpoint(WikiPageBaseEndpoint):
    @wiki_docs(
        operation_id="duplicate_wiki_page",
        summary="Duplicate a wiki page",
        description="Copy a wiki page you can see. You own the copy, and it starts unlocked.",
        responses={201: OpenApiResponse(description="Wiki page duplicated", response=WikiPageDetailSerializer)},
    )
    def post(self, request, slug, page_id):
        page = self.get_page(page_id)

        page.pk = None
        page.name = f"{page.name} (Copy)"
        page.description_binary = None
        page.owned_by = request.user
        page.created_by = request.user
        page.updated_by = request.user
        page.is_locked = False
        page.archived_at = None
        page.save()

        page_transaction.delay(new_description_html=page.description_html, old_description_html=None, page_id=page.id)
        copy_s3_objects_of_description_and_assets.delay(
            entity_name="PAGE",
            entity_identifier=page.id,
            project_id=None,
            slug=slug,
            user_id=request.user.id,
        )
        return Response(WikiPageDetailSerializer(self.get_page(page.id)).data, status=status.HTTP_201_CREATED)


class WikiPageVersionListAPIEndpoint(WikiPageBaseEndpoint):
    @wiki_docs(
        operation_id="list_wiki_page_versions",
        summary="List wiki page versions",
        description="List the saved versions of a wiki page, newest first, without their content.",
        responses={
            200: create_paginated_response(
                WikiPageVersionSerializer,
                "PaginatedWikiPageVersionResponse",
                "Paginated wiki page versions",
                "Paginated Wiki Page Versions",
            )
        },
    )
    def get(self, request, slug, page_id):
        # Resolve the page through the visibility rules so private pages stay private
        page = self.get_page(page_id)
        versions = PageVersion.objects.filter(workspace__slug=slug, page_id=page.id).order_by("-last_saved_at", "id")
        return self.paginate(
            request=request,
            queryset=versions,
            on_results=lambda items: WikiPageVersionSerializer(items, many=True).data,
            default_per_page=20,
            max_per_page=100,
        )


class WikiPageVersionDetailAPIEndpoint(WikiPageBaseEndpoint):
    @wiki_docs(
        operation_id="retrieve_wiki_page_version",
        summary="Retrieve a wiki page version",
        description="Retrieve one saved version of a wiki page including its HTML and JSON content.",
        responses={200: OpenApiResponse(description="Wiki page version", response=WikiPageVersionDetailSerializer)},
    )
    def get(self, request, slug, page_id, pk):
        page = self.get_page(page_id)
        version = PageVersion.objects.get(pk=pk, workspace__slug=slug, page_id=page.id)
        return Response(WikiPageVersionDetailSerializer(version).data, status=status.HTTP_200_OK)
