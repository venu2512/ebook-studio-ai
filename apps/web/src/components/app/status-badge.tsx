import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { StatusMeta } from "@/lib/status";

export function StatusBadge({
  meta,
  className,
  showDot = true,
}: {
  meta: StatusMeta;
  className?: string;
  showDot?: boolean;
}) {
  return (
    <Badge variant={meta.variant} className={cn("gap-1.5 capitalize", className)}>
      {showDot && <span className={cn("size-1.5 rounded-full", meta.dot)} />}
      {meta.label}
    </Badge>
  );
}
