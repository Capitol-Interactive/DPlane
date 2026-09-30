/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TAppSectionKey = "agents" | "strategy" | "knowledge" | "people" | "clients";

export type TAppSection = {
  key: TAppSectionKey;
  label: string;
  description: string;
};

// Rail sections that live outside the projects app. Each one is served by the (sections) route group.
export const APP_SECTIONS: TAppSection[] = [
  { key: "agents", label: "Agents", description: "Automations and AI agents that work alongside your team." },
  { key: "strategy", label: "Strategy", description: "Goals, roadmaps and the plans that tie your work together." },
  { key: "knowledge", label: "Knowledge", description: "Docs, playbooks and everything your team needs to know." },
  { key: "people", label: "People", description: "Teammates, roles and who is working on what." },
  { key: "clients", label: "Clients", description: "Client accounts, contacts and the work delivered for them." },
];

export const getAppSectionFromPathname = (pathname: string, workspaceSlug: string | string[] | undefined) =>
  APP_SECTIONS.find((section) => pathname.includes(`/${workspaceSlug}/${section.key}`));
