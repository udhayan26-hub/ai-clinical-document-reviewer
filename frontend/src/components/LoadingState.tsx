export default function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-6 py-14 text-center">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-sky-600" aria-hidden="true" />
      <p className="text-sm text-slate-500">{label}</p>
    </div>
  );
}
