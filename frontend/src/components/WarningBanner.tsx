import type { ReactNode } from "react";

interface Props {
  tone?: "warning" | "info" | "danger";
  title: string;
  children?: ReactNode;
}

const TONE_STYLES = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
  danger: "border-rose-200 bg-rose-50 text-rose-900",
};

export default function WarningBanner({ tone = "warning", title, children }: Props) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${TONE_STYLES[tone]}`} role="alert">
      <p className="font-semibold">{title}</p>
      {children && <div className="mt-1 text-[13px] leading-relaxed opacity-90">{children}</div>}
    </div>
  );
}
