# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views import (
    WikiCollectionListCreateAPIEndpoint,
    WikiCollectionDetailAPIEndpoint,
    WikiPageListCreateAPIEndpoint,
    WikiPageDetailAPIEndpoint,
    WikiPageArchiveAPIEndpoint,
    WikiPageLockAPIEndpoint,
    WikiPageDuplicateAPIEndpoint,
    WikiPageVersionListAPIEndpoint,
    WikiPageVersionDetailAPIEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/wiki/collections/",
        WikiCollectionListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="wiki-collections",
    ),
    path(
        "workspaces/<str:slug>/wiki/collections/<uuid:pk>/",
        WikiCollectionDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="wiki-collection-detail",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/",
        WikiPageListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="wiki-pages",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/",
        WikiPageDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="wiki-page-detail",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/archive/",
        WikiPageArchiveAPIEndpoint.as_view(http_method_names=["post", "delete"]),
        name="wiki-page-archive",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/lock/",
        WikiPageLockAPIEndpoint.as_view(http_method_names=["post", "delete"]),
        name="wiki-page-lock",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/duplicate/",
        WikiPageDuplicateAPIEndpoint.as_view(http_method_names=["post"]),
        name="wiki-page-duplicate",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/",
        WikiPageVersionListAPIEndpoint.as_view(http_method_names=["get"]),
        name="wiki-page-versions",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/<uuid:pk>/",
        WikiPageVersionDetailAPIEndpoint.as_view(http_method_names=["get"]),
        name="wiki-page-version-detail",
    ),
]
