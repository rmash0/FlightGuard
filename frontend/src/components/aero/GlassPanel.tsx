import type { ComponentPropsWithoutRef } from "react";

import "./GlassPanel.css";
import { cx } from "./classes";

type GlassPanelTag = "div" | "section" | "article" | "aside" | "header" | "footer";

type GlassPanelProps = ComponentPropsWithoutRef<"div"> & {
  as?: GlassPanelTag;
};

// Frosted glass card. The base for every panel/card in the app.
function GlassPanel({ as: Tag = "div", className, ...props }: GlassPanelProps) {
  return <Tag className={cx("glass-panel", className)} {...props} />;
}

export default GlassPanel;
