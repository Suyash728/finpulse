/** Shared cache keys + fetchers so every page (and prefetch) hits the same entries. */
import {
  getAutoRate, getGoals, getNudges, getProfile, getRecurring, getReport, listTransactions, simulate,
} from "@/lib/api";
import { prefetch } from "@/lib/cache";

export const Q = {
  reportLatest: ["report:latest", () => getReport("latest")] as const,
  report: (m: string) => [`report:${m}`, () => getReport(m)] as const,
  recurring: ["recurring", getRecurring] as const,
  goals: ["goals", getGoals] as const,
  baseline: ["simulate:baseline", () => simulate([])] as const,
  nudges: ["nudges", getNudges] as const,
  autoRate: ["auto-rate", getAutoRate] as const,
  profile: ["profile", getProfile] as const,
  transactions: ["transactions:all", () => listTransactions()] as const,
};

/** Warm the data every tab needs, right after the app shell mounts. */
export function prefetchAll() {
  for (const [k, f] of [Q.reportLatest, Q.recurring, Q.goals, Q.baseline, Q.nudges, Q.autoRate, Q.profile, Q.transactions]) {
    prefetch(k, f as () => Promise<unknown>);
  }
}
