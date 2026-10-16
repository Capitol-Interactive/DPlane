/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import { AgentRoster } from "@/components/agents/agent-roster";
import { PageHead } from "@/components/core/page-title";
import { APP_SECTIONS } from "@/components/navigation/app-sections";
import { AppSectionPlaceholder } from "../_placeholder";

const section = APP_SECTIONS.find((item) => item.key === "agents")!;

export default function AgentsPage() {
  const { itemKey } = useParams();

  // the first nav item (and the bare /agents URL) is the roster; the other items are still placeholders
  if (!itemKey || itemKey === "ai-teammates") {
    return (
      <>
        <PageHead title={`Agents - ${section.label}`} />
        <AgentRoster />
      </>
    );
  }
  return <AppSectionPlaceholder section={section} />;
}
