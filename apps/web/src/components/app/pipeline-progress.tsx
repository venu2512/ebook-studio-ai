"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  Circle,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useJobStream } from "@/hooks/use-job-stream";
import { jobsApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { cn } from "@/lib/utils";
import { duration, formatUsd } from "@/lib/format";
import type { PipelineStep } from "@ebook/shared";

const STEP_ICON: Record<PipelineStep["status"], React.ComponentType<{ className?: string }>> = {
  pending: Circle,
  running: Loader2,
  succeeded: CheckCircle2,
  failed: AlertTriangle,
  skipped: Circle,
};

export function PipelineProgress({
  jobId,
  onDone,
  onRetried,
  title = "Generation pipeline",
}: {
  jobId: string;
  onDone?: (status: string) => void;
  onRetried?: () => void;
  title?: string;
}) {
  const queryClient = useQueryClient();
  const { state: streamed, status: streamStatus, error: streamError, done } = useJobStream(jobId);

  // Poll the job itself for a reliable status even if the stream drops.
  const jobQuery = useQuery({
    queryKey: queryKeys.job(jobId),
    queryFn: () => jobsApi.get(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && ["succeeded", "failed", "cancelled"].includes(status)) return false;
      return 1500;
    },
  });

  const job = jobQuery.data;
  const state = streamed;
  const status = job?.status ?? state?.status ?? "queued";
  const progress = job?.progress_pct ?? state?.progress_pct ?? 0;
  const steps = state?.steps ?? [];
  const terminal = ["succeeded", "failed", "cancelled"].includes(status);
  const errorMessage = job?.error ?? state?.message ?? streamError ?? null;

  const doneStatus = done?.status;
  React.useEffect(() => {
    if (doneStatus && onDone) onDone(doneStatus);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doneStatus]);

  async function handleCancel() {
    try {
      await jobsApi.cancel(jobId);
      toast.message("Cancellation requested");
      queryClient.invalidateQueries({ queryKey: queryKeys.job(jobId) });
    } catch {
      toast.error("Could not cancel the job");
    }
  }

  async function handleRetry() {
    try {
      await jobsApi.retry(jobId);
      toast.success("Retrying…");
      queryClient.invalidateQueries({ queryKey: queryKeys.job(jobId) });
      onRetried?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not retry the job");
    }
  }

  return (
    <Card>
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-medium">{title}</h3>
            <p className="text-xs text-muted-foreground">
              {status === "running" || status === "queued"
                ? `Working… ${progress}%`
                : status === "succeeded"
                  ? "All steps finished"
                  : status === "failed"
                    ? "Stopped on an error"
                    : "Cancelled"}
              {streamStatus === "error" && " · live stream unavailable, polling"}
            </p>
          </div>
          {!terminal && (
            <Button variant="outline" size="sm" onClick={handleCancel}>
              <Ban className="size-4" /> Cancel
            </Button>
          )}
          {status === "failed" && (
            <Button variant="outline" size="sm" onClick={handleRetry}>
              <RotateCcw className="size-4" /> Retry
            </Button>
          )}
        </div>

        <Progress value={progress} />

        <ul className="grid gap-2 sm:grid-cols-2">
          {steps.map((step) => {
            const Icon = STEP_ICON[step.status] ?? Circle;
            return (
              <li
                key={step.key}
                className={cn(
                  "flex items-center gap-3 rounded-lg border p-3",
                  step.status === "running" && "border-primary/40 bg-primary/5",
                  step.status === "failed" && "border-destructive/40 bg-destructive/5",
                )}
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={step.status}
                    initial={{ scale: 0.6, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.6, opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className={cn(
                      "grid size-7 shrink-0 place-items-center rounded-full",
                      step.status === "succeeded" && "bg-success/15 text-success",
                      step.status === "running" && "bg-primary/15 text-primary",
                      step.status === "failed" && "bg-destructive/15 text-destructive",
                      step.status === "pending" && "bg-muted text-muted-foreground",
                      step.status === "skipped" && "bg-muted text-muted-foreground",
                    )}
                  >
                    <Icon className={cn("size-4", step.status === "running" && "animate-spin")} />
                  </motion.span>
                </AnimatePresence>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{step.label}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {step.tokens > 0
                      ? `${step.tokens.toLocaleString()} tokens · ${formatUsd(step.cost_usd, 4)}`
                      : step.detail ?? "Waiting"}
                    {step.elapsed_ms ? ` · ${duration(step.elapsed_ms)}` : ""}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>

        {status === "failed" && errorMessage && (
          <Alert variant="destructive">
            <AlertDescription>
              <span className="font-medium">Error:</span> {errorMessage}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
