# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Page, WikiCollection
from .base import BaseSerializer


class WikiCollectionSerializer(BaseSerializer):
    page_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = WikiCollection
        fields = [
            "id",
            "name",
            "logo_props",
            "sort_order",
            "owned_by",
            "workspace",
            "page_count",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = ["workspace", "owned_by"]


class WikiPageSerializer(BaseSerializer):
    is_favorite = serializers.BooleanField(read_only=True, required=False)
    # Kept so the shared web page store (TPage) can consume wiki pages unchanged
    label_ids = serializers.SerializerMethodField()
    project_ids = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "owned_by",
            "access",
            "color",
            "parent",
            "collection",
            "sort_order",
            "is_favorite",
            "is_locked",
            "archived_at",
            "workspace",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "view_props",
            "logo_props",
            "label_ids",
            "project_ids",
        ]
        read_only_fields = ["workspace", "owned_by", "archived_at", "is_locked"]

    def get_label_ids(self, obj):
        return []

    def get_project_ids(self, obj):
        return []


class WikiPageDetailSerializer(WikiPageSerializer):
    description_html = serializers.CharField(required=False)

    class Meta(WikiPageSerializer.Meta):
        fields = WikiPageSerializer.Meta.fields + ["description_html"]
