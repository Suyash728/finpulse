import type { Report } from "@/lib/api";
import { iconFor } from "@/lib/category-meta";
import { inr } from "@/lib/format";

function Ring({ ratio, tone }: { ratio: number; tone: string }) {
  const r = 26, c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 64 64" className="h-14 w-14 -rotate-90 md:h-16 md:w-16" aria-hidden>
      <circle cx="32" cy="32" r={r} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
      <circle cx="32" cy="32" r={r} fill="none" stroke={tone} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={`${Math.min(1, ratio) * c} ${c}`} />
    </svg>
  );
}

/** Monthly budget rings: spent / budget per category (amounts from /report; ring = visual ratio only). */
export function BudgetRings({ report }: { report: Report }) {
  const rows = report.by_category.filter((c) => c.budget).sort((a, b) => b.amount / b.budget! - a.amount / a.budget!).slice(0, 8);
  if (!rows.length) return <p className="text-sm text-muted-foreground">Set budgets in Plan to see them here.</p>;
  return (
    <ul className="grid grid-cols-4 gap-x-2 gap-y-4">
      {rows.map((c) => {
        const ratio = c.amount / c.budget!;
        const tone = ratio > 1 ? "hsl(var(--negative))" : ratio > 0.8 ? "hsl(var(--warning))" : "hsl(var(--positive))";
        const Icon = iconFor(c.category);
        return (
          <li key={c.category} className="flex flex-col items-center text-center">
            <div className="relative">
              <Ring ratio={ratio} tone={tone} />
              <Icon className="absolute left-1/2 top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2" style={{ color: tone }} />
            </div>
            <p className="mt-1 w-full truncate text-xs font-medium">{c.category}</p>
            <p className="text-[11px] tabular-nums text-muted-foreground">
              <span className={ratio > 1 ? "text-negative" : undefined}>{inr(c.amount)}</span>
              <span className="hidden sm:inline"> / {inr(c.budget!)}</span>
            </p>
          </li>
        );
      })}
    </ul>
  );
}
