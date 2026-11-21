import { Car, Home, Palmtree, Plane, Shield, Target, type LucideIcon } from "lucide-react";
import type { Goal, SimulateResult } from "@/lib/api";
import { fmtMonth, inr, monthsBetween } from "@/lib/format";
import { cn } from "@/lib/utils";

type Projection = SimulateResult["goal_dates"][number] | undefined;

const ICONS: [RegExp, LucideIcon][] = [
  [/emergency|fund|safety/i, Shield], [/goa|trip|vacation|holiday/i, Palmtree], [/flight|travel/i, Plane],
  [/car|bike/i, Car], [/home|house|flat/i, Home],
];
const iconFor = (name: string) => ICONS.find(([re]) => re.test(name))?.[1] ?? Target;

/** Savings goal card: saved / target, progress, ₹/mo needed (Python), status from /simulate. */
export function GoalCard({ goal, projection }: { goal: Goal; projection: Projection }) {
  const saved = goal.saved_amount ?? 0;
  const ratio = goal.target_amount > 0 ? Math.min(1, saved / goal.target_amount) : 0;
  const late = projection ? monthsBetween(goal.target_date.slice(0, 7), projection.baseline_date.slice(0, 7)) : 0;
  const status = !projection ? null : projection.on_track
    ? { text: "On track", cls: "bg-positive/10 text-positive" }
    : { text: late > 0 ? `${late} mo late` : "Behind", cls: "bg-negative/10 text-negative" };
  const Icon = iconFor(goal.name);
  return (
    <div className="flex gap-3 rounded-xl border bg-card p-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-muted">
        <Icon className="h-5 w-5 text-muted-foreground" />
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate font-medium">{goal.name}</p>
          {status && <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-xs font-medium", status.cls)}>{status.text}</span>}
        </div>
        <p className="tabular-nums">
          <span className="text-lg font-semibold">{inr(saved)}</span>
          <span className="text-sm text-muted-foreground"> / {inr(goal.target_amount)}</span>
        </p>
        <div className="h-1.5 rounded-full bg-muted">
          <div className="h-1.5 rounded-full bg-primary" style={{ width: `${ratio * 100}%` }} />
        </div>
        <div className="flex flex-wrap justify-between gap-x-3 text-xs text-muted-foreground tabular-nums">
          <span>{goal.monthly_needed !== undefined ? `${inr(goal.monthly_needed)}/mo needed` : ""}</span>
          <span>
            Target {fmtMonth(goal.target_date.slice(0, 7))}
            {projection && <> · est. {fmtMonth(projection.baseline_date.slice(0, 7))}</>}
          </span>
        </div>
      </div>
    </div>
  );
}
