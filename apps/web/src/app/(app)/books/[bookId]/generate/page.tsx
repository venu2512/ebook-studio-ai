"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Layers, Play, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { PipelineProgress } from "@/components/app/pipeline-progress";
import { StatusBadge } from "@/components/app/status-badge";
import { booksApi, jobsApi, chaptersApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { jobStatus } from "@/lib/status";
import { relativeTime } from "@/lib/format";
import { pluralize } from "@/lib/utils";

export default function GeneratePage() {
  const { bookId } = useParams<{ bookId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = React.useState<string | null>(null);

  const bookQuery = useQuery({
    queryKey: queryKeys.book(bookId),
    queryFn: () => booksApi.get(bookId),
  });
  const estimateQuery = useQuery({
    queryKey: queryKeys.costEstimate(bookId),
    queryFn: () => booksApi.costEstimate(bookId),
  });
  const chaptersQuery = useQuery({
    queryKey: queryKeys.chapters(bookId),
    queryFn: () => chaptersApi.list(bookId),
  });
  const jobsQuery = useQuery({
    queryKey: queryKeys.bookJobs(bookId),
    queryFn: () => jobsApi.listForBook(bookId, 10),
    refetchInterval: activeJobId ? 3000 : false,
  });

  const activeJob = jobsQuery.data?.items.find(
    (j) => j.status === "queued" || j.status === "running",
  );

  React.useEffect(() => {
    if (activeJob) setActiveJobId(activeJob.id);
  }, [activeJob]);

  const start = useMutation({
    mutationFn: () => jobsApi.generate(bookId, { type: "full_book" }),
    onSuccess: (job) => {
      setActiveJobId(job.id);
      toast.success("Generation started");
      queryClient.invalidateQueries({ queryKey: queryKeys.bookJobs(bookId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not start generation"),
  });

  const book = bookQuery.data;
  const chapters = chaptersQuery.data?.items ?? [];
  const estimate = estimateQuery.data;
  const hasChapters = chapters.length > 0;
  const generated = chapters.filter((c) => c.status !== "pending").length;

  if (bookQuery.isLoading) return <Skeleton className="h-64 rounded-xl" />;
  if (!book) return null;

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Generate"
        description="Run the eight-agent pipeline to write, edit, fact-check, design and publish your book."
        actions={
          <StatusBadge meta={jobStatus(book.status === "ready" ? "succeeded" : book.status)} showDot={false} />
        }
      />

      {!hasChapters ? (
        <Alert variant="warning">
          <AlertDescription className="flex flex-wrap items-center gap-3">
            <span>Approve an outline first — the pipeline writes one chapter per planned chapter.</span>
            <Button size="sm" variant="outline" asChild>
              <Link href={`/books/${bookId}/outline`}>
                <Layers className="size-4" /> Go to outline
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            {activeJobId ? (
              <PipelineProgress
                jobId={activeJobId}
                onDone={(status) => {
                  queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
                  queryClient.invalidateQueries({ queryKey: queryKeys.chapters(bookId) });
                  queryClient.invalidateQueries({ queryKey: queryKeys.bookJobs(bookId) });
                  if (status === "succeeded") {
                    toast.success("Your book is ready!");
                    router.push(`/books/${bookId}/export`);
                  }
                }}
              />
            ) : (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Ready to write</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    {chapters.length} {pluralize(chapters.length, "chapter")} planned.{" "}
                    {generated > 0 && `${generated} already generated.`}
                  </p>
                  {estimate && (
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <Metric label="Estimated tokens" value={estimate.estimated_tokens.toLocaleString()} />
                      <Metric label="Estimated credits" value={estimate.estimated_credits.toLocaleString()} />
                    </div>
                  )}
                  {estimate && !estimate.affordable && (
                    <Alert variant="destructive">
                      <AlertDescription>
                        You have {estimate.user_balance.toLocaleString()} credits but this run needs
                        about {estimate.estimated_credits.toLocaleString()}.{" "}
                        <Link href="/billing" className="font-medium underline">
                          Top up credits
                        </Link>
                        .
                      </AlertDescription>
                    </Alert>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => start.mutate()}
                      disabled={start.isPending || (estimate ? !estimate.affordable : false)}
                    >
                      <Play className="size-4" />
                      {start.isPending ? "Starting…" : "Start full generation"}
                    </Button>
                    {generated > 0 && (
                      <Button
                        variant="outline"
                        onClick={() => start.mutate()}
                        disabled={start.isPending}
                      >
                        <RotateCcw className="size-4" /> Resume / regenerate
                      </Button>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Credits are charged once per run — retries and resumes never double-charge.
                  </p>
                </CardContent>
              </Card>
            )}

            {book.status === "failed" && (
              <Alert variant="destructive">
                <AlertDescription className="flex items-center gap-2">
                  <AlertTriangle className="size-4" />
                  The last run failed. Retry above or open a previous job to inspect the error.
                </AlertDescription>
              </Alert>
            )}
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Progress value={chapters.length ? (generated / chapters.length) * 100 : 0} />
                <p className="text-sm text-muted-foreground">
                  {generated}/{chapters.length} chapters written
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Recent runs</CardTitle>
              </CardHeader>
              <CardContent>
                {jobsQuery.isLoading ? (
                  <Skeleton className="h-20" />
                ) : (jobsQuery.data?.items.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground">No runs yet.</p>
                ) : (
                  <ul className="divide-y">
                    {jobsQuery.data!.items.slice(0, 6).map((job) => {
                      const meta = jobStatus(job.status);
                      return (
                        <li key={job.id} className="flex items-center justify-between gap-2 py-2.5">
                          <div>
                            <p className="text-sm font-medium capitalize">{job.type.replace("_", " ")}</p>
                            <p className="text-xs text-muted-foreground">
                              {relativeTime(job.created_at)}
                            </p>
                          </div>
                          <StatusBadge meta={meta} />
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-semibold">{value}</p>
    </div>
  );
}
