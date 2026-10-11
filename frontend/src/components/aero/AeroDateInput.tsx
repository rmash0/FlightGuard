import type { ComponentPropsWithRef } from "react";

import { cx } from "./classes";
import "./AeroInput.css";
import "./AeroDateInput.css";

type AeroDateInputProps = Omit<ComponentPropsWithRef<"input">, "type">;

function AeroDateInput({ className, ...props }: AeroDateInputProps) {
  return (
    <span
      className={cx("aero-input", "aero-date-input", className)}
      data-invalid={props["aria-invalid"]}
    >
      <input className="aero-date-input__native" type="date" {...props} />
    </span>
  );
}

export default AeroDateInput;
