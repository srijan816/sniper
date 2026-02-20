import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { SniperChevron } from "@/components/app/sniper-chevron";

export function ThreatMetric({
  label,
  value,
  delta,
  positive = true,
  icon: Icon,
}: {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
  icon: LucideIcon;
}) {
  return (
    <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="rounded-sm bg-secondary p-2 text-foreground">
          <Icon className="h-4 w-4" />
        </div>
        {delta ? (
          <span className={cn("inline-flex items-center gap-1 text-app-xs font-medium", positive ? "text-[#0A7C2E]" : "text-destructive")}>
            <SniperChevron className={cn("h-3 w-3", !positive && "rotate-180")} />
            {delta}
          </span>
        ) : null}
      </div>
      <p className="font-heading text-app-3xl font-bold text-foreground">{value}</p>
      <p className="text-app-sm text-muted-foreground">{label}</p>
    </article>
  );
}
