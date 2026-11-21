import {
  Bus, Car, CircleDollarSign, Clapperboard, CreditCard, Fuel, GraduationCap, HeartPulse, Home, Landmark,
  Plane, Receipt, Repeat, ShieldCheck, ShoppingBag, ShoppingCart, Utensils, UtensilsCrossed, Wallet, Zap,
  type LucideIcon,
} from "lucide-react";
import type { Category } from "@/lib/api";

export const CATEGORY_ICON: Record<Category, LucideIcon> = {
  Rent: Home, Utilities: Zap, Groceries: ShoppingCart, Medical: HeartPulse, EMI: Landmark, Insurance: ShieldCheck,
  Education: GraduationCap, Dining: Utensils, "Food Delivery": UtensilsCrossed, Shopping: ShoppingBag, Travel: Plane,
  Entertainment: Clapperboard, Subscriptions: Repeat, Fuel, Transfers: Wallet, Income: CircleDollarSign,
  Investments: CreditCard, Other: Receipt,
};
export const iconFor = (c: string): LucideIcon => CATEGORY_ICON[c as Category] ?? (c === "Travel" ? Bus : Car);

/** Theme-token palette for categorical charts (works in light + dark). */
export const CHART_COLORS = [
  "hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--chart-5))",
  "hsl(var(--muted-foreground) / 0.75)", "hsl(var(--chart-1) / 0.55)", "hsl(var(--chart-2) / 0.55)",
];

export const inrCompact = (n: number) =>
  `₹${new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(n)}`;
