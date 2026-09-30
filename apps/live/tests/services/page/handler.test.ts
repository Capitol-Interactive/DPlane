/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, it, expect, vi } from "vitest";
import { getPageService } from "@/services/page/handler";
import { ProjectPageService } from "@/services/page/project-page.service";
import { WorkspacePageService } from "@/services/page/workspace-page.service";
import type { HocusPocusServerContext } from "@/types";

// The services read env at import time; the handler test only needs a valid base URL.
vi.mock("@/env", () => ({ env: { API_BASE_URL: "http://api.test" } }));

const buildContext = (overrides: Partial<HocusPocusServerContext> = {}): HocusPocusServerContext => ({
  projectId: null,
  cookie: "session=abc",
  documentType: "workspace_page",
  workspaceSlug: "acme",
  userId: "user-1",
  ...overrides,
});

const basePathOf = (service: unknown) => (service as { basePath: string }).basePath;

describe("getPageService", () => {
  it("resolves workspace pages to the wiki API without a project", () => {
    const service = getPageService("workspace_page", buildContext());

    expect(service).toBeInstanceOf(WorkspacePageService);
    expect(basePathOf(service)).toBe("/api/workspaces/acme/wiki");
  });

  it("keeps resolving project pages to the project API", () => {
    const service = getPageService("project_page", buildContext({ projectId: "p1", documentType: "project_page" }));

    expect(service).toBeInstanceOf(ProjectPageService);
    expect(basePathOf(service)).toBe("/api/workspaces/acme/projects/p1");
  });

  it("requires a workspace slug and a cookie for workspace pages", () => {
    expect(() => getPageService("workspace_page", buildContext({ workspaceSlug: null }))).toThrow();
    expect(() => getPageService("workspace_page", buildContext({ cookie: "" }))).toThrow();
  });

  it("rejects unknown document types", () => {
    // @ts-expect-error - deliberately invalid document type
    expect(() => getPageService("team_page", buildContext())).toThrow(/Invalid document type/);
  });
});
