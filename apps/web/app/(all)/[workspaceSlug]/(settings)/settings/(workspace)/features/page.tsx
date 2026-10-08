/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Switch } from "@makeplane/propel/components/switch";
import { setToast } from "@plane/blocks/toast";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import {
  APP_SECTIONS,
  isAppSectionToggleable,
  TOGGLEABLE_APP_SECTION_KEYS,
} from "@/components/navigation/app-sections";
import type { TAppSectionKey } from "@/components/navigation/app-sections";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsControlItem } from "@/components/settings/control-item";
import { SettingsHeading } from "@/components/settings/heading";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { FeaturesWorkspaceSettingsHeader } from "./header";

// Work is the projects app; it is not in APP_SECTIONS but is listed so admins see it is always on
const WORK_SECTION = { label: "Work", description: "Projects, work items, cycles, modules and views." };

function FeaturesSettingsPage() {
  const { workspaceSlug } = useParams();
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentWorkspace, updateWorkspace } = useWorkspace();
  const { t } = useTranslation();
  // states
  const [updatingKey, setUpdatingKey] = useState<TAppSectionKey | null>(null);
  // derived values
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const disabledSections = currentWorkspace?.disabled_app_sections ?? [];
  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.features.title")}`
    : undefined;

  const handleToggle = async (key: TAppSectionKey, enabled: boolean) => {
    if (!workspaceSlug) return;
    // keep the stored list in rail order, matching what the API saves
    const nextDisabled = TOGGLEABLE_APP_SECTION_KEYS.filter((sectionKey) =>
      sectionKey === key ? !enabled : disabledSections.includes(sectionKey)
    );
    setUpdatingKey(key);
    try {
      await updateWorkspace(workspaceSlug.toString(), { disabled_app_sections: nextDisabled });
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("workspace_settings.settings.features.updated"),
      });
    } catch (error) {
      console.error("Failed to update workspace features", error);
      setToast({
        type: "error",
        title: t("common.errors.default.title"),
        message: t("common.errors.default.message"),
      });
    } finally {
      setUpdatingKey(null);
    }
  };

  // if user is not authorized to view this page
  if (workspaceUserInfo && !isAdmin) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  const alwaysOn = (
    <span className="text-caption-md-regular text-tertiary">{t("workspace_settings.settings.features.always_on")}</span>
  );

  return (
    <SettingsContentWrapper header={<FeaturesWorkspaceSettingsHeader />} hugging>
      <PageHead title={pageTitle} />
      <div className="flex w-full flex-col gap-y-6">
        <SettingsHeading
          title={t("workspace_settings.settings.features.title")}
          description={t("workspace_settings.settings.features.description")}
        />
        <div className="flex flex-col divide-y divide-subtle">
          <SettingsControlItem title={WORK_SECTION.label} description={WORK_SECTION.description} control={alwaysOn} />
          {APP_SECTIONS.map((section) => {
            if (!isAppSectionToggleable(section.key)) {
              return (
                <SettingsControlItem
                  key={section.key}
                  title={section.label}
                  description={section.description}
                  control={alwaysOn}
                />
              );
            }
            const isEnabled = !disabledSections.includes(section.key);
            return (
              <SettingsControlItem
                key={section.key}
                title={section.label}
                description={section.description}
                control={
                  <Switch
                    size="sm"
                    checked={isEnabled}
                    onCheckedChange={(checked) => void handleToggle(section.key, checked)}
                    disabled={updatingKey !== null}
                    aria-label={section.label}
                  />
                }
              />
            );
          })}
        </div>
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(FeaturesSettingsPage);
