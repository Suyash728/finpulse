"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { putProfile, type Profile } from "@/lib/api";
import { useCached } from "@/lib/cache";
import { Q } from "@/lib/queries";
import { emitDataChanged } from "@/lib/events";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const FIELDS = [
  { key: "monthly_income", label: "Monthly income ₹" },
  { key: "fixed_costs", label: "Fixed costs ₹/mo" },
  { key: "emergency_fund", label: "Emergency fund ₹" },
] as const;

export function ProfileForm() {
  const [p, setP] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);

  const cached = useCached(...Q.profile).data;
  useEffect(() => { if (cached && !p) setP(cached); }, [cached, p]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!p) return;
    setSaving(true);
    try {
      setP(await putProfile({ monthly_income: p.monthly_income, fixed_costs: p.fixed_costs, emergency_fund: p.emergency_fund, email: p.email }));
      emitDataChanged();
      toast.success("Profile saved");
    } catch (err) {
      toast.error("Couldn't save profile", { description: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="shadow-none">
      <CardHeader className="p-4"><CardTitle className="text-sm">Profile</CardTitle></CardHeader>
      <CardContent className="p-4 pt-0">
        {!p ? (
          <div className="h-40 animate-pulse rounded-md bg-muted" />
        ) : (
          <form onSubmit={save} className="grid grid-cols-2 gap-3">
            {FIELDS.map((f) => (
              <label key={f.key} className="space-y-1 text-sm">
                <span className="text-muted-foreground">{f.label}</span>
                <Input inputMode="numeric" className="h-11 tabular-nums md:h-9" value={String(p[f.key] ?? "")}
                  onChange={(e) => setP({ ...p, [f.key]: Number(e.target.value.replace(/[^\d]/g, "")) || 0 })} />
              </label>
            ))}
            <label className="col-span-2 space-y-1 text-sm">
              <span className="text-muted-foreground">Email for nudges &amp; reports</span>
              <Input type="email" className="h-11 md:h-9" value={p.email ?? ""} onChange={(e) => setP({ ...p, email: e.target.value || null })} />
            </label>
            <Button type="submit" className="col-span-2 h-11 md:h-9" disabled={saving}>Save profile</Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
