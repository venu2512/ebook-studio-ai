"use client";

import * as React from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, ChevronUp, GripVertical, Plus, Save, Sparkles, Trash2 } from "lucide-react";

import { toast } from "sonner";
import type { Outline, OutlineChapter, OutlineStructure } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { EmptyState } from "@/components/app/empty-state";
import { PipelineProgress } from "@/components/app/pipeline-progress";
import { ApiError } from "@/lib/api/client";
import { outlineApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";

function chaptersOf(structure: OutlineStructure): OutlineChapter[] {
  return structure.parts.flatMap((p) => p.chapters);
}

function OutlineContent() {
  const { bookId } = useParams<{ bookId: string }>();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const autoGenerate = params.get("generate") === "1";

  const [jobId, setJobId] = React.useState<string | null>(null);
  const autoStarted = React.useRef(false);

  const outlineQuery = useQuery({
    queryKey: queryKeys.outline(bookId),
    queryFn: () => outlineApi.get(bookId),
    retry: false,
  });

  const outlineMissing =
    outlineQuery.isError &&
    outlineQuery.error instanceof ApiError &&
    outlineQuery.error.code === "outline_not_found";

  const generate = useMutation({
    mutationFn: () => outlineApi.generate(bookId, { reuse_research: true }),
    onSuccess: (job) => {
      setJobId(job.id);
      toast.success("Outline generation started");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not start generation"),
  });

  // Auto-start when arriving from the wizard or with ?generate=1.
  React.useEffect(() => {
    if (autoGenerate && outlineMissing && !autoStarted.current && !generate.isPending) {
      autoStarted.current = true;
      generate.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoGenerate, outlineMissing]);

  const generating = Boolean(jobId);

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Outline"
        description="Review and shape the blueprint before any chapters are written."
        actions={
          <Button
            variant="outline"
            onClick={() => generate.mutate()}
            disabled={generate.isPending || generating}
          >
            <Sparkles className="size-4" /> Regenerate
          </Button>
        }
      />

      {generating && (
        <div className="mb-6">
          <PipelineProgress
            jobId={jobId!}
            title="Planning your book"
            onDone={(status) => {
              setJobId(null);
              if (status === "succeeded") {
                queryClient.invalidateQueries({ queryKey: queryKeys.outline(bookId) });
                queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
                toast.success("Outline ready to review");
              }
            }}
          />
        </div>
      )}

      {outlineQuery.isLoading ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : outlineMissing ? (
        <EmptyState
          icon={Sparkles}
          title="No outline yet"
          description="Run the Researcher and Planner to draft a structured outline you can edit."
          action={
            <Button onClick={() => generate.mutate()} disabled={generate.isPending || generating}>
              <Sparkles className="size-4" /> Generate outline
            </Button>
          }
        />
      ) : outlineQuery.data ? (
        <OutlineEditor bookId={bookId} outline={outlineQuery.data} />
      ) : null}
    </div>
  );
}

function OutlineEditor({ bookId, outline }: { bookId: string; outline: Outline }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [structure, setStructure] = React.useState<OutlineStructure>(() =>
    structuredClone(outline.structure),
  );
  const [dirty, setDirty] = React.useState(false);

  const totalWords = chaptersOf(structure).reduce((s, c) => s + (c.word_budget || 0), 0);
  const approved = Boolean(outline.approved_at);

  function update(updater: (draft: OutlineStructure) => void) {
    setStructure((prev) => {
      const next = structuredClone(prev);
      updater(next);
      return next;
    });
    setDirty(true);
  }

  function moveChapter(partIndex: number, fromIdx: number, toIdx: number) {
    if (toIdx < 0 || toIdx >= structure.parts[partIndex].chapters.length) return;
    update((s) => {
      const [item] = s.parts[partIndex].chapters.splice(fromIdx, 1);
      s.parts[partIndex].chapters.splice(toIdx, 0, item);
    });
  }


  const save = useMutation({
    mutationFn: () =>
      outlineApi.update(bookId, {
        structure,
        title: structure.title,
        subtitle: structure.subtitle ?? null,
        reader_promise: structure.reader_promise,
      }),
    onSuccess: () => {
      setDirty(false);
      toast.success("Outline saved");
      queryClient.invalidateQueries({ queryKey: queryKeys.outline(bookId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not save the outline"),
  });

  const approve = useMutation({
    mutationFn: async () => {
      if (dirty) {
        await outlineApi.update(bookId, {
          structure,
          title: structure.title,
          subtitle: structure.subtitle ?? null,
          reader_promise: structure.reader_promise,
        });
      }
      return outlineApi.approve(bookId);
    },
    onSuccess: (result) => {
      toast.success(`Approved — ${result.chapter_count} chapters ready to write`);
      queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.chapters(bookId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.outline(bookId) });
      router.push(`/books/${bookId}/generate`);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not approve the outline"),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Title & positioning</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="o-title">Title</Label>
              <Input
                id="o-title"
                value={structure.title ?? ""}
                onChange={(e) => update((s) => void (s.title = e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="o-subtitle">Subtitle</Label>
              <Input
                id="o-subtitle"
                value={structure.subtitle ?? ""}
                onChange={(e) => update((s) => void (s.subtitle = e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="o-promise">Reader promise</Label>
              <Textarea
                id="o-promise"
                rows={2}
                value={structure.reader_promise ?? ""}
                onChange={(e) => update((s) => void (s.reader_promise = e.target.value))}
              />
            </div>
            {structure.title_options && structure.title_options.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">Alternatives:</span>
                {structure.title_options.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => update((s) => void (s.title = t))}
                    className="rounded-full border px-3 py-1 text-xs transition-colors hover:bg-accent"
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {structure.parts.map((part, partIndex) => (
          <Card key={partIndex}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2">
                <Input
                  value={part.title}
                  onChange={(e) =>
                    update((s) => void (s.parts[partIndex].title = e.target.value))
                  }
                  className="max-w-xs font-medium"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() =>
                    update((s) => {
                      s.parts.splice(partIndex, 1);
                    })
                  }
                >
                  <Trash2 className="size-4" /> Remove part
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {part.chapters.map((chapter, chapterIndex) => (
                <div
                  key={chapterIndex}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("text/plain", `${partIndex}:${chapterIndex}`);
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const raw = e.dataTransfer.getData("text/plain");
                    if (raw) {
                      const [pIdx, cIdx] = raw.split(":").map(Number);
                      if (pIdx === partIndex && cIdx !== chapterIndex) {
                        moveChapter(partIndex, cIdx, chapterIndex);
                      }
                    }
                  }}
                  className="rounded-lg border p-4 bg-background transition-shadow hover:shadow-sm"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className="cursor-grab active:cursor-grabbing p-1 text-muted-foreground hover:text-foreground">
                      <GripVertical className="size-4" />
                    </span>
                    <Input
                      value={chapter.title}
                      onChange={(e) =>
                        update(
                          (s) => void (s.parts[partIndex].chapters[chapterIndex].title = e.target.value),
                        )
                      }
                      placeholder="Chapter title"
                      className="font-medium"
                    />
                    <div className="flex items-center gap-0.5">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        disabled={chapterIndex === 0}
                        onClick={() => moveChapter(partIndex, chapterIndex, chapterIndex - 1)}
                        title="Move chapter up"
                        aria-label="Move chapter up"
                      >
                        <ChevronUp className="size-3.5" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        disabled={chapterIndex === part.chapters.length - 1}
                        onClick={() => moveChapter(partIndex, chapterIndex, chapterIndex + 1)}
                        title="Move chapter down"
                        aria-label="Move chapter down"
                      >
                        <ChevronDown className="size-3.5" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() =>
                          update((s) => {
                            s.parts[partIndex].chapters.splice(chapterIndex, 1);
                          })
                        }
                        title="Remove chapter"
                        aria-label="Remove chapter"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>

                  <Textarea
                    rows={2}
                    value={chapter.summary}
                    placeholder="Summary of what this chapter covers"
                    className="mb-2"
                    onChange={(e) =>
                      update(
                        (s) => void (s.parts[partIndex].chapters[chapterIndex].summary = e.target.value),
                      )
                    }
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Label className="text-xs text-muted-foreground">Word budget</Label>
                      <Input
                        type="number"
                        min={0}
                        className="h-8 w-28"
                        value={chapter.word_budget}
                        onChange={(e) =>
                          update(
                            (s) =>
                              void (s.parts[partIndex].chapters[chapterIndex].word_budget =
                                Number(e.target.value) || 0),
                          )
                        }
                      />
                    </div>
                    <Input
                      className="h-8 flex-1"
                      placeholder="Key points (comma separated)"
                      value={chapter.key_points.join(", ")}
                      onChange={(e) =>
                        update(
                          (s) =>
                            void (s.parts[partIndex].chapters[chapterIndex].key_points = e.target.value
                              .split(",")
                              .map((k) => k.trim())
                              .filter(Boolean)),
                        )
                      }
                    />
                  </div>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  update((s) => {
                    s.parts[partIndex].chapters.push({
                      title: "New chapter",
                      summary: "",
                      key_points: [],
                      word_budget: 2000,
                    });
                  })
                }
              >
                <Plus className="size-4" /> Add chapter
              </Button>
            </CardContent>
          </Card>
        ))}

        <Button
          variant="outline"
          onClick={() =>
            update((s) => {
              s.parts.push({
                title: `Part ${String.fromCharCode(65 + s.parts.length)}`,
                chapters: [],
              });
            })
          }
        >
          <Plus className="size-4" /> Add part
        </Button>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Version" value={`v${outline.version}`} />
            <Row label="Parts" value={structure.parts.length} />
            <Row label="Chapters" value={chaptersOf(structure).length} />
            <Row label="Total words" value={totalWords.toLocaleString()} />
            <Row
              label="Status"
              value={
                approved ? (
                  <Badge variant="success">Approved</Badge>
                ) : (
                  <Badge variant="warning">Awaiting review</Badge>
                )
              }
            />
            <Separator />
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                onClick={() => save.mutate()}
                disabled={!dirty || save.isPending}
              >
                <Save className="size-4" /> {save.isPending ? "Saving…" : "Save changes"}
              </Button>
              <Button onClick={() => approve.mutate()} disabled={approve.isPending}>
                <CheckCircle2 className="size-4" />
                {approve.isPending ? "Approving…" : "Approve & start writing"}
              </Button>
              {approved && !dirty && (
                <Button variant="secondary" onClick={() => router.push(`/books/${bookId}/generate`)}>
                  Continue to generation
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {dirty && (
          <Alert variant="info">
            <AlertDescription>
              You have unsaved edits. Approving will save them first.
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium capitalize">{value}</span>
    </div>
  );
}

export default function OutlinePage() {
  return (
    <React.Suspense
      fallback={
        <div className="space-y-6 p-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <OutlineContent />
    </React.Suspense>
  );
}
