"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity } from "lucide-react";
import { NAV } from "@/lib/nav";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";

const isActive = (path: string, href: string) => (href === "/" ? path === "/" : path.startsWith(href));
const groups = Array.from(new Set(NAV.map((n) => n.group)));

/** Mobile-first: bottom tab bar < md, sidebar >= md. Header holds page title + theme toggle. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const title = NAV.find((n) => isActive(path, n.href))?.label ?? "FinPulse";

  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-56 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center gap-2 px-4 font-semibold">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <Activity className="h-4 w-4" />
          </span>
          FinPulse
        </div>
        <nav className="flex-1 space-y-4 px-2 py-2 text-sm">
          {groups.map((g) => (
            <div key={g}>
              <p className="px-2 pb-1 text-xs font-medium text-muted-foreground">{g}</p>
              {NAV.filter((n) => n.group === g).map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-accent",
                    isActive(path, href) && "bg-accent font-medium text-foreground",
                    !isActive(path, href) && "text-muted-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <p className="border-t p-3 text-xs text-muted-foreground">
          Educational coach. Not investment advice.
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground md:hidden">
            <Activity className="h-4 w-4" />
          </span>
          <h1 className="text-base font-semibold">{title}</h1>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-24 md:p-6 md:pb-6">{children}</main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-col items-center gap-0.5 py-2 text-[11px]",
              isActive(path, href) ? "text-primary" : "text-muted-foreground",
            )}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
