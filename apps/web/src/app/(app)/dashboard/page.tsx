"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BookOpen, CheckCircle2, Circle, MoreVertical, PlusCircle, Search, Sparkles, Trash2, X } from "lucide-react";

import { toast } from "sonner";
import type { BookWithProgress } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/app/page-header";
import { EmptyState } from "@/components/app/empty-state";
import { StatusBadge } from "@/components/app/status-badge";
import { booksApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { bookStatus } from "@/lib/status";
import { relativeTime } from "@/lib/format";
import { cn, pluralize } from "@/lib/utils";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "awaiting_approval", label: "Awaiting review" },
  { value: "writing", label: "Writing" },
  { value: "ready", label: "Ready" },
  { value: "failed", label: "Failed" },
];

export default function DashboardPage() {
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [debounced, setDebounced] = React.useState("");

  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const params = { search: debounced || undefined, status: status || undefined, limit: 60 };
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.books({ search: debounced, status }),
    queryFn: () => booksApi.list(params),
  });

  const books = data?.items ?? [];
  const totalWords = books.reduce((sum, b) => sum + b.target_word_count, 0);

  return (
    <div>
      <PageHeader
        title="Your books"
        description="Every project in one place. Pick up where you left off or start something new."
        actions={
          <Button asChild>
            <Link href="/books/new">
              <PlusCircle className="size-4" /> New book
            </Link>
          </Button>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Stat label="Books" value={data?.total ?? 0} />
        <Stat label="Planned words" value={totalWords.toLocaleString()} />
        <Stat
          label="Ready to export"
          value={books.filter((b) => b.status === "ready").length}
        />
      </div>

      <OnboardingChecklist books={books} />


      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title, topic or category…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <Button
              key={f.value || "all"}
              variant={status === f.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatus(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      ) : books.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={debounced || status ? "No books match your filters" : "No books yet"}
          description={
            debounced || status
              ? "Try a different search or clear the filters."
              : "Create your first book and watch the agent team bring it to life."
          }
          action={
            !debounced && !status ? (
              <Button asChild>
                <Link href="/books/new">
                  <PlusCircle className="size-4" /> Create a book
                </Link>
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("");
                  setStatus("");
                }}
              >
                Clear filters
              </Button>
            )
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {books.map((book, i) => (
            <BookCard key={book.id} book={book} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

function BookCard({ book, index }: { book: BookWithProgress; index: number }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const meta = bookStatus(book.status);

  const remove = useMutation({
    mutationFn: () => booksApi.remove(book.id),
    onSuccess: () => {
      toast.success("Book deleted");
      queryClient.invalidateQueries({ queryKey: ["books"] });
    },
    onError: (e: Error) => toast.error(e.message || "Could not delete the book"),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.03, 0.3) }}
    >
      <Card className="group h-full overflow-hidden transition-shadow hover:shadow-md">
        <Link href={`/books/${book.id}`} className="block">
          <div
            className={cn(
              "relative flex h-28 items-end bg-gradient-to-br p-4",
              book.cover_asset_id
                ? "from-primary/50 to-fuchsia-500/40"
                : "from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800",
            )}
          >
            <div className="absolute right-3 top-3">
              <StatusBadge meta={meta} />
            </div>
            <p className="line-clamp-2 font-serif text-lg font-semibold text-foreground/90">
              {book.title}
            </p>
          </div>
        </Link>
        <CardContent className="space-y-3 p-4">
          <div className="flex items-center justify-between gap-2">
            <p className="line-clamp-1 text-xs text-muted-foreground">
              {book.category} · {pluralize(book.chapter_count, "chapter")} ·{" "}
              {book.target_pages} pages
            </p>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm" aria-label="Book actions">
                  <MoreVertical className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => router.push(`/books/${book.id}`)}>
                  <BookOpen className="size-4" /> Open
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive"
                  onSelect={(e) => {
                    e.preventDefault();
                    setConfirmOpen(true);
                  }}
                >
                  <Trash2 className="size-4" /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {book.completed_chapters}/{book.chapter_count} chapters
              </span>
              <span>{book.progress_pct}%</span>
            </div>
            <Progress value={book.progress_pct} />
          </div>
          <p className="text-xs text-muted-foreground">Updated {relativeTime(book.updated_at)}</p>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete “{book.title}”?</DialogTitle>
            <DialogDescription>
              This soft-deletes the book. Generated chapters and exports are kept recoverable for a
              short time.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
            >
              Delete book
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}

function OnboardingChecklist({ books }: { books: BookWithProgress[] }) {
  const [dismissed, setDismissed] = React.useState(false);

  const hasCreatedBook = books.length > 0;
  const hasOutline = books.some((b) =>
    ["awaiting_approval", "writing", "editing", "designing", "ready"].includes(b.status),
  );
  const hasGeneratedChapters = books.some((b) => b.completed_chapters > 0 || b.status === "ready");
  const hasExported = books.some((b) => b.status === "ready");

  const completedCount = [hasCreatedBook, hasOutline, hasGeneratedChapters, hasExported].filter(
    Boolean,
  ).length;

  if (dismissed || (hasCreatedBook && hasExported)) {
    return null;
  }

  return (
    <Card className="mb-6 border-primary/30 bg-gradient-to-r from-primary/5 via-fuchsia-500/5 to-transparent">
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="grid size-7 place-items-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="size-4" />
            </span>
            <h3 className="font-medium text-sm sm:text-base">Quick start checklist ({completedCount}/4)</h3>
          </div>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Dismiss checklist"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex items-center gap-2.5 rounded-lg border bg-background/80 p-2.5 text-xs">
            {hasCreatedBook ? (
              <CheckCircle2 className="size-4 text-success shrink-0" />
            ) : (
              <Circle className="size-4 text-muted-foreground shrink-0" />
            )}
            <span className={hasCreatedBook ? "line-through text-muted-foreground" : "font-medium"}>
              1. Create a book
            </span>
          </div>

          <div className="flex items-center gap-2.5 rounded-lg border bg-background/80 p-2.5 text-xs">
            {hasOutline ? (
              <CheckCircle2 className="size-4 text-success shrink-0" />
            ) : (
              <Circle className="size-4 text-muted-foreground shrink-0" />
            )}
            <span className={hasOutline ? "line-through text-muted-foreground" : "font-medium"}>
              2. Approve the outline
            </span>
          </div>

          <div className="flex items-center gap-2.5 rounded-lg border bg-background/80 p-2.5 text-xs">
            {hasGeneratedChapters ? (
              <CheckCircle2 className="size-4 text-success shrink-0" />
            ) : (
              <Circle className="size-4 text-muted-foreground shrink-0" />
            )}
            <span className={hasGeneratedChapters ? "line-through text-muted-foreground" : "font-medium"}>
              3. Run generation
            </span>
          </div>

          <div className="flex items-center gap-2.5 rounded-lg border bg-background/80 p-2.5 text-xs">
            {hasExported ? (
              <CheckCircle2 className="size-4 text-success shrink-0" />
            ) : (
              <Circle className="size-4 text-muted-foreground shrink-0" />
            )}
            <span className={hasExported ? "line-through text-muted-foreground" : "font-medium"}>
              4. Download exports
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


