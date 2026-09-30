# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Page, PageVersion, WikiCollection
from .base import BaseSerializer


class WikiCollectionSerializer(BaseSerializer):
    """A group of wiki pages."""

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
        ]
        read_only_fields = ["workspace", "owned_by", "page_count"]


class WikiPageSerializer(BaseSerializer):
    """A wiki page without its body, used for lists and writes."""

    # A plain integer rather than the model's choices: another v1 serializer has an `access` enum
    # of its own, and two enums on one field name would rename the existing schema component.
    access = serializers.IntegerField(
        required=False, help_text=f"{Page.PUBLIC_ACCESS} for public, {Page.PRIVATE_ACCESS} for private"
    )

    def validate_access(self, value):
        if value not in (Page.PUBLIC_ACCESS, Page.PRIVATE_ACCESS):
            raise serializers.ValidationError(
                f"access must be {Page.PUBLIC_ACCESS} (public) or {Page.PRIVATE_ACCESS} (private)"
            )
        return value

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
            "is_locked",
            "archived_at",
            "workspace",
            "logo_props",
            "view_props",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["workspace", "owned_by", "archived_at", "is_locked"]


class WikiPageDetailSerializer(WikiPageSerializer):
    """A wiki page together with its HTML body."""

    description_html = serializers.CharField(read_only=True)

    class Meta(WikiPageSerializer.Meta):
        fields = WikiPageSerializer.Meta.fields + ["description_html"]


class WikiPageVersionSerializer(BaseSerializer):
    class Meta:
        model = PageVersion
        fields = ["id", "page", "owned_by", "last_saved_at", "created_at", "updated_at"]
        read_only_fields = fields


class WikiPageVersionDetailSerializer(BaseSerializer):
    class Meta:
        model = PageVersion
        fields = [
            "id",
            "page",
            "owned_by",
            "last_saved_at",
            "description_html",
            "description_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
