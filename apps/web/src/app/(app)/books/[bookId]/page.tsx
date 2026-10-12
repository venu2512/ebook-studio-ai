"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Download,
  FileText,
  Image as ImageIcon,
  Layers,
  PenLine,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { StatusBadge } from "@/components/app/status-badge";
import { EmptyState } from "@/components/app/empty-state";
import { booksApi, chaptersApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { bookStatus, chapterStatus } from "@/lib/status";
import { relativeTime } from "@/lib/format";
import { LANGUAGES } from "@ebook/shared";

export default function BookOverviewPage() {
  const { bookId } = useParams<{ bookId: string }>();

  const bookQuery = useQuery({
    queryKey: queryKeys.book(bookId),
    queryFn: () => booksApi.get(bookId),
  });
  const chaptersQuery = useQuery({
    queryKey: queryKeys.chapters(bookId),
    queryFn: () => chaptersApi.list(bookId),
  });

  if (bookQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (bookQuery.isError || !bookQuery.data) {
    return (
      <EmptyState
        icon={BookOpen}
        title="Book not found"
        description="It may have been deleted, or you don't have access to it."
        action={
          <Button asChild>
            <Link href="/dashboard">Back to dashboard</Link>
          </Button>
        }
      />
    );
  }

  const book = bookQuery.data;
  const meta = bookStatus(book.status);
  const chapters = chaptersQuery.data?.items ?? [];
  const done = chapters.filter((c) => c.status !== "pending" && c.status !== "failed").length;
  const progress = chapters.length ? Math.round((done / chapters.length) * 100) : 0;

  const cta = primaryAction(book.id, book.status);

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title={book.title}
        description={book.subtitle || book.topic}
        actions={
          <>
            <StatusBadge meta={meta} />
            {cta && (
              <Button asChild>
                <Link href={cta.href}>
                  <cta.icon className="size-4" /> {cta.label}
                </Link>
              </Button>
            )}
          </>
        }
      />

      {book.status === "failed" && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>
            Generation failed. Open the Generate tab to retry the failed step. You won&apos;t be
            charged twice.
          </AlertDescription>
        </Alert>
      )}

      {book.is_sensitive && (
        <Alert variant="warning" className="mb-6">
          <AlertDescription>
            This is a <strong>{book.category}</strong> book. A disclaimer page and extra
            fact-checking are applied automatically.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between text-base">
                <span>Progress</span>
                <span className="text-sm font-normal text-muted-foreground">
                  {done}/{chapters.length} chapters
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={progress} />
              {chapters.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No chapters yet. Generate and approve an outline to begin.
                </p>
              ) : (
                <ul className="divide-y">
                  {chapters.slice(0, 8).map((chapter) => {
                    const cs = chapterStatus(chapter.status);
                    return (
                      <li key={chapter.id} className="flex items-center justify-between gap-3 py-2.5">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">
                            {chapter.order_index + 1}. {chapter.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {chapter.word_count.toLocaleString()} / {chapter.target_word_count.toLocaleString()} words
                          </p>
                        </div>
                        <StatusBadge meta={cs} />
                      </li>
                    );
                  })}
                  {chapters.length > 8 && (
                    <li className="pt-3">
                      <Link
                        href={`/books/${book.id}/workspace`}
                        className="text-sm text-primary hover:underline"
                      >
                        View all {chapters.length} chapters →
                      </Link>
                    </li>
                  )}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardContent className="p-5">
              <div className="mx-auto mb-4 flex aspect-[5/8] max-w-[180px] items-center justify-center overflow-hidden rounded-lg bg-gradient-to-br from-primary/20 to-fuchsia-500/20">
                {book.cover_asset_id ? (
                  <span className="text-xs text-muted-foreground">Cover generated</span>
                ) : (
                  <ImageIcon className="size-8 text-muted-foreground/50" />
                )}
              </div>
              <Button variant="outline" className="w-full" asChild>
                <Link href={`/books/${book.id}/cover`}>
                  <ImageIcon className="size-4" /> Cover studio
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm">
              <Detail label="Category" value={book.category} />
              <Detail
                label="Language"
                value={LANGUAGES.find((l) => l.value === book.language)?.label ?? book.language}
              />
              <Detail label="Tone" value={book.tone} />
              <Detail label="Target" value={`${book.target_pages} pages · ${book.target_word_count.toLocaleString()} words`} />
              <Detail label="Words used" value={book.tokens_used.toLocaleString() + " tokens"} />
              <Detail label="Credits charged" value={book.credits_charged.toLocaleString()} />
              <Detail label="Updated" value={relativeTime(book.updated_at)} />
              {book.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {book.keywords.map((k) => (
                    <Badge key={k} variant="secondary">
                      {k}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium capitalize">{value}</span>
    </div>
  );
}

function primaryAction(bookId: string, status: string) {
  switch (status) {
    case "draft":
      return { href: `/books/${bookId}/outline?generate=1`, label: "Generate outline", icon: Sparkles };
    case "awaiting_approval":
      return { href: `/books/${bookId}/outline`, label: "Review outline", icon: Layers };
    case "planning":
      return { href: `/books/${bookId}/generate`, label: "Start writing", icon: PenLine };
    case "ready":
      return { href: `/books/${bookId}/export`, label: "Export", icon: Download };
    case "writing":
    case "editing":
    case "designing":
      return { href: `/books/${bookId}/generate`, label: "View progress", icon: Sparkles };
    default:
      return { href: `/books/${bookId}/workspace`, label: "Open workspace", icon: FileText };
  }
}
