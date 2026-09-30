/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronRightOutline } from "@makeplane/propel/icons";
import { cn } from "@plane/utils";

type TWikiTreeRowProps = {
  depth: number;
  label: string;
  icon: ReactNode;
  href?: string;
  onClick?: () => void;
  isActive?: boolean;
  isExpandable?: boolean;
  isOpen?: boolean;
  onToggle?: () => void;
  // rendered at the end of the row, revealed on hover
  actions?: ReactNode;
};

const ROW_INDENT = 16;

/**
 * One row of the wiki sidebar tree: expand chevron, icon, label and hover actions.
 */
export function WikiTreeRow(props: TWikiTreeRowProps) {
  const { depth, label, icon, href, onClick, isActive = false, isExpandable = false, isOpen = false, onToggle } = props;

  const content = (
    <>
      <span className="grid size-4 flex-shrink-0 place-items-center">{icon}</span>
      <span className="truncate">{label}</span>
    </>
  );
  const contentClassName = "flex min-w-0 flex-1 items-center gap-2 py-1.5 text-left";

  return (
    <div
      className={cn(
        "group/wiki-row flex items-center gap-0.5 rounded-md pr-1 text-13 font-medium text-secondary hover:bg-layer-transparent-hover",
        { "bg-layer-transparent-selected text-primary": isActive }
      )}
      style={{ paddingLeft: 4 + depth * ROW_INDENT }}
    >
      {isExpandable ? (
        <button
          type="button"
          onClick={onToggle}
          aria-label={isOpen ? "Collapse" : "Expand"}
          aria-expanded={isOpen}
          className="grid size-5 flex-shrink-0 place-items-center rounded-sm text-icon-tertiary hover:bg-layer-transparent-active"
        >
          <ChevronRightOutline className={cn("size-3.5 transition-transform", { "rotate-90": isOpen })} />
        </button>
      ) : (
        <span className="size-5 flex-shrink-0" />
      )}
      {href ? (
        <Link href={href} className={contentClassName}>
          {content}
        </Link>
      ) : (
        <button type="button" onClick={onClick ?? onToggle} className={contentClassName}>
          {content}
        </button>
      )}
      {props.actions && (
        <div className="flex flex-shrink-0 items-center opacity-0 group-focus-within/wiki-row:opacity-100 group-hover/wiki-row:opacity-100">
          {props.actions}
        </div>
      )}
    </div>
  );
}
