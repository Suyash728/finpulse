/** Typed client for the FinPulse API. Contract: openapi.yaml. Every response = Envelope<T>. */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8787";

export type Envelope<T> = { success: boolean; data: T | null; error: string | null };

export class ApiError extends Error {}

export const CATEGORIES = [
  "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
  "Dining", "Food Delivery", "Shopping", "Travel", "Entertainment", "Subscriptions",
  "Fuel", "Transfers", "Income", "Investments", "Other",
] as const;
export type Category = (typeof CATEGORIES)[number];
export const ESSENTIAL: ReadonlySet<Category> = new Set<Category>([
  "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
]);

export type Transaction = {
  id: string; upload_id: string | null; date: string; amount: number; direction: "dr" | "cr";
  raw_desc: string; merchant_norm: string; category: Category; cat_source: "rule" | "ai" | "user";
  confidence: number; needs_review: boolean;
};
export type Rule = { id: string; match_type: "exact" | "normalized"; pattern: string; category: Category; hits: number };
export type Reconciled = { ok: boolean; opening: number; closing: number; computed_closing: number } | null;
export type IngestResult = { upload_id: string; rows: Transaction[]; auto_rate: number; reconciled: Reconciled };
export type Profile = {
  monthly_income: number; fixed_costs: number; emergency_fund: number; email: string | null;
  budgets: Partial<Record<Category, number>>;
};
export type Goal = { id?: string; name: string; target_amount: number; saved_amount?: number; target_date: string };
export type RecurringItem = {
  id: string; merchant_norm: string; category: Category; amount: number; prev_amount: number | null;
  cadence: "monthly" | "weekly" | "yearly"; last_seen: string; status: "active" | "changed" | "unused"; note?: string;
};
export type Nudge = {
  id: string; kind: "drift" | "price_change" | "unused" | "essentials_over_income";
  category: string | null; message: string; severity: "info" | "warn" | "alert"; month: string;
};
export type Adjustment = { category: Category; pct_change?: number; abs_change?: number };
export type SimulateResult = {
  baseline: { monthly_spend: number; monthly_savings: number };
  scenario: { monthly_spend: number; monthly_savings: number };
  goal_dates: { goal_id: string; name: string; baseline_date: string; scenario_date: string; on_track: boolean }[];
  warnings: string[];
};
export type Report = {
  month: string; income: number; spend: number; savings: number; savings_rate: number;
  by_category: { category: Category; amount: number; budget: number | null }[];
  recurring_changes: { merchant_norm: string; from: number; to: number }[];
  goal_progress: { goal_id: string; name: string; pct: number; on_track: boolean }[];
  highlights: string[];
};
export type CoachResult = { events: import("@/components/TracePanel").TraceEvent[]; answer: string | null; refused: boolean };

/** fetch + unwrap the envelope; throws ApiError on success:false or HTTP error. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: isForm ? init?.headers : { "content-type": "application/json", ...init?.headers },
  });
  const env = (await res.json().catch(() => null)) as Envelope<T> | null;
  if (!res.ok || !env?.success) throw new ApiError(env?.error ?? `HTTP ${res.status}`);
  return env.data as T;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T,>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const postFile = <T,>(path: string, file: File | Blob, name = "upload") => {
  const fd = new FormData();
  fd.append("file", file, file instanceof File ? file.name : name);
  return api<T>(path, { method: "POST", body: fd });
};

/** Subscribe to an SSE trace stream; returns a close() function. */
export function sse<E>(path: string, onEvent: (e: E) => void, onEnd?: () => void): () => void {
  const src = new EventSource(`${API_BASE}${path}`);
  src.onmessage = (m) => onEvent(JSON.parse(m.data) as E);
  src.addEventListener("end", () => { src.close(); onEnd?.(); });
  src.onerror = () => { src.close(); onEnd?.(); };
  return () => src.close();
}

// ---------- endpoint helpers (slice 1) ----------
export type TxnFilters = { month?: string; category?: Category; needs_review?: boolean };
export type CorrectResult = { rule: Rule; similar_ids: string[] };
export type AutoRatePoint = { upload_id: string; filename: string; created_at: string; auto_rate: number };

const qs = (p: Record<string, string | boolean | undefined>) => {
  const s = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== undefined && v !== "" && s.set(k, String(v)));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const ingestSms = (text: string) => post<IngestResult>("/ingest", { kind: "sms", text });
export const ingestFile = (file: File | Blob, name?: string) => postFile<IngestResult>("/ingest", file, name);
export const listTransactions = (f: TxnFilters = {}) =>
  get<{ items: Transaction[]; total: number }>(`/transactions${qs(f)}`);
export const correctTransaction = (id: string, category: Category) =>
  post<CorrectResult>(`/transactions/${encodeURIComponent(id)}/correct`, { category });
export const applyRule = (rule_id: string, transaction_ids: string[]) =>
  post<{ updated: number }>("/rules/apply", { rule_id, transaction_ids });
export const getAutoRate = () => get<{ series: AutoRatePoint[] }>("/stats/auto-rate");

// ---------- endpoint helpers (slice 2) ----------
export const getProfile = () => get<Profile>("/profile");
export const putProfile = (p: Partial<Profile>) => put<Profile>("/profile", p);
export const getGoals = () => get<{ items: Goal[] }>("/goals");
export const createGoal = (g: Goal) => post<Goal>("/goals", g);
export const getRecurring = () => get<{ items: RecurringItem[] }>("/recurring");
export const simulate = (adjustments: Adjustment[]) => post<SimulateResult>("/simulate", { adjustments });
export const getReport = (month: string) => get<Report>(`/report/${encodeURIComponent(month)}`);

/** Newest month that has transactions (YYYY-MM), else the current month. */
export async function latestMonth(): Promise<string> {
  try {
    const { items } = await listTransactions();
    const max = items.reduce((m, t) => (t.date > m ? t.date : m), "");
    if (max) return max.slice(0, 7);
  } catch { /* fall through */ }
  return new Date().toISOString().slice(0, 7);
}

// ---------- endpoint helpers (slice 3: coach) ----------
export type ChatTurn = { role: "user" | "assistant"; content: string };
export const startCoach = (message: string, history: ChatTurn[]) =>
  post<{ run_id: string }>("/coach", { message, history });
export const getCoach = (runId: string) => get<CoachResult>(`/coach/${encodeURIComponent(runId)}`);
