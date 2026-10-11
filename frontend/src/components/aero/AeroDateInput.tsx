import type { ComponentPropsWithRef } from "react";

import { cx } from "./classes";
import "./AeroInput.css";
import "./AeroDateInput.css";

type AeroDateInputProps = Omit<ComponentPropsWithRef<"input">, "type" | "value"> & {
  value: string;
};

function formatDate(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Select date";

  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function AeroDateInput({ className, value, onClick, ...props }: AeroDateInputProps) {
  return (
    <span
      className={cx("aero-input", "aero-date-input", className)}
      data-invalid={props["aria-invalid"]}
    >
      <span className="aero-date-input__display" aria-hidden="true">
        {formatDate(value)}
      </span>
      <input
        className="aero-date-input__native"
        type="date"
        value={value}
        onClick={(event) => {
          onClick?.(event);
          if (!event.defaultPrevented) {
            try {
              event.currentTarget.showPicker();
            } catch {
              // The input still opens its native picker in browsers without showPicker.
            }
          }
        }}
        {...props}
      />
    </span>
  );
}

export default AeroDateInput;
