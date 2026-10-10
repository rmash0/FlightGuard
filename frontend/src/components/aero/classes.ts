// Class helpers for applying Aero styles to elements that aren't our components
// (e.g. <Link className={aeroButtonClass()}>). Kept out of component files for fast refresh.

// Load button styles with the helper so links styled as buttons work without <AeroButton>.
import "./AeroButton.css";

export type AeroButtonVariant = "primary" | "eco" | "glass";
export type AeroButtonSize = "md" | "lg";

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function aeroButtonClass(
  variant: AeroButtonVariant = "primary",
  size: AeroButtonSize = "md",
  className?: string,
): string {
  return cx(
    "aero-button",
    `aero-button--${variant}`,
    size === "lg" && "aero-button--lg",
    className,
  );
}
