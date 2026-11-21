"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getGoals, getRecurring, getReport, latestMonth, simulate,
  type Goal, type RecurringItem, type Report, type SimulateResult,
} from "@/lib/api";
import { onDataChanged } from "@/lib/events";
import { AlertList } from "@/components/AlertList";
import { AutoRateChip } from "@/components/AutoRateChip";
import { CategoryBars } from "@/components/CategoryBars";
import { GoalCard } from "@/components/GoalCard";
import { IngestSheet } from "@/components/IngestSheet";
import { KpiStrip } from "@/components/KpiStrip";
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

  const load = useCallback(() => {
    latestMonth().then((m) => getReport(m)).then(setReport).catch(() => setReport(null));
    getRecurring().then((d) => setRecurring(d.items)).catch(() => setRecurring([]));
    getGoals().then((d) => setGoals(d.items)).catch(() => setGoals([]));
    simulate([]).then(setBase).catch(() => setBase(null));
  }, []);
  useEffect(() => { load(); return onDataChanged(load); }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <AutoRateChip />
        <div className="ml-auto"><IngestSheet /></div>
      </div>
      <KpiStrip report={report} />
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <Section title="Alerts">
            {/* TODO(slice 4): nudges from GET /nudges render as extra rows here */}
            <AlertList recurring={recurring} />
          </Section>
          <Section title="Where the money went" action={<Link href="/transactions" className="text-xs text-primary">See all</Link>}>
            <CategoryBars rows={report?.by_category ?? []} />
          </Section>
        </div>
        <Section title="Goals" action={<Link href="/plan" className="text-xs text-primary">Plan</Link>}>
          <div className="space-y-2">
            {goals.length === 0 && <p className="text-sm text-muted-foreground">No goals yet.</p>}
            {goals.map((g) => (
              <GoalCard key={g.id ?? g.name} goal={g} projection={base?.goal_dates.find((d) => d.goal_id === g.id)} />
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
