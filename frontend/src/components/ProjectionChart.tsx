"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SimulateResult } from "@/lib/api";
import { fmtDate, inr } from "@/lib/format";
import { cn } from "@/lib/utils";

const compact = (n: number) => new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(n);

/** Baseline vs scenario (values from /simulate) + goal dates moving. */
export function ProjectionChart({ result }: { result: SimulateResult }) {
  const data = [
    { name: "Spend / mo", baseline: result.baseline.monthly_spend, scenario: result.scenario.monthly_spend },
    { name: "Savings / mo", baseline: result.baseline.monthly_savings, scenario: result.scenario.monthly_savings },
  ];
  return (
    <div className="space-y-3">
      <div className="h-44 w-full">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 4, right: 4, left: -12, bottom: 0 }} barGap={4}>
            <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
            <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} stroke="hsl(var(--muted-foreground))" />
            <YAxis tickLine={false} axisLine={false} fontSize={11} tickFormatter={compact} stroke="hsl(var(--muted-foreground))" />
            <Tooltip
              cursor={{ fill: "hsl(var(--muted))" }}
              formatter={(v: number) => inr(v)}
              contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
            />
            <Bar dataKey="baseline" name="Now" fill="hsl(var(--muted-foreground) / 0.45)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="scenario" name="What-if" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs tabular-nums">
        <p className="text-muted-foreground">
          Now: saves <span className="font-medium text-foreground">{inr(result.baseline.monthly_savings)}</span>/mo
        </p>
        <p className="text-muted-foreground">
          What-if: saves <span className="font-medium text-primary">{inr(result.scenario.monthly_savings)}</span>/mo
        </p>
      </div>
      {result.goal_dates.length > 0 && (
        <ul className="divide-y rounded-md border text-sm">
          {result.goal_dates.map((g) => {
            const moved = g.baseline_date !== g.scenario_date;
            const earlier = g.scenario_date < g.baseline_date;
            return (
              <li key={g.goal_id} className="flex items-center justify-between gap-2 px-3 py-2">
                <span className="truncate">{g.name}</span>
                <span className="whitespace-nowrap text-xs tabular-nums">
                  {moved && <span className="mr-1.5 text-muted-foreground line-through">{fmtDate(g.baseline_date)}</span>}
                  <span className={cn("font-medium", moved && (earlier ? "text-positive" : "text-negative"))}>
                    {fmtDate(g.scenario_date)}
                  </span>
                  <span className={cn("ml-1.5", g.on_track ? "text-positive" : "text-negative")}>
                    {g.on_track ? "✓" : "late"}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
