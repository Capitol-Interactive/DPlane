# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.management import BaseCommand, CommandError

# Module imports
from plane.db.models import APIToken, User, Workspace, WorkspaceMember


class Command(BaseCommand):
    help = (
        "Create or update an agent: a bot user (no login) that acts through an API token. "
        "Adds it to the workspace and prints a new API token when it has none (or with --new-token)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, help="Workspace slug")
        parser.add_argument("--email", required=True, help="Email for the agent's user, e.g. fiona@agents.example.com")
        parser.add_argument("--name", required=True, help="Display name, e.g. 'Finance Fiona'")
        parser.add_argument("--role", default="", help="Job title shown on the Agents page (30 characters at most)")
        parser.add_argument("--reports-to", default="", help="Email of the user (person or agent) it reports to")
        parser.add_argument("--workspace-role", type=int, default=15, choices=[5, 15, 20], help="5 guest, 15 member")
        parser.add_argument("--new-token", action="store_true", help="Create another API token even if one exists")

    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(slug=options["workspace"]).first()
        if not workspace:
            raise CommandError(f"Workspace '{options['workspace']}' not found")
        if len(options["role"]) > 30:
            raise CommandError("--role must be 30 characters or fewer")

        manager = None
        if options["reports_to"]:
            manager = User.objects.filter(email=options["reports_to"]).first()
            if not manager:
                raise CommandError(f"User '{options['reports_to']}' not found")

        first_name, _, last_name = options["name"].partition(" ")
        agent, created = User.objects.get_or_create(
            email=options["email"], defaults={"username": options["email"], "is_bot": True}
        )
        if not created and not agent.is_bot:
            raise CommandError(f"{options['email']} is a regular user, not an agent")

        agent.first_name = first_name
        agent.last_name = last_name
        agent.display_name = options["name"]
        agent.is_bot = True
        agent.bot_type = options["role"] or None
        agent.bot_reports_to = manager
        agent.set_unusable_password()
        agent.save()

        membership, _ = WorkspaceMember.objects.get_or_create(
            workspace=workspace, member=agent, defaults={"role": options["workspace_role"]}
        )
        if not membership.is_active or membership.role != options["workspace_role"]:
            membership.is_active = True
            membership.role = options["workspace_role"]
            membership.save()

        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} agent {agent.display_name}"))

        has_token = APIToken.objects.filter(user=agent, workspace=workspace, is_active=True).exists()
        if options["new_token"] or not has_token:
            token = APIToken.objects.create(
                user=agent,
                user_type=1,
                workspace=workspace,
                label=f"{agent.display_name} agent",
                description="Created by the create_agent command",
            )
            self.stdout.write(f"API token (shown once, store it as this agent's secret): {token.token}")
