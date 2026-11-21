"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getGoals, getNudges, getRecurring, getReport, latestMonth, simulate,
  type Goal, type Nudge, type RecurringItem, type Report, type SimulateResult,
} from "@/lib/api";
import { onDataChanged } from "@/lib/events";
import { AlertList } from "@/components/AlertList";
import { AutoRateChip } from "@/components/AutoRateChip";
import { EmailButton } from "@/components/EmailButton";
import { GoalCard } from "@/components/GoalCard";
import { IngestSheet } from "@/components/IngestSheet";
import { KpiStrip } from "@/components/KpiStrip";
import { BudgetRings } from "@/components/viz/BudgetRings";
import { CategoryDonut } from "@/components/viz/CategoryDonut";
import { ProjectionCard } from "@/components/viz/ProjectionCard";
import { NudgeRows } from "@/components/NudgeRows";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="flex-row items-center justify-between space-y-0 p-4 pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
        {action}
      </CardHeader>
      <CardContent className="p-4 pt-0">{children}</CardContent>
    </Card>
  );
}

export default function HomePage() {
  const [report, setReport] = useState<Report | null>(null);
  const [recurring, setRecurring] = useState<RecurringItem[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [base, setBase] = useState<SimulateResult | null>(null);
  const [nudges, setNudges] = useState<Nudge[]>([]);

  const load = useCallback(() => {
    latestMonth().then((m) => getReport(m)).then(setReport).catch(() => setReport(null));
    getRecurring().then((d) => setRecurring(d.items)).catch(() => setRecurring([]));
    getGoals().then((d) => setGoals(d.items)).catch(() => setGoals([]));
    simulate([]).then(setBase).catch(() => setBase(null));
    getNudges().then((d) => setNudges(d.items)).catch(() => setNudges([]));
  }, []);
  useEffect(() => { load(); return onDataChanged(load); }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <AutoRateChip />
        <div className="ml-auto"><IngestSheet /></div>
      </div>
      <KpiStrip report={report} />
      <div className="grid gap-3 lg:grid-cols-3 [&>*]:min-w-0">
        <div className="space-y-3 lg:col-span-2 [&>*]:min-w-0">
          <Section title="Alerts" action={<EmailButton kind="nudges" label="Email me these" />}>
            <AlertList recurring={recurring}>
              <NudgeRows nudges={nudges} />
            </AlertList>
          </Section>
          {report?.projection && (
            <Section title="Month projection">
              <ProjectionCard p={report.projection} />
            </Section>
          )}
        </div>
        <div className="space-y-3 [&>*]:min-w-0">
          <Section title="Spending by category" action={<Link href="/report" className="-mr-2 inline-flex min-h-11 items-center px-2 text-xs text-primary md:min-h-0">Report</Link>}>
            {report ? <CategoryDonut report={report} /> : <div className="h-48 animate-pulse rounded-md bg-muted" />}
          </Section>
          <Section title="Goals" action={<Link href="/plan" className="-mr-2 inline-flex min-h-11 items-center px-2 text-xs text-primary md:min-h-0">Plan</Link>}>
            <div className="space-y-2">
              {goals.length === 0 && <p className="text-sm text-muted-foreground">No goals yet.</p>}
              {goals.map((g) => (
                <GoalCard key={g.id ?? g.name} goal={g} projection={base?.goal_dates.find((d) => d.goal_id === g.id)} />
              ))}
            </div>
          </Section>
        </div>
      </div>
      {report && (
        <Section title="Monthly budgets" action={<Link href="/transactions" className="-mr-2 inline-flex min-h-11 items-center px-2 text-xs text-primary md:min-h-0">See all</Link>}>
          <BudgetRings report={report} />
        </Section>
      )}
    </div>
  );
}
