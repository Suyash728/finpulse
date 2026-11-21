import type { Goal, SimulateResult } from "@/lib/api";
import { fmtMonth, inr, monthsBetween } from "@/lib/format";
import { cn } from "@/lib/utils";

type Projection = SimulateResult["goal_dates"][number] | undefined;

/** Goal progress + projected date from POST /simulate baseline. */
export function GoalCard({ goal, projection }: { goal: Goal; projection: Projection }) {
  const saved = goal.saved_amount ?? 0;
  const ratio = goal.target_amount > 0 ? Math.min(1, saved / goal.target_amount) : 0;
  const late = projection ? monthsBetween(goal.target_date, projection.baseline_date) : 0;
  const status = !projection
    ? { text: "No projection yet", cls: "text-muted-foreground" }
    : projection.on_track
      ? { text: "On track", cls: "text-positive" }
      : { text: late > 0 ? `${late} month${late === 1 ? "" : "s"} late` : "Off track", cls: "text-negative" };

  return (
    <div className="space-y-2 rounded-xl border bg-card p-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="truncate font-medium">{goal.name}</p>
        <p className={cn("whitespace-nowrap text-xs font-medium", status.cls)}>{status.text}</p>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${ratio * 100}%` }} />
      </div>
      <div className="flex flex-wrap justify-between gap-x-3 text-xs text-muted-foreground tabular-nums">
        <span className="whitespace-nowrap">
          {inr(saved)} of {inr(goal.target_amount)}
        </span>
        <span className="whitespace-nowrap">
          Target {fmtMonth(goal.target_date.slice(0, 7))}
          {projection && <> · est. {fmtMonth(projection.baseline_date.slice(0, 7))}</>}
        </span>
      </div>
    </div>
  );
}
