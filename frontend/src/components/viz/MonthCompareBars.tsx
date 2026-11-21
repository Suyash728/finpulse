"use client";

import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Report } from "@/lib/api";
import { inrCompact } from "@/lib/category-meta";
import { fmtMonth, inr } from "@/lib/format";

/** This month vs last month per category; % labels are change_pct from /report. */
export function MonthCompareBars({ report }: { report: Report }) {
  const data = [...report.by_category].filter((c) => c.category !== "Other")
    .sort((a, b) => b.amount - a.amount).slice(0, 7)
    .map((c) => ({ name: c.category, now: c.amount, prev: c.prev_amount ?? 0, pct: c.change_pct }));
  const label = (v: unknown) => {
    const n = typeof v === "number" ? v : null;
    return n === null ? "" : `${n > 0 ? "+" : ""}${Math.round(n)}%`;
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-chart-1" />{fmtMonth(report.month)} <b className="tabular-nums">{inr(report.spend)}</b></span>
        {report.prev_month && (
          <span className="flex items-center gap-1.5 text-muted-foreground"><span className="h-2 w-2 rounded-full bg-muted-foreground/40" />{fmtMonth(report.prev_month)} <b className="tabular-nums">{inr(report.prev_spend ?? 0)}</b></span>
        )}
      </div>
      <div className="h-56 w-full">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 18, right: 4, left: 0, bottom: 0 }} barGap={2}>
            <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
            <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={10} interval={0} stroke="hsl(var(--muted-foreground))"
              tickFormatter={(v: string) => (v.length > 8 ? `${v.slice(0, 7)}…` : v)} />
            <YAxis tickLine={false} axisLine={false} fontSize={10} tickFormatter={inrCompact} width={48} stroke="hsl(var(--muted-foreground))" />
            <Tooltip formatter={(v: number) => inr(v)} cursor={{ fill: "hsl(var(--muted))" }}
              contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="prev" name="Last month" fill="hsl(var(--muted-foreground) / 0.35)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="now" name="This month" fill="hsl(var(--chart-1))" radius={[3, 3, 0, 0]} isAnimationActive={false}>
              <LabelList dataKey="pct" position="top" fontSize={10} formatter={label}
                content={(props) => {
                  const { x, y, width, value } = props as { x: number; y: number; width: number; value: number | null };
                  if (value === null || value === undefined) return null;
                  return <text x={x + width / 2} y={y - 4} textAnchor="middle" fontSize={10}
                    fill={value > 0 ? "hsl(var(--negative))" : "hsl(var(--positive))"}>{label(value)}</text>;
                }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
