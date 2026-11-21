"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Sparkles } from "lucide-react";
import { availableMonths, getReport, type Report } from "@/lib/api";
import { onDataChanged } from "@/lib/events";
import { fmtMonth, inr, pct, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EmailButton } from "@/components/EmailButton";
import { StatTile } from "@/components/placeholder";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="p-4 pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent className="p-4 pt-0">{children}</CardContent>
    </Card>
  );
}

export default function ReportPage() {
  const [months, setMonths] = useState<string[]>([]);
  const [month, setMonth] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () => availableMonths().then((ms) => { setMonths(ms); setMonth((m) => m ?? ms[0]); });
    load();
    return onDataChanged(load);
  }, []);

  useEffect(() => {
    if (!month) return;
    setReport(null);
    setError(null);
    getReport(month).then(setReport).catch((e) => setError((e as Error).message));
  }, [month]);

  const rows = report ? [...report.by_category].sort((a, b) => b.amount - a.amount).slice(0, 8) : [];
  const max = Math.max(1, ...rows.map((r) => Math.max(r.amount, r.budget ?? 0)));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={month ?? undefined} onValueChange={setMonth}>
          <SelectTrigger className="h-9 w-40" aria-label="Report month"><SelectValue placeholder="Month" /></SelectTrigger>
          <SelectContent>
            {months.map((m) => <SelectItem key={m} value={m}>{fmtMonth(m)}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="ml-auto">{month && <EmailButton kind="report" month={month} label="Email this report" />}</div>
      </div>

      {error && <p className="text-sm text-negative">Couldn&apos;t load the report: {error}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Income" value={report ? inr(report.income) : undefined} />
        <StatTile label="Spent" value={report ? inr(report.spend) : undefined} />
        <StatTile label="Saved" value={report ? inr(report.savings) : undefined} />
        <StatTile label="Savings rate" value={report ? pct(report.savings_rate) : undefined} />
      </div>

      <div className="grid gap-3 lg:grid-cols-3 [&>*]:min-w-0">
        <div className="space-y-3 lg:col-span-2">
          <Section title="Highlights">
            {report && report.highlights.length > 0 ? (
              <ul className="space-y-1.5 text-sm">
                {report.highlights.map((h, i) => (
                  <li key={i} className="flex gap-2"><Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />{h}</li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">{report ? "Nothing notable this month." : "Loading…"}</p>}
          </Section>
          <Section title="Categories vs budget">
            <ul className="space-y-2.5">
              {rows.map((r) => {
                const over = r.budget != null && r.amount > r.budget;
                const under = r.budget != null && r.amount <= r.budget;
                return (
                  <li key={r.category} className="space-y-1">
                    <div className="flex items-baseline justify-between gap-2 text-sm">
                      <span className="flex items-center gap-1 truncate">
                        {over && <ArrowUp className="h-3.5 w-3.5 text-negative" aria-label="over budget" />}
                        {under && <ArrowDown className="h-3.5 w-3.5 text-positive" aria-label="within budget" />}
                        {r.category}
                      </span>
                      <span className="whitespace-nowrap tabular-nums">
                        <span className={cn("font-medium", over && "text-negative")}>{inr(r.amount)}</span>
                        {r.budget != null && <span className="text-xs text-muted-foreground"> / {inr(r.budget)}</span>}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted">
                      <div className={cn("h-1.5 rounded-full", over ? "bg-negative" : "bg-chart-1")} style={{ width: `${(r.amount / max) * 100}%` }} />
                    </div>
                  </li>
                );
              })}
              {report && rows.length === 0 && <li className="text-sm text-muted-foreground">No spending this month.</li>}
            </ul>
          </Section>
        </div>
        <div className="space-y-3">
          <Section title="Subscription changes">
            {report && report.recurring_changes.length > 0 ? (
              <ul className="divide-y text-sm">
                {report.recurring_changes.map((c) => (
                  <li key={c.merchant_norm} className="flex justify-between gap-2 py-1.5 tabular-nums">
                    <span>{titleCase(c.merchant_norm)}</span>
                    <span>{inr(c.from)} → <span className={c.to > c.from ? "text-negative" : "text-positive"}>{inr(c.to)}</span></span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">No changes.</p>}
          </Section>
          <Section title="Goal progress">
            {report && report.goal_progress.length > 0 ? (
              <ul className="space-y-2.5 text-sm">
                {report.goal_progress.map((g) => (
                  <li key={g.goal_id} className="space-y-1">
                    <div className="flex justify-between gap-2">
                      <span>{g.name}</span>
                      <span className={cn("text-xs", g.on_track ? "text-positive" : "text-negative")}>
                        {pct(g.pct)} · {g.on_track ? "on track" : "behind"}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted">
                      <div className="h-1.5 rounded-full bg-primary" style={{ width: `${Math.min(1, g.pct) * 100}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">No goals yet.</p>}
          </Section>
        </div>
      </div>
    </div>
  );
}
