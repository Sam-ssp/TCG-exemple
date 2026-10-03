import type { LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  icon: LucideIcon;
  tone?: "plain" | "solid" | "danger";
};

// A round icon-only button; the label is its accessible name and its tooltip.
export function IconButton({ label, icon: Icon, tone = "plain", className = "", type = "button", ...props }: Props) {
  return (
    <button type={type} className={`icon-button ${tone} ${className}`} aria-label={label} data-tip={label} {...props}>
      <Icon />
    </button>
  );
}
