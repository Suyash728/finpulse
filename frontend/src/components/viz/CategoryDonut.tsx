"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { Report } from "@/lib/api";
import { CHART_COLORS } from "@/lib/category-meta";
import { inr } from "@/lib/format";

/** Spending by category (values from /report; no sums in the browser). */
export function CategoryDonut({ report }: { report: Report }) {
  const data = [...report.by_category].sort((a, b) => b.amount - a.amount).map((c) => ({ name: c.category, value: c.amount }));
  if (!data.length) return <p className="text-sm text-muted-foreground">No spending yet.</p>;
  const legend = data.slice(0, 8);
  return (
    <div className="space-y-3">
      <div className="relative mx-auto h-48 w-48">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="100%" paddingAngle={2}
              stroke="hsl(var(--card))" strokeWidth={2} isAnimationActive={false}>
              {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={(v: number) => inr(v)}
              contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="text-lg font-semibold tabular-nums">{inr(report.spend)}</p>
            <p className="text-xs text-muted-foreground">total spent</p>
          </div>
        </div>
      </div>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        {legend.map((d, i) => (
          <li key={d.name} className="flex items-center justify-between gap-2">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
              <span className="truncate text-muted-foreground">{d.name}</span>
            </span>
            <span className="font-medium tabular-nums">{inr(d.value)}</span>
          </li>
        ))}
      </ul>
      {data.length > legend.length && (
        <p className="text-center text-xs text-muted-foreground">+{data.length - legend.length} smaller categories in the chart</p>
      )}
    </div>
  );
}
