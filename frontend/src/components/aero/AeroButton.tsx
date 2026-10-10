import type { ComponentPropsWithoutRef } from "react";

import {
  aeroButtonClass,
  type AeroButtonSize,
  type AeroButtonVariant,
} from "./classes";

type AeroButtonProps = ComponentPropsWithoutRef<"button"> & {
  variant?: AeroButtonVariant;
  size?: AeroButtonSize;
};

// Glossy gel button. For links styled as buttons, use aeroButtonClass() from ./classes.
function AeroButton({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...props
}: AeroButtonProps) {
  return (
    <button
      type={type}
      className={aeroButtonClass(variant, size, className)}
      {...props}
    />
  );
}

export default AeroButton;
