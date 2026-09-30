/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { Collapsible } from "@makeplane/propel/components/collapsible";
// hooks
import useLocalStorage from "@/hooks/use-local-storage";

type TWikiSidebarSectionProps = {
  title: string;
  // localStorage key remembering whether the section is expanded
  storageKey: string;
  // rendered next to the title, revealed on hover
  trailing?: ReactNode;
  children: ReactNode;
};

export function WikiSidebarSection(props: TWikiSidebarSectionProps) {
  const { title, storageKey, trailing, children } = props;
  // local storage
  const { storedValue, setValue } = useLocalStorage<boolean>(storageKey, true);
  const isOpen = storedValue ?? true;

  return (
    <Collapsible
      // the group marker lives on the root: CollapsibleHeader takes no className
      render={<div className="group/wiki-section" />}
      placement="sidebar"
      open={isOpen}
      onOpenChange={() => setValue(!isOpen)}
      trigger={<span className="text-13 font-semibold whitespace-nowrap text-placeholder">{title}</span>}
      trailing={
        trailing ? (
          <span className="pointer-events-none flex items-center opacity-0 group-hover/wiki-section:pointer-events-auto group-hover/wiki-section:opacity-100">
            {trailing}
          </span>
        ) : undefined
      }
    >
      <div className="mt-0.5 flex flex-col gap-0.5">{children}</div>
    </Collapsible>
  );
}
