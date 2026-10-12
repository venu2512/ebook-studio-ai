import type { BadgeProps } from "@/components/ui/badge";

type Variant = BadgeProps["variant"];

export interface StatusMeta {
  label: string;
  variant: Variant;
  /** Tailwind class for a small dot indicator. */
  dot: string;
  description?: string;
}

const BOOK_STATUS: Record<string, StatusMeta> = {
  draft: { label: "Draft", variant: "muted", dot: "bg-muted-foreground", description: "Not started" },
  planning: {
    label: "Planning",
    variant: "info",
    dot: "bg-primary",
    description: "Outline approved",
  },
  awaiting_approval: {
    label: "Awaiting review",
    variant: "warning",
    dot: "bg-warning",
    description: "Review and approve the outline",
  },
  writing: { label: "Writing", variant: "info", dot: "bg-primary", description: "Chapters in progress" },
  editing: { label: "Editing", variant: "info", dot: "bg-primary" },
  designing: { label: "Designing", variant: "info", dot: "bg-primary" },
  ready: { label: "Ready", variant: "success", dot: "bg-success", description: "Ready to export" },
  failed: { label: "Failed", variant: "destructive", dot: "bg-destructive" },
  cancelled: { label: "Cancelled", variant: "muted", dot: "bg-muted-foreground" },
};

const JOB_STATUS: Record<string, StatusMeta> = {
  queued: { label: "Queued", variant: "muted", dot: "bg-muted-foreground" },
  running: { label: "Running", variant: "info", dot: "bg-primary" },
  succeeded: { label: "Succeeded", variant: "success", dot: "bg-success" },
  failed: { label: "Failed", variant: "destructive", dot: "bg-destructive" },
  cancelled: { label: "Cancelled", variant: "muted", dot: "bg-muted-foreground" },
};

const CHAPTER_STATUS: Record<string, StatusMeta> = {
  pending: { label: "Pending", variant: "muted", dot: "bg-muted-foreground" },
  generating: { label: "Generating", variant: "info", dot: "bg-primary" },
  drafted: { label: "Drafted", variant: "secondary", dot: "bg-secondary-foreground" },
  edited: { label: "Edited", variant: "secondary", dot: "bg-secondary-foreground" },
  fact_checked: { label: "Fact-checked", variant: "info", dot: "bg-primary" },
  approved: { label: "Approved", variant: "success", dot: "bg-success" },
  failed: { label: "Failed", variant: "destructive", dot: "bg-destructive" },
};

const STEP_STATUS: Record<string, StatusMeta> = {
  pending: { label: "Pending", variant: "muted", dot: "bg-muted-foreground" },
  running: { label: "Running", variant: "info", dot: "bg-primary" },
  succeeded: { label: "Done", variant: "success", dot: "bg-success" },
  failed: { label: "Failed", variant: "destructive", dot: "bg-destructive" },
  skipped: { label: "Skipped", variant: "muted", dot: "bg-muted-foreground" },
};

const EXPORT_STATUS: Record<string, StatusMeta> = {
  ready: { label: "Ready", variant: "success", dot: "bg-success" },
  pending: { label: "Pending", variant: "muted", dot: "bg-muted-foreground" },
  processing: { label: "Processing", variant: "info", dot: "bg-primary" },
  failed: { label: "Failed", variant: "destructive", dot: "bg-destructive" },
};

const FALLBACK: StatusMeta = {
  label: "Unknown",
  variant: "muted",
  dot: "bg-muted-foreground",
};

function lookup(map: Record<string, StatusMeta>, key: string | null | undefined): StatusMeta {
  if (!key) return FALLBACK;
  return map[key] ?? { ...FALLBACK, label: key.replace(/_/g, " ") };
}

export const bookStatus = (key: string | null | undefined) => lookup(BOOK_STATUS, key);
export const jobStatus = (key: string | null | undefined) => lookup(JOB_STATUS, key);
export const chapterStatus = (key: string | null | undefined) => lookup(CHAPTER_STATUS, key);
export const stepStatus = (key: string | null | undefined) => lookup(STEP_STATUS, key);
export const exportStatus = (key: string | null | undefined) => lookup(EXPORT_STATUS, key);

export function isTerminalJob(status: string | null | undefined): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}
