import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Stat tile: label, big value, optional delta. Values come from the API (computed in Python). */
export function StatTile({ label, value = "—", delta }: { label: string; value?: string; delta?: string }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="p-3 pb-1">
        <CardDescription className="text-xs">{label}</CardDescription>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <p className="text-xl font-semibold tabular-nums">{value}</p>
        {delta && <p className="text-xs text-muted-foreground">{delta}</p>}
      </CardContent>
    </Card>
  );
}

export function TodoCard({ title, slice, children }: { title: string; slice: number; children?: React.ReactNode }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="p-4">
        <CardTitle className="text-sm">{title}</CardTitle>
        <CardDescription className="font-mono text-xs">TODO(slice {slice})</CardDescription>
      </CardHeader>
      {children && <CardContent className="p-4 pt-0 text-sm text-muted-foreground">{children}</CardContent>}
    </Card>
  );
}
