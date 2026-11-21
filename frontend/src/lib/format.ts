/** Display-only formatting. All figures are computed server-side; we never do money math here. */

const inrFmt = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export const inr = (n: number) => inrFmt.format(n);

export const pct = (x: number) => `${Math.round(x * 100)}%`;

export const fmtDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });

export const fmtMonth = (ym: string) =>
  new Date(`${ym}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "numeric" });

/** "raz payu8823" -> "Raz Payu8823" */
export const titleCase = (s: string) => s.replace(/\b[a-z]/g, (c) => c.toUpperCase());

export const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

/** Whole months from a to b (dates, not money). Positive = b is later. */
export const monthsBetween = (a: string, b: string) => {
  const [ay, am] = a.split("-").map(Number);
  const [by, bm] = b.split("-").map(Number);
  return (by - ay) * 12 + (bm - am);
};
