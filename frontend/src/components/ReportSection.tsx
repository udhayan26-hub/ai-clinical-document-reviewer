import type { ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  count?: number;
  children: ReactNode;
}

export default function ReportSection({ title, subtitle, count, children }: Props) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-baseline justify-between border-b border-slate-100 px-5 py-3.5">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        {typeof count === "number" && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">{count}</span>
        )}
      </div>
      {subtitle && <p className="border-b border-slate-100 px-5 py-2 text-xs text-slate-500">{subtitle}</p>}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}
