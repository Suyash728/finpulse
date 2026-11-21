"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { createGoal } from "@/lib/api";
import { useCached } from "@/lib/cache";
import { emitDataChanged } from "@/lib/events";
import { Q } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { GoalCard } from "@/components/GoalCard";

export function GoalsEditor() {
  const goals = useCached(...Q.goals).data?.items ?? null;
  const base = useCached(...Q.baseline).data ?? null;
  const [form, setForm] = useState({ name: "", target_amount: "", target_date: "" });
  const [adding, setAdding] = useState(false);


  async function add(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      await createGoal({ name: form.name.trim(), target_amount: Number(form.target_amount), target_date: form.target_date });
      setForm({ name: "", target_amount: "", target_date: "" });
      emitDataChanged();
      toast.success("Goal added");
    } catch (err) {
      toast.error("Couldn't add goal", { description: (err as Error).message });
    } finally {
      setAdding(false);
    }
  }

  const valid = form.name.trim() && Number(form.target_amount) > 0 && form.target_date;
  return (
    <Card className="shadow-none">
      <CardHeader className="p-4"><CardTitle className="text-sm">Goals</CardTitle></CardHeader>
      <CardContent className="space-y-3 p-4 pt-0">
        {goals === null ? (
          <div className="h-20 animate-pulse rounded-md bg-muted" />
        ) : goals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No goals yet.</p>
        ) : (
          goals.map((g) => (
            <GoalCard key={g.id ?? g.name} goal={g} projection={base?.goal_dates.find((d) => d.goal_id === g.id)} />
          ))
        )}
        <form onSubmit={add} className="grid grid-cols-2 gap-2 border-t pt-3">
          <Input placeholder="Goal name" className="col-span-2 h-11 md:h-9" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input placeholder="Target ₹" inputMode="numeric" className="h-11 md:h-9" value={form.target_amount}
            onChange={(e) => setForm({ ...form, target_amount: e.target.value.replace(/[^\d]/g, "") })} />
          <Input type="date" aria-label="Target date" className="h-11 md:h-9" value={form.target_date}
            onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
          <Button type="submit" variant="secondary" className="col-span-2 h-11 md:h-9" disabled={!valid || adding}>
            <Plus /> Add goal
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
