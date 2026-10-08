/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import {
  AgentOutline,
  AnalyticsOutline,
  CalendarOutline,
  ClipboardOutline,
  CustomersOutline,
  DashboardsOutline,
  GridOutline,
  InitiativeOutline,
  IntakeOutline,
  MembersOutline,
  ProjectsOutline,
  RefreshOutline,
  UsageOutline,
  UserAltOutline,
  UserOutline,
} from "@makeplane/propel/icons";
import type { TAppSectionKey } from "./app-sections";

type TSectionNavIcon = ComponentType<{ className?: string }>;

export type TSectionNavItem = {
  key: string;
  label: string;
  icon: TSectionNavIcon;
  /** Copy for the item's page until the feature is built */
  title: string;
  description: string;
};

export type TSectionNavGroup = {
  key: string;
  /** Optional heading above the group's items */
  title?: string;
  items: TSectionNavItem[];
  /** Shown under the heading when the group has no items */
  emptyLabel?: string;
};

export type TSectionNav = {
  /** Title at the top of the section's sidebar panel */
  title: string;
  groups: TSectionNavGroup[];
  /** Copy for the "Recent" block at the bottom of the panel */
  recentEmptyLabel?: string;
};

// Sidebar navigation for the placeholder sections, modelled on Asana's rail panels.
// Knowledge is not here: it has its own panel (the wiki).
export const SECTION_NAV: Partial<Record<TAppSectionKey, TSectionNav>> = {
  agents: {
    title: "Agents",
    recentEmptyLabel: "Deploy AI Teammates and workflows",
    groups: [
      {
        key: "agents",
        items: [
          {
            key: "ai-teammates",
            label: "AI Teammates",
            icon: AgentOutline,
            title: "Unlock AI Teammates for your organization",
            description: "Help your team work smarter with AI teammates that support every project.",
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
            title: "Automate repetitive work",
            description: "Create rules that assign, update and route work for you.",
          },
          {
            key: "project-templates",
            label: "Project templates",
            icon: ClipboardOutline,
            title: "Start projects faster with templates",
            description: "Save a project's structure and reuse it for the next one.",
          },
          {
            key: "forms",
            label: "Forms",
            icon: IntakeOutline,
            title: "Collect requests with forms",
            description: "Turn submissions into work items that land in the right project.",
          },
          {
            key: "custom-fields",
            label: "Custom fields",
            icon: GridOutline,
            title: "Track what matters with custom fields",
            description: "Add your own properties to work items and reuse them across projects.",
          },
        ],
      },
    ],
  },
  strategy: {
    title: "Strategy",
    recentEmptyLabel: "Align and measure your work with goals",
    groups: [
      {
        key: "strategy",
        items: [
          {
            key: "goals",
            label: "Goals",
            icon: InitiativeOutline,
            title: "Track progress on key initiatives",
            description:
              "Set goals for your company, your team, or yourself. Connect each goal to the work that supports it so you can track progress automatically.",
          },
          {
            key: "reporting",
            label: "Reporting",
            icon: DashboardsOutline,
            title: "See how work is going",
            description: "Build dashboards that roll progress up across projects and teams.",
          },
          {
            key: "resourcing",
            label: "Resourcing",
            icon: AnalyticsOutline,
            title: "Plan your team's capacity",
            description: "See who is working on what so you can staff projects with confidence.",
          },
        ],
      },
    ],
  },
  people: {
    title: "People",
    groups: [
      {
        key: "people",
        items: [
          {
            key: "profile",
            label: "Profile",
            icon: UserOutline,
            title: "Your profile",
            description: "Your tasks, projects and goals will show up here.",
          },
          {
            key: "teams",
            label: "Teams",
            icon: MembersOutline,
            title: "Bring your teams together",
            description: "Create teams to organize people and share projects.",
          },
        ],
      },
      { key: "teams-list", title: "Teams", items: [], emptyLabel: "No teams yet" },
    ],
  },
  clients: {
    title: "Client management",
    recentEmptyLabel: "Clients you open will show up here",
    groups: [
      {
        key: "clients",
        items: [
          {
            key: "clients",
            label: "Clients",
            icon: CustomersOutline,
            title: "Manage client work and relationships",
            description: "Track client health and relationship data right where the work happens.",
          },
          {
            key: "contacts",
            label: "Contacts",
            icon: UserAltOutline,
            title: "Keep your client contacts in one place",
            description: "Add the people you work with at each client.",
          },
          {
            key: "projects",
            label: "Projects",
            icon: ProjectsOutline,
            title: "See projects by client",
            description: "Link projects to clients to follow every engagement.",
          },
          {
            key: "team-capacity",
            label: "Team capacity",
            icon: UsageOutline,
            title: "Staff client work with confidence",
            description: "Track your team's capacity across every client project.",
          },
          {
            key: "meetings",
            label: "Meetings",
            icon: CalendarOutline,
            title: "Get notes and action items from every call",
            description: "Client meeting notes will show up here automatically.",
          },
        ],
      },
    ],
  },
};

/** The selected nav item; an unknown or missing key falls back to the section's first item */
export const getSectionNavItem = (nav: TSectionNav | undefined, itemKey: string | undefined) => {
  const items = nav?.groups.flatMap((group) => group.items) ?? [];
  return items.find((item) => item.key === itemKey) ?? items[0];
};
