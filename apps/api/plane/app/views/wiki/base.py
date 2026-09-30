# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
from datetime import datetime

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.http import StreamingHttpResponse

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.serializers import (
    PageBinaryUpdateSerializer,
    PageVersionDetailSerializer,
    PageVersionSerializer,
)
from plane.app.serializers.wiki import (
    WikiCollectionSerializer,
    WikiPageDetailSerializer,
    WikiPageSerializer,
)
from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.app.views.page.base import unarchive_archive_page_and_descendants
from plane.bgtasks.copy_s3_object import copy_s3_objects_of_description_and_assets
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version
from plane.bgtasks.recent_visited_task import recent_visited_task
from plane.db.models import (
    Page,
    PageVersion,
    UserFavorite,
    UserRecentVisit,
    WikiCollection,
    Workspace,
)
from plane.utils.error_codes import ERROR_CODES
from plane.utils.wiki import (
    SORT_ORDER_STEP,
    get_descendant_ids,
    is_workspace_admin,
    visible_wiki_pages,
    would_create_cycle,
)


class WikiCollectionViewSet(BaseViewSet):
    model = WikiCollection
    serializer_class = WikiCollectionSerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        user = self.request.user
        return (
            WikiCollection.objects.filter(workspace__slug=self.kwargs.get("slug"))
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

    def list(self, request, slug):
        return Response(WikiCollectionSerializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)

    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = WikiCollectionSerializer(data=request.data)
        if serializer.is_valid():
            last = WikiCollection.objects.filter(workspace=workspace).aggregate(last=Max("sort_order"))["last"]
            serializer.save(
                workspace=workspace,
                owned_by=request.user,
                sort_order=(last if last is not None else 0) + SORT_ORDER_STEP,
            )
            collection = self.get_queryset().get(pk=serializer.data["id"])
            return Response(WikiCollectionSerializer(collection).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_editable(self, request, slug, pk):
        collection = WikiCollection.objects.get(pk=pk, workspace__slug=slug)
        if collection.owned_by_id != request.user.id and not is_workspace_admin(request.user, slug):
            return collection, Response(
                {"error": "Only the collection owner or a workspace admin can change this collection"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return collection, None

    def partial_update(self, request, slug, pk):
        collection, error = self._get_editable(request, slug, pk)
        if error:
            return error
        serializer = WikiCollectionSerializer(collection, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                WikiCollectionSerializer(self.get_queryset().get(pk=pk)).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, slug, pk):
        """
        `?mode=transfer&target_collection=<id>` moves the pages into another collection first,
        `?mode=delete_pages` deletes the collection together with all of its pages.
        """
        collection, error = self._get_editable(request, slug, pk)
        if error:
            return error

        mode = request.query_params.get("mode", "delete_pages")
        pages = Page.objects.filter(collection=collection, workspace__slug=slug)

        if mode == "transfer":
            target_id = request.query_params.get("target_collection")
            if not target_id or str(target_id) == str(collection.id):
                return Response(
                    {"error": "A different target collection is required"}, status=status.HTTP_400_BAD_REQUEST
                )
            target = WikiCollection.objects.filter(pk=target_id, workspace__slug=slug).first()
            if target is None:
                return Response({"error": "Target collection not found"}, status=status.HTTP_404_NOT_FOUND)
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
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageViewSet(BaseViewSet):
    model = Page
    serializer_class = WikiPageSerializer
    permission_classes = [WorkspaceEntityPermission]
    search_fields = ["name"]

    def get_queryset(self):
        favorites = UserFavorite.objects.filter(
            user=self.request.user,
            entity_type="page",
            entity_identifier=OuterRef("pk"),
            workspace__slug=self.kwargs.get("slug"),
        )
        return (
            visible_wiki_pages(self.request.user, self.kwargs.get("slug"))
            .select_related("workspace", "owned_by")
            .annotate(is_favorite=Exists(favorites))
            .order_by("sort_order", "-created_at", "id")
        )

    def _get_page(self, slug, page_id):
        return self.get_queryset().get(pk=page_id)

    def _validate_relations(self, slug, data, page=None):
        """Check that parent/collection belong to this workspace and keep the hierarchy sane."""
        parent_id = data.get("parent")
        collection_id = data.get("collection")

        if parent_id:
            parent = self.get_queryset().filter(pk=parent_id, archived_at__isnull=True).first()
            if parent is None:
                return Response({"error": "Parent page not found"}, status=status.HTTP_404_NOT_FOUND)
            if page is not None and would_create_cycle(page.id, parent.id):
                return Response(
                    {"error": "A page cannot be moved under itself or one of its sub pages"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Nested pages inherit the collection from their root page
            data["collection"] = None
        elif collection_id:
            if not WikiCollection.objects.filter(pk=collection_id, workspace__slug=slug).exists():
                return Response({"error": "Collection not found"}, status=status.HTTP_404_NOT_FOUND)
            # A page placed straight into a collection becomes a root page
            data["parent"] = None
        return None

    def list(self, request, slug):
        queryset = self.get_queryset()
        if request.query_params.get("archived", "false").lower() == "true":
            queryset = queryset.filter(archived_at__isnull=False)
        else:
            queryset = queryset.filter(archived_at__isnull=True)
        return Response(WikiPageSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        data = request.data.copy()
        error = self._validate_relations(slug, data)
        if error:
            return error

        if "access" not in data:
            parent = Page.objects.filter(pk=data.get("parent")).first() if data.get("parent") else None
            if parent is not None:
                data["access"] = parent.access
            else:
                data["access"] = Page.PUBLIC_ACCESS if data.get("collection") else Page.PRIVATE_ACCESS

        serializer = WikiPageSerializer(data=data)
        if serializer.is_valid():
            page = serializer.save(
                workspace=workspace,
                owned_by=request.user,
                is_global=True,
                description_json={},
                description_html="<p></p>",
                description_binary=None,
            )
            page_transaction.delay(new_description_html="<p></p>", old_description_html=None, page_id=page.id)
            return Response(
                WikiPageDetailSerializer(self._get_page(slug, page.id)).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, slug, page_id):
        page = self._get_page(slug, page_id)
        if request.query_params.get("track_visit", "true").lower() == "true":
            recent_visited_task.delay(
                slug=slug,
                entity_name="page",
                entity_identifier=page_id,
                user_id=request.user.id,
                project_id=None,
            )
        return Response(WikiPageDetailSerializer(page).data, status=status.HTTP_200_OK)

    def partial_update(self, request, slug, page_id):
        page = self._get_page(slug, page_id)

        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)

        if page.access != request.data.get("access", page.access) and page.owned_by_id != request.user.id:
            return Response(
                {"error": "Access cannot be updated since this page is owned by someone else"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        error = self._validate_relations(slug, data, page=page)
        if error:
            return error

        serializer = WikiPageSerializer(page, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(WikiPageDetailSerializer(self._get_page(slug, page_id)).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def lock(self, request, slug, page_id):
        page = self._get_page(slug, page_id)
        page.is_locked = True
        page.save(update_fields=["is_locked", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def unlock(self, request, slug, page_id):
        page = self._get_page(slug, page_id)
        page.is_locked = False
        page.save(update_fields=["is_locked", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def access(self, request, slug, page_id):
        access = request.data.get("access", Page.PUBLIC_ACCESS)
        if access not in (Page.PUBLIC_ACCESS, Page.PRIVATE_ACCESS):
            return Response({"error": "Invalid access value"}, status=status.HTTP_400_BAD_REQUEST)
        page = self._get_page(slug, page_id)
        if page.access != access and page.owned_by_id != request.user.id:
            return Response(
                {"error": "Access cannot be updated since this page is owned by someone else"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page.access = access
        page.save(update_fields=["access", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _can_archive_or_delete(self, request, slug, page):
        return page.owned_by_id == request.user.id or is_workspace_admin(request.user, slug)

    def archive(self, request, slug, page_id):
        page = self._get_page(slug, page_id)
        if not self._can_archive_or_delete(request, slug, page):
            return Response({"error": "Only the owner or admin can archive the page"}, status=status.HTTP_403_FORBIDDEN)

        descendant_ids = get_descendant_ids(page_id)
        UserFavorite.objects.filter(
            workspace__slug=slug, entity_type="page", entity_identifier__in=descendant_ids
        ).delete(soft=False)

        archived_at = datetime.now()
        unarchive_archive_page_and_descendants(page_id, archived_at)
        return Response({"archived_at": str(archived_at)}, status=status.HTTP_200_OK)

    def unarchive(self, request, slug, page_id):
        page = self._get_page(slug, page_id)
        if not self._can_archive_or_delete(request, slug, page):
            return Response(
                {"error": "Only the owner or admin can un archive the page"}, status=status.HTTP_403_FORBIDDEN
            )

        # If the parent is still archived the page is restored as a root page
        if page.parent_id and page.parent.archived_at:
            page.parent = None
            page.save(update_fields=["parent"])

        unarchive_archive_page_and_descendants(page_id, None)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, slug, page_id):
        page = self._get_page(slug, page_id)

        if page.archived_at is None:
            return Response(
                {"error": "The page should be archived before deleting"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not self._can_archive_or_delete(request, slug, page):
            return Response({"error": "Only admin or owner can delete the page"}, status=status.HTTP_403_FORBIDDEN)

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


class WikiPageFavoriteViewSet(BaseViewSet):
    model = UserFavorite
    permission_classes = [WorkspaceEntityPermission]

    def create(self, request, slug, page_id):
        page = visible_wiki_pages(request.user, slug).get(pk=page_id)
        UserFavorite.objects.get_or_create(
            workspace_id=page.workspace_id,
            project=None,
            user=request.user,
            entity_type="page",
            entity_identifier=page.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, slug, page_id):
        UserFavorite.objects.filter(
            workspace__slug=slug, user=request.user, entity_identifier=page_id, entity_type="page"
        ).delete(soft=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageDescriptionViewSet(BaseViewSet):
    permission_classes = [WorkspaceEntityPermission]

    def _get_page(self, request, slug, page_id):
        return visible_wiki_pages(request.user, slug).get(pk=page_id)

    def retrieve(self, request, slug, page_id):
        binary_data = self._get_page(request, slug, page_id).description_binary

        def stream_data():
            yield binary_data or b""

        response = StreamingHttpResponse(stream_data(), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="page_description.bin"'
        return response

    def partial_update(self, request, slug, page_id):
        page = self._get_page(request, slug, page_id)

        if page.is_locked:
            return Response(
                {"error_code": ERROR_CODES["PAGE_LOCKED"], "error_message": "PAGE_LOCKED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if page.archived_at:
            return Response(
                {"error_code": ERROR_CODES["PAGE_ARCHIVED"], "error_message": "PAGE_ARCHIVED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_description_html = page.description_html
        existing_instance = json.dumps({"description_html": old_description_html}, cls=DjangoJSONEncoder)

        serializer = PageBinaryUpdateSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data.get("description_html"):
                page_transaction.delay(
                    new_description_html=request.data.get("description_html", "<p></p>"),
                    old_description_html=old_description_html,
                    page_id=page_id,
                )
            track_page_version.delay(page_id=page_id, existing_instance=existing_instance, user_id=request.user.id)
            return Response({"message": "Updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WikiPageVersionEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, page_id, pk=None):
        # Resolve the page through the visibility rules so private pages stay private
        page = visible_wiki_pages(request.user, slug).get(pk=page_id)
        versions = PageVersion.objects.filter(workspace__slug=slug, page_id=page.id)
        if pk:
            return Response(PageVersionDetailSerializer(versions.get(pk=pk)).data, status=status.HTTP_200_OK)
        return Response(PageVersionSerializer(versions, many=True).data, status=status.HTTP_200_OK)


class WikiPageDuplicateEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def post(self, request, slug, page_id):
        page = visible_wiki_pages(request.user, slug).get(pk=page_id)

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

        duplicate = visible_wiki_pages(request.user, slug).get(pk=page.id)
        return Response(WikiPageDetailSerializer(duplicate).data, status=status.HTTP_201_CREATED)
