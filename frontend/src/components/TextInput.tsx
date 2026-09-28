interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export default function TextInput({ value, onChange, disabled, maxLength = 20000 }: Props) {
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={maxLength}
        rows={10}
        placeholder="Paste or type clinical notes here — e.g. a visit summary, discharge note, or referral letter…"
        className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:bg-slate-50 disabled:opacity-60"
      />
      <div className="mt-1.5 flex justify-end">
        <span className="text-xs text-slate-400">
          {value.length.toLocaleString()} / {maxLength.toLocaleString()} characters
        </span>
      </div>
    </div>
  );
}
