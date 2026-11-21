import { ESSENTIAL, type Report } from "@/lib/api";
import { inr } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Top 6 categories as horizontal bars (widths are visual scaling only). */
export function CategoryBars({ rows }: { rows: Report["by_category"] }) {
  const top = [...rows].sort((a, b) => b.amount - a.amount).slice(0, 6);
  const max = Math.max(1, ...top.map((r) => Math.max(r.amount, r.budget ?? 0)));
  if (top.length === 0) return <p className="text-sm text-muted-foreground">No spending yet.</p>;
  return (
    <ul className="space-y-2.5">
      {top.map((r) => {
        const over = r.budget != null && r.amount > r.budget;
        return (
          <li key={r.category} className="space-y-1">
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span className="truncate">
                {r.category}
                {ESSENTIAL.has(r.category) && <span className="ml-1.5 text-xs text-muted-foreground">essential</span>}
              </span>
              <span className="whitespace-nowrap tabular-nums">
                <span className={cn("font-medium", over && "text-negative")}>{inr(r.amount)}</span>
                {r.budget != null && <span className="text-xs text-muted-foreground"> / {inr(r.budget)}</span>}
              </span>
            </div>
            <div className="relative h-2 rounded-full bg-muted">
              <div
                className={cn("h-2 rounded-full", over ? "bg-negative" : "bg-chart-1")}
                style={{ width: `${(r.amount / max) * 100}%` }}
              />
              {r.budget != null && (
                <div className="absolute -top-0.5 h-3 w-0.5 bg-foreground/60" style={{ left: `${(r.budget / max) * 100}%` }} />
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
