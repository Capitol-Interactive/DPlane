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

// Sections a workspace admin can hide from the rail in Settings > Features. Work and Knowledge always stay on.
// Keep in sync with TOGGLEABLE_APP_SECTIONS in apps/api/plane/app/serializers/workspace.py.
export const TOGGLEABLE_APP_SECTION_KEYS: TAppSectionKey[] = ["agents", "strategy", "people", "clients"];

export const isAppSectionToggleable = (key: TAppSectionKey) => TOGGLEABLE_APP_SECTION_KEYS.includes(key);

/** Whether a section shows in the rail, given the workspace's `disabled_app_sections` */
export const isAppSectionEnabled = (key: TAppSectionKey, disabledSections: string[] | undefined) =>
  !isAppSectionToggleable(key) || !disabledSections?.includes(key);

export const getAppSectionFromPathname = (pathname: string, workspaceSlug: string | string[] | undefined) =>
  APP_SECTIONS.find((section) => pathname.includes(`/${workspaceSlug}/${section.key}`));
