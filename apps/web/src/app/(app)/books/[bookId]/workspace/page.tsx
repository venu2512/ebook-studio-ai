"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  History,
  RefreshCw,
  Save,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import type { AIAction, ChapterListItem } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { EmptyState } from "@/components/app/empty-state";
import { StatusBadge } from "@/components/app/status-badge";
import { chaptersApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { chapterStatus } from "@/lib/status";
import { TONES } from "@ebook/shared";
import { cn, pluralize } from "@/lib/utils";

const AI_ACTIONS: { action: AIAction; label: string }[] = [
  { action: "improve", label: "Improve" },
  { action: "rewrite", label: "Rewrite" },
  { action: "expand", label: "Expand" },
  { action: "shorten", label: "Shorten" },
];

export default function WorkspacePage() {
  const { bookId } = useParams<{ bookId: string }>();
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const chaptersQuery = useQuery({
    queryKey: queryKeys.chapters(bookId),
    queryFn: () => chaptersApi.list(bookId),
  });

  const chapters = React.useMemo(
    () => chaptersQuery.data?.items ?? [],
    [chaptersQuery.data],
  );

  React.useEffect(() => {
    if (!selectedId && chapters.length > 0) {
      const firstWithContent = chapters.find((c) => c.status !== "pending") ?? chapters[0];
      setSelectedId(firstWithContent.id);
    }
  }, [chapters, selectedId]);

  if (chaptersQuery.isLoading) {
    return (
      <div>
        <BookNav bookId={bookId} />
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (chapters.length === 0) {
    return (
      <div>
        <BookNav bookId={bookId} />
        <PageHeader title="Workspace" description="Edit and refine your chapters here." />
        <EmptyState
          icon={Wand2}
          title="No chapters yet"
          description="Generate and approve an outline, then run generation to create chapters."
        />
      </div>
    );
  }

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Workspace"
        description="Read, edit and polish each chapter. Nothing is saved until you save."
      />
      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <ChapterList
          chapters={chapters}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        {selectedId ? (
          <ChapterEditor key={selectedId} bookId={bookId} chapterId={selectedId} />
        ) : (
          <EmptyState title="Select a chapter" description="Choose a chapter from the list." />
        )}
      </div>
    </div>
  );
}

function ChapterList({
  chapters,
  selectedId,
  onSelect,
}: {
  chapters: ChapterListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Card className="h-fit lg:sticky lg:top-20">
      <CardContent className="max-h-[70vh] space-y-1 overflow-y-auto p-3">
        {chapters.map((chapter) => {
          const meta = chapterStatus(chapter.status);
          const active = chapter.id === selectedId;
          return (
            <button
              key={chapter.id}
              onClick={() => onSelect(chapter.id)}
              className={cn(
                "flex w-full flex-col gap-1 rounded-lg p-3 text-left transition-colors",
                active ? "bg-primary/10 ring-1 ring-primary/30" : "hover:bg-accent",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium">
                  {chapter.order_index + 1}. {chapter.title}
                </span>
                <span className={cn("size-1.5 shrink-0 rounded-full", meta.dot)} />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{meta.label}</span>
                <span>{chapter.word_count.toLocaleString()} words</span>
              </div>
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}

function ChapterEditor({ bookId, chapterId }: { bookId: string; chapterId: string }) {
  const queryClient = useQueryClient();
  const chapterQuery = useQuery({
    queryKey: queryKeys.chapter(chapterId),
    queryFn: () => chaptersApi.get(chapterId),
  });

  const chapter = chapterQuery.data;
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  const [tone, setTone] = React.useState("professional");
  const contentRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    if (chapter) {
      setTitle(chapter.title);
      setContent(chapter.content ?? "");
      setDirty(false);
    }
  }, [chapter]);

  const words = React.useMemo(
    () => content.trim().split(/\s+/).filter(Boolean).length,
    [content],
  );

  const save = useMutation({
    mutationFn: () => chaptersApi.update(chapterId, { title, content, create_version: true }),
    onSuccess: () => {
      setDirty(false);
      toast.success("Chapter saved");
      queryClient.invalidateQueries({ queryKey: queryKeys.chapter(chapterId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.chapters(bookId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.versions(chapterId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not save"),
  });

  const aiAction = useMutation({
    mutationFn: (payload: { action: AIAction; tone?: string }) =>
      chaptersApi.aiAction(chapterId, payload),
    onSuccess: (result) => {
      setContent(result.content);
      setDirty(true);
      toast.success("AI suggestion applied — save to keep it");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "AI action failed"),
  });

  const regenerate = useMutation({
    mutationFn: () =>
      chaptersApi.regenerate(chapterId, "Regenerate this chapter with the same brief."),
    onSuccess: () => {
      toast.success("Regeneration queued — watch the Generate tab");
      queryClient.invalidateQueries({ queryKey: queryKeys.chapters(bookId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not regenerate"),
  });

  const versionsQuery = useQuery({
    queryKey: queryKeys.versions(chapterId),
    queryFn: () => chaptersApi.versions(chapterId),
  });

  const restore = useMutation({
    mutationFn: (version: number) => chaptersApi.restore(chapterId, version),
    onSuccess: () => {
      toast.success("Version restored");
      queryClient.invalidateQueries({ queryKey: queryKeys.chapter(chapterId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.versions(chapterId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not restore"),
  });

  function autoResize(el: HTMLTextAreaElement | null) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.max(el.scrollHeight, 420)}px`;
  }

  if (chapterQuery.isLoading || !chapter) return <Skeleton className="h-96 rounded-xl" />;

  const flags = chapter.flags ?? [];
  const factChecks = chapter.fact_checks ?? [];
  const needsSource = factChecks.filter((f) => f.verdict === "needs_source");

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setDirty(true);
            }}
            className="max-w-md text-base font-medium"
          />
          <div className="flex items-center gap-2">
            <StatusBadge meta={chapterStatus(chapter.status)} />
            <span className="text-xs text-muted-foreground">
              v{chapter.current_version} · {words.toLocaleString()}/
              {chapter.target_word_count.toLocaleString()} words
            </span>
          </div>
        </div>

        {(flags.length > 0 || needsSource.length > 0) && (
          <Alert variant="warning">
            <AlertDescription>
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <div className="space-y-1">
                  {flags.slice(0, 3).map((f, i) => (
                    <p key={i} className="text-xs">
                      {String(f.message ?? f.type ?? "Flag")}
                    </p>
                  ))}
                  {needsSource.length > 0 && (
                    <p className="text-xs">
                      {needsSource.length} {pluralize(needsSource.length, "claim")} need a source.
                    </p>
                  )}
                </div>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {AI_ACTIONS.map((a) => (
            <Button
              key={a.action}
              variant="outline"
              size="sm"
              disabled={aiAction.isPending}
              onClick={() => aiAction.mutate({ action: a.action })}
            >
              <Sparkles className="size-3.5" /> {a.label}
            </Button>
          ))}
          <div className="flex items-center gap-1">
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger className="h-8 w-32 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TONES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              disabled={aiAction.isPending}
              onClick={() => aiAction.mutate({ action: "change_tone", tone })}
            >
              Change tone
            </Button>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <History className="size-3.5" /> Versions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Version history</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {(versionsQuery.data?.items.length ?? 0) === 0 ? (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">No versions yet</div>
                ) : (
                  versionsQuery.data!.items.map((v) => (
                    <DropdownMenuItem key={v.id} onSelect={() => restore.mutate(v.version)}>
                      <span className="flex-1">
                        v{v.version} · {v.source}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {v.word_count.toLocaleString()}w
                      </span>
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="outline"
              size="sm"
              disabled={regenerate.isPending}
              onClick={() => regenerate.mutate()}
            >
              <RefreshCw className="size-3.5" /> Regenerate
            </Button>
            <Button size="sm" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
              {dirty ? <Save className="size-3.5" /> : <Check className="size-3.5" />}
              {save.isPending ? "Saving…" : dirty ? "Save" : "Saved"}
            </Button>
          </div>
        </div>

        {aiAction.isPending && (
          <p className="flex items-center gap-2 text-xs text-primary">
            <Sparkles className="size-3.5 animate-pulse" /> The Editor is working on your chapter…
          </p>
        )}

        <Separator />

        <Textarea
          ref={(el) => {
            contentRef.current = el;
            autoResize(el);
          }}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setDirty(true);
            autoResize(e.target);
          }}
          placeholder="This chapter hasn't been written yet. Run generation to draft it, or write here."
          className="min-h-[420px] resize-none font-serif text-[15px] leading-7"
        />

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-destructive"
            onClick={() => {
              setContent("");
              setDirty(true);
            }}
          >
            Clear content
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
