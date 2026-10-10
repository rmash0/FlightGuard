import type { ComponentPropsWithRef } from "react";

import "./AeroInput.css";
import { cx } from "./classes";

type AeroInputProps = ComponentPropsWithRef<"input">;

// Glassy text/date input. Set aria-invalid to show the error style.
function AeroInput({ className, ...props }: AeroInputProps) {
  return <input className={cx("aero-input", className)} {...props} />;
}

export default AeroInput;
