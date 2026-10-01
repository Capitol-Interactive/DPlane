/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import {
  AiStar1Outline,
  AnalyticsOutline,
  CalendarOutline,
  ClipboardOutline,
  DashboardsOutline,
  GridOutline,
  GroupOutline,
  IntakeOutline,
  MembersOutline,
  PagesOutline,
  ProjectsOutline,
  RefreshOutline,
  RocketOutline,
  UsageOutline,
  UserAltOutline,
  UserOutline,
} from "@makeplane/propel/icons";

type TRailIcon = ComponentType<{ className?: string }>;

export type TRailSectionKey = "agents" | "strategy" | "knowledge" | "people" | "clients";

export type TRailNavItem = {
  key: string;
  label: string;
  icon: TRailIcon;
  /** Empty-state copy shown on the item's page until the feature ships */
  emptyTitle: string;
  emptyDescription: string;
};

export type TRailNavGroup = {
  key: string;
  /** Optional heading rendered above the group's items */
  title?: string;
  items: TRailNavItem[];
  /** Shown under the heading when the group has no items (e.g. no teams yet) */
  emptyLabel?: string;
};

export type TRailSection = {
  key: TRailSectionKey;
  /** Label shown under the icon in the app rail */
  label: string;
  /** Title at the top of the secondary sidebar */
  sidebarTitle: string;
  icon: TRailIcon;
  groups: TRailNavGroup[];
  /** Copy for the "Recent" block at the bottom of the secondary sidebar */
  recentEmptyLabel?: string;
};

export const RAIL_SECTIONS: TRailSection[] = [
  {
    key: "agents",
    label: "Agents",
    sidebarTitle: "Agents",
    icon: AiStar1Outline,
    recentEmptyLabel: "Deploy AI Teammates and workflows",
    groups: [
      {
        key: "agents",
        items: [
          {
            key: "ai-teammates",
            label: "AI Teammates",
            icon: AiStar1Outline,
            emptyTitle: "Unlock AI Teammates for your organization",
            emptyDescription: "Help your team work smarter with AI teammates that support every project.",
          },
        ],
      },
      {
        key: "workflow",
        title: "Workflow",
        items: [
          {
            key: "automations",
            label: "Automations",
            icon: RefreshOutline,
            emptyTitle: "Automate repetitive work",
            emptyDescription: "Create rules that assign, update and route work for you.",
          },
          {
            key: "project-templates",
            label: "Project templates",
            icon: ClipboardOutline,
            emptyTitle: "Start projects faster with templates",
            emptyDescription: "Save a project's structure and reuse it for the next one.",
          },
          {
            key: "forms",
            label: "Forms",
            icon: IntakeOutline,
            emptyTitle: "Collect requests with forms",
            emptyDescription: "Turn submissions into work items that land in the right project.",
          },
          {
            key: "custom-fields",
            label: "Custom fields",
            icon: GridOutline,
            emptyTitle: "Track what matters with custom fields",
            emptyDescription: "Add your own properties to work items and reuse them across projects.",
          },
        ],
      },
    ],
  },
  {
    key: "strategy",
    label: "Strategy",
    sidebarTitle: "Strategy",
    icon: RocketOutline,
    recentEmptyLabel: "Align and measure your work with goals",
    groups: [
      {
        key: "strategy",
        items: [
          {
            key: "goals",
            label: "Goals",
            icon: RocketOutline,
            emptyTitle: "Track progress on key initiatives",
            emptyDescription:
              "Set goals for your company, your team, or yourself. Connect each goal to the work that supports it so you can track progress automatically.",
          },
          {
            key: "reporting",
            label: "Reporting",
            icon: DashboardsOutline,
            emptyTitle: "See how work is going",
            emptyDescription: "Build dashboards that roll progress up across projects and teams.",
          },
          {
            key: "resourcing",
            label: "Resourcing",
            icon: AnalyticsOutline,
            emptyTitle: "Plan your team's capacity",
            emptyDescription: "See who is working on what so you can staff projects with confidence.",
          },
        ],
      },
    ],
  },
  {
    key: "knowledge",
    label: "Knowledge",
    sidebarTitle: "Knowledge",
    icon: PagesOutline,
    recentEmptyLabel: "Write it down, keep it connected, and turn ideas into action",
    groups: [
      {
        key: "knowledge",
        items: [
          {
            key: "pages",
            label: "Pages",
            icon: PagesOutline,
            emptyTitle: "Keep notes, docs, and plans connected to work with pages",
            emptyDescription: "Collaborate with your team to turn ideas into action all in one tool.",
          },
          {
            key: "meetings",
            label: "Meetings",
            icon: CalendarOutline,
            emptyTitle: "Capture notes and action items from every call",
            emptyDescription: "Meeting notes and follow-ups will show up here, connected to your work.",
          },
        ],
      },
    ],
  },
  {
    key: "people",
    label: "People",
    sidebarTitle: "People",
    icon: UserOutline,
    groups: [
      {
        key: "people",
        items: [
          {
            key: "profile",
            label: "Profile",
            icon: UserOutline,
            emptyTitle: "Your profile",
            emptyDescription: "Your tasks, projects and goals will show up here.",
          },
          {
            key: "teams",
            label: "Teams",
            icon: MembersOutline,
            emptyTitle: "Bring your teams together",
            emptyDescription: "Create teams to organize people and share projects.",
          },
        ],
      },
      { key: "teams-list", title: "Teams", items: [], emptyLabel: "No teams yet" },
    ],
  },
  {
    key: "clients",
    label: "Clients",
    sidebarTitle: "Client management",
    icon: GroupOutline,
    recentEmptyLabel: "Clients you open will show up here",
    groups: [
      {
        key: "clients",
        items: [
          {
            key: "clients",
            label: "Clients",
            icon: GroupOutline,
            emptyTitle: "Manage client work and relationships",
            emptyDescription: "Track client health and relationship data right where the work happens.",
          },
          {
            key: "contacts",
            label: "Contacts",
            icon: UserAltOutline,
            emptyTitle: "Keep your client contacts in one place",
            emptyDescription: "Add the people you work with at each client.",
          },
          {
            key: "projects",
            label: "Projects",
            icon: ProjectsOutline,
            emptyTitle: "See projects by client",
            emptyDescription: "Link projects to clients to follow every engagement.",
          },
          {
            key: "team-capacity",
            label: "Team capacity",
            icon: UsageOutline,
            emptyTitle: "Staff client work with confidence",
            emptyDescription: "Track your team's capacity across every client project.",
          },
          {
            key: "meetings",
            label: "Meetings",
            icon: CalendarOutline,
            emptyTitle: "Get notes and action items from every call",
            emptyDescription: "Client meeting notes will show up here automatically.",
          },
        ],
      },
    ],
  },
];

export const getRailSection = (key: string | undefined) => RAIL_SECTIONS.find((section) => section.key === key);

export const getRailSectionItems = (section: TRailSection) => section.groups.flatMap((group) => group.items);

/** Path (after the workspace slug) of a rail item, e.g. "agents/automations" */
export const getRailItemPath = (section: TRailSection, item: TRailNavItem) => `${section.key}/${item.key}`;

/** Where clicking a section in the app rail lands */
export const getRailSectionHref = (workspaceSlug: string, section: TRailSection) => {
  const [firstItem] = getRailSectionItems(section);
  return `/${workspaceSlug}/${firstItem ? getRailItemPath(section, firstItem) : section.key}`;
};
