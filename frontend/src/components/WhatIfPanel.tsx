"use client";

import { useEffect, useRef, useState } from "react";
import { Info, RotateCcw } from "lucide-react";
import { simulate, type Adjustment, type Category, type SimulateResult } from "@/lib/api";
import { fmtMonth, inr } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ProjectionChart } from "@/components/ProjectionChart";

// Discretionary only. Essentials are never offered as cuts (guardrail visible in the UI);
// rent / income CHANGES are allowed as absolute amounts below.
const SLIDERS: Category[] = ["Dining", "Food Delivery", "Shopping", "Entertainment", "Travel", "Subscriptions"];

export function WhatIfPanel() {
  const [pcts, setPcts] = useState<Record<string, number>>({});
  const [rent, setRent] = useState("");
  const [income, setIncome] = useState("");
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    const adjustments: Adjustment[] = [
      ...Object.entries(pcts).filter(([, v]) => v !== 0).map(([c, v]) => ({ category: c as Category, pct_change: v })),
      ...(Number(rent) ? [{ category: "Rent" as Category, abs_change: Number(rent) }] : []),
      ...(Number(income) ? [{ category: "Income" as Category, abs_change: Number(income) }] : []),
    ];
    const id = ++seq.current;
    const t = setTimeout(() => {
      simulate(adjustments)
        .then((r) => id === seq.current && (setResult(r), setError(null)))
        .catch((e) => id === seq.current && setError((e as Error).message));
    }, 300);
    return () => clearTimeout(t);
  }, [pcts, rent, income]);

  const reset = () => { setPcts({}); setRent(""); setIncome(""); };
  const touched = Object.values(pcts).some(Boolean) || !!Number(rent) || !!Number(income);

  return (
    <Card className="shadow-none">
      <CardHeader className="flex-row items-start justify-between space-y-0 p-4">
        <div className="space-y-1">
          <CardTitle className="text-sm">What-if simulator</CardTitle>
          <CardDescription className="text-xs">Move a slider. Every number is calculated by the server.</CardDescription>
        </div>
        {touched && (
          <Button variant="ghost" size="sm" onClick={reset} className="h-9">
            <RotateCcw /> Reset
          </Button>
        )}
      </CardHeader>
      {/* mobile: live result stays visible while dragging */}
      {result && (
        <div className="sticky top-14 z-10 mx-4 mb-3 flex items-center justify-between gap-2 rounded-md border bg-background/95 px-3 py-2 text-xs backdrop-blur lg:hidden">
          <span className="tabular-nums">
            Saves <span className="font-semibold text-primary">{inr(result.scenario.monthly_savings)}</span>/mo
          </span>
          {result.goal_dates[0] && (
            <span className="truncate tabular-nums">
              {result.goal_dates[0].name}:{" "}
              {result.goal_dates[0].baseline_date !== result.goal_dates[0].scenario_date && (
                <span className="text-muted-foreground line-through">{fmtMonth(result.goal_dates[0].baseline_date.slice(0, 7))}</span>
              )}{" "}
              <span className="font-semibold">{fmtMonth(result.goal_dates[0].scenario_date.slice(0, 7))}</span>
            </span>
          )}
        </div>
      )}
      <CardContent className="grid gap-5 p-4 pt-0 lg:grid-cols-2">
        <div className="space-y-3">
          {SLIDERS.map((c) => {
            const v = pcts[c] ?? 0;
            return (
              <label key={c} className="block space-y-1">
                <span className="flex justify-between text-sm">
                  <span>{c}</span>
                  <span className={`tabular-nums ${v < 0 ? "text-positive" : v > 0 ? "text-negative" : "text-muted-foreground"}`}>
                    {v > 0 ? "+" : ""}{v}%
                  </span>
                </span>
                <input
                  type="range" min={-50} max={50} step={5} value={v}
                  aria-label={`${c} change percent`}
                  onChange={(e) => setPcts((p) => ({ ...p, [c]: Number(e.target.value) }))}
                  className="h-11 w-full cursor-pointer accent-[hsl(var(--primary))] md:h-6"
                />
              </label>
            );
          })}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <label className="space-y-1 text-sm">
              <span>Rent change ₹/mo</span>
              <Input inputMode="numeric" placeholder="e.g. 3000" value={rent}
                onChange={(e) => setRent(e.target.value.replace(/[^\d-]/g, ""))} className="h-11 md:h-9" />
            </label>
            <label className="space-y-1 text-sm">
              <span>Income change ₹/mo</span>
              <Input inputMode="numeric" placeholder="e.g. -5000" value={income}
                onChange={(e) => setIncome(e.target.value.replace(/[^\d-]/g, ""))} className="h-11 md:h-9" />
            </label>
          </div>
          <p className="flex gap-1.5 text-xs text-muted-foreground">
            <Info className="mt-0.5 h-3 w-3 shrink-0" />
            Essentials (rent, utilities, groceries, medical, EMI, insurance, education) aren&apos;t offered as cuts. You
            can model them rising.
          </p>
        </div>

        <div className="space-y-3">
          {result && result.warnings.length > 0 && (
            <div className="rounded-md border border-warning/50 bg-warning/10 p-3 text-sm">
              {result.warnings.map((w, i) => <p key={i}>{w}</p>)}
              <p className="mt-1 text-xs text-muted-foreground">
                If essentials cost more than you earn, the fix is on the income side, or talk to a fee-only financial
                advisor. Cutting essentials isn&apos;t a plan.
              </p>
            </div>
          )}
          {error && <p className="text-sm text-negative">Simulation failed: {error}</p>}
          {result ? <ProjectionChart result={result} /> : <div className="h-44 animate-pulse rounded-md bg-muted" />}
          {result && <p className="sr-only">Scenario savings {inr(result.scenario.monthly_savings)} per month</p>}
        </div>
      </CardContent>
    </Card>
  );
}
