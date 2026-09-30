# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Query helpers shared by the session (app) and API-token (api/v1) wiki endpoints.

Keeping them in one place means both surfaces apply the same visibility and hierarchy rules.
"""

# Django imports
from django.db import connection
from django.db.models import Exists, OuterRef, Q

# Module imports
from plane.app.permissions import ROLE
from plane.db.models import Page, ProjectPage, WorkspaceMember

MAX_ANCESTRY_DEPTH = 100
SORT_ORDER_STEP = 10000


def get_workspace_role(user, slug):
    return (
        WorkspaceMember.objects.filter(workspace__slug=slug, member=user, is_active=True)
        .values_list("role", flat=True)
        .first()
    )


def is_workspace_admin(user, slug):
    return get_workspace_role(user, slug) == ROLE.ADMIN.value


def wiki_pages(slug):
    """Workspace wiki pages: global pages that are not linked to any project."""
    return (
        Page.objects.filter(workspace__slug=slug, is_global=True)
        .annotate(in_project=Exists(ProjectPage.objects.filter(page_id=OuterRef("id"))))
        .filter(in_project=False)
    )


def visible_wiki_pages(user, slug):
    """Wiki pages the user may see: their own plus public ones. Guests only see their own."""
    queryset = wiki_pages(slug)
    if get_workspace_role(user, slug) == ROLE.GUEST.value:
        return queryset.filter(owned_by=user)
    return queryset.filter(Q(owned_by=user) | Q(access=Page.PUBLIC_ACCESS))


def get_descendant_ids(page_id):
    sql = """
    WITH RECURSIVE descendants AS (
        SELECT id FROM pages WHERE id = %s AND deleted_at IS NULL
        UNION ALL
        SELECT pages.id FROM pages, descendants
        WHERE pages.parent_id = descendants.id AND pages.deleted_at IS NULL
    )
    SELECT id FROM descendants;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [page_id])
        return [row[0] for row in cursor.fetchall()]


def would_create_cycle(page_id, new_parent_id):
    """True if `new_parent_id` is the page itself or one of its descendants."""
    current = new_parent_id
    for _ in range(MAX_ANCESTRY_DEPTH):
        if current is None:
            return False
        if str(current) == str(page_id):
            return True
        current = Page.objects.filter(pk=current).values_list("parent_id", flat=True).first()
    return True
