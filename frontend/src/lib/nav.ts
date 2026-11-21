import { Home, ListChecks, Target, MessageSquare, FileText, type LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; group: string };

export const NAV: NavItem[] = [
  { href: "/", label: "Home", icon: Home, group: "Overview" },
  { href: "/transactions", label: "Transactions", icon: ListChecks, group: "Money" },
  { href: "/plan", label: "Plan", icon: Target, group: "Money" },
  { href: "/coach", label: "Coach", icon: MessageSquare, group: "Insights" },
  { href: "/report", label: "Report", icon: FileText, group: "Insights" },
];
