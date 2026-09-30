/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { APP_SECTIONS } from "@/components/navigation/app-sections";
import { AppSectionPlaceholder } from "../_placeholder";

const section = APP_SECTIONS.find((item) => item.key === "people")!;

export default function PeoplePage() {
  return <AppSectionPlaceholder section={section} />;
}
