import type { Report } from "@/lib/api";
import { inrCompact } from "@/lib/category-meta";
import { fmtMonth } from "@/lib/format";

/** Month calendar; each day shaded by its spend (daily totals from /report). */
export function SpendCalendar({ report }: { report: Report }) {
  const days = report.daily ?? [];
  if (!days.length) return null;
  const max = Math.max(1, ...days.map((d) => d.amount));
  const lead = new Date(`${report.month}-01T00:00:00`).getDay();
  const asOf = report.projection?.as_of_day ?? days.length;
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{fmtMonth(report.month)} · darker = more spent</p>
      <div className="grid grid-cols-7 gap-1 text-center text-[10px]">
        {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <div key={i} className="pb-1 text-muted-foreground">{d}</div>)}
        {Array.from({ length: lead }).map((_, i) => <div key={`b${i}`} />)}
        {days.map((d, i) => {
          const level = d.amount / max;
          const future = i + 1 > asOf;
          return (
            <div key={d.date} title={`${d.date}: ₹${d.amount.toLocaleString("en-IN")}`}
              className={`flex aspect-square flex-col items-center justify-center rounded-md ${future ? "text-muted-foreground/50" : ""} ${i + 1 === asOf ? "ring-1 ring-foreground" : ""}`}
              style={{ background: !future && d.amount > 0 ? `hsl(var(--chart-1) / ${0.12 + level * 0.78})` : "hsl(var(--muted) / 0.5)",
                color: level > 0.55 ? "hsl(var(--primary-foreground))" : undefined }}>
              <span className="font-medium">{i + 1}</span>
              {!future && d.amount > 0 && <span className="hidden tabular-nums opacity-90 sm:block">{inrCompact(d.amount)}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
