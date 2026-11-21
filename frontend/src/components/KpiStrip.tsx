import type { Report } from "@/lib/api";
import { fmtMonth, inr, pct } from "@/lib/format";
import { StatTile } from "@/components/placeholder";

/** Month KPIs straight from GET /report/{month}. No arithmetic here. */
export function KpiStrip({ report }: { report: Report | null }) {
  const over = report?.by_category.filter((c) => c.budget != null && c.amount > c.budget).length ?? 0;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label={report ? `Income · ${fmtMonth(report.month)}` : "Income"} value={report ? inr(report.income) : undefined} />
      <StatTile
        label="Spent"
        value={report ? inr(report.spend) : undefined}
        delta={report ? (over ? `${over} categor${over === 1 ? "y" : "ies"} over budget` : "All within budget") : undefined}
      />
      <StatTile label="Saved" value={report ? inr(report.savings) : undefined} />
      <StatTile label="Savings rate" value={report ? pct(report.savings_rate) : undefined} />
    </div>
  );
}
