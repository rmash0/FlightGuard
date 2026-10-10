import type { ReactNode } from "react";

import "./AeroBadge.css";
import { cx } from "./classes";

export type AeroBadgeTone = "sky" | "aqua" | "leaf" | "amber" | "coral" | "muted";

type AeroBadgeProps = {
  tone: AeroBadgeTone;
  children: ReactNode;
  className?: string;
};

// Small glossy status pill (flight status, delay risk, eco score...).
function AeroBadge({ tone, children, className }: AeroBadgeProps) {
  return (
    <span className={cx("aero-badge", `aero-badge--${tone}`, className)}>
      {children}
    </span>
  );
}

export default AeroBadge;
