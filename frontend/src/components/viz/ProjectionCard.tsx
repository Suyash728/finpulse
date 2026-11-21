"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Projection } from "@/lib/api";
import { inrCompact } from "@/lib/category-meta";
import { inr } from "@/lib/format";

/** Month projection: stats + cumulative spend vs budget (all values from /report.projection). */
export function ProjectionCard({ p }: { p: Projection }) {
  const ok = p.on_track;
  const stats = [
    { label: "Days left", value: String(p.days_left) },
    { label: "Avg / day", value: inr(p.avg_per_day) },
    { label: "Spent so far", value: inr(p.spent_so_far) },
    { label: "Projected", value: inr(p.projected) },
  ];
  return (
    <div className="space-y-3">
      <p className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${ok ? "bg-positive/10 text-positive" : "bg-negative/10 text-negative"}`}>
        {ok ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
        {ok ? "On track this month" : `Projected above the ${inr(p.budget_total)} budget`}
      </p>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label}>
            <dt className="text-xs text-muted-foreground">{s.label}</dt>
            <dd className="text-base font-semibold tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>
      <div className="h-36 w-full">
        <ResponsiveContainer>
          <ComposedChart data={p.cumulative} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.35} />
                <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" tickLine={false} axisLine={false} fontSize={10} interval={4} stroke="hsl(var(--muted-foreground))" />
            <YAxis tickLine={false} axisLine={false} fontSize={10} tickFormatter={inrCompact} width={48} stroke="hsl(var(--muted-foreground))" />
            <Tooltip formatter={(v: number) => inr(v)} labelFormatter={(d) => `Day ${d}`}
              contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
            {p.budget_total > 0 && (
              <ReferenceLine y={p.budget_total} stroke="hsl(var(--negative))" strokeDasharray="4 4"
                label={{ value: "Budget", position: "insideTopRight", fontSize: 10, fill: "hsl(var(--negative))" }} />
            )}
            <Area type="monotone" dataKey="actual" name="Spent" stroke="hsl(var(--chart-1))" strokeWidth={2} fill="url(#spendFill)" isAnimationActive={false} />
            <Line type="monotone" dataKey="projected" name="Projected" stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
