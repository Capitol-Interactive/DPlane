# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    WikiCollectionViewSet,
    WikiPageViewSet,
    WikiPageFavoriteViewSet,
    WikiPageDescriptionViewSet,
    WikiPageVersionEndpoint,
    WikiPageDuplicateEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/wiki/collections/",
        WikiCollectionViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-collections",
    ),
    path(
        "workspaces/<str:slug>/wiki/collections/<uuid:pk>/",
        WikiCollectionViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="wiki-collections",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/",
        WikiPageViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-pages",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/",
        WikiPageViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="wiki-pages",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/favorite/",
        WikiPageFavoriteViewSet.as_view({"post": "create", "delete": "destroy"}),
        name="wiki-page-favorite",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/archive/",
        WikiPageViewSet.as_view({"post": "archive", "delete": "unarchive"}),
        name="wiki-page-archive",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/lock/",
        WikiPageViewSet.as_view({"post": "lock", "delete": "unlock"}),
        name="wiki-page-lock",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/access/",
        WikiPageViewSet.as_view({"post": "access"}),
        name="wiki-page-access",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/description/",
        WikiPageDescriptionViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="wiki-page-description",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/",
        WikiPageVersionEndpoint.as_view(),
        name="wiki-page-versions",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/<uuid:pk>/",
        WikiPageVersionEndpoint.as_view(),
        name="wiki-page-versions",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/duplicate/",
        WikiPageDuplicateEndpoint.as_view(),
        name="wiki-page-duplicate",
    ),
]
