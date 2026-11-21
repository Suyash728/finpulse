import { Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import type { Insight } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Rule-based insights computed in Python (/report.insights). */
export function InsightCards({ items }: { items: Insight[] }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">No insights yet.</p>;
  return (
    <ul className="space-y-2">
      {items.map((it, i) => {
        const up = (it.delta_pct ?? 0) > 0;
        const Trend = up ? TrendingUp : TrendingDown;
        return (
          <li key={i} className="flex gap-3 rounded-lg border p-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-muted">
              <Sparkles className="h-4 w-4 text-primary" />
            </span>
            <div className="min-w-0 space-y-1.5">
              <p className="text-sm">{it.text}</p>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {it.delta_pct !== null && (
                  <span className={cn("inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium",
                    it.tone === "bad" ? "bg-negative/10 text-negative" : "bg-positive/10 text-positive")}>
                    <Trend className="h-3 w-3" />{Math.abs(Math.round(it.delta_pct))}%
                  </span>
                )}
                {it.category && <span className="text-muted-foreground">{it.category}</span>}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
