import { SORT_OPTIONS } from "@/lib/explorer";

export function SortSelect({ value, onChange }: { value: string; onChange: (tri: string) => void }) {
  const known = SORT_OPTIONS.some((option) => option.value === value);
  return (
    <label className="sort">
      Trier par
      <select className="field" value={value} onChange={(e) => onChange(e.target.value)}>
        {!known && <option value={value}>Tri de l&apos;assistant ({value})</option>}
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
