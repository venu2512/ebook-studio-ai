"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Loader2, Lock, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { ExportFormat } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { StatusBadge } from "@/components/app/status-badge";
import { EmptyState } from "@/components/app/empty-state";
import { exportsApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { exportStatus } from "@/lib/status";
import { relativeTime } from "@/lib/format";
import { formatBytes } from "@/lib/utils";
import { EXPORT_FORMATS, PAGE_SIZES } from "@ebook/shared";
import { cn } from "@/lib/utils";

const FORMAT_META: Record<ExportFormat, { label: string; hint: string }> = {
  pdf: { label: "PDF", hint: "Print-ready, fixed layout" },
  epub: { label: "EPUB", hint: "Reflowable e-reader format" },
  docx: { label: "DOCX", hint: "Editable Word document" },
};

export default function ExportPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const queryClient = useQueryClient();
  const [format, setFormat] = React.useState<ExportFormat>("pdf");
  const [template, setTemplate] = React.useState("classic");
  const [pageSize, setPageSize] = React.useState("a5");
  const [frontMatter, setFrontMatter] = React.useState(true);
  const [toc, setToc] = React.useState(true);

  const templatesQuery = useQuery({
    queryKey: queryKeys.templates("interior"),
    queryFn: () => exportsApi.templates("interior"),
  });
  const exportsQuery = useQuery({
    queryKey: queryKeys.exports(bookId),
    queryFn: () => exportsApi.list(bookId),
  });

  const create = useMutation({
    mutationFn: () =>
      exportsApi.create(bookId, {
        format,
        template,
        page_size: pageSize as "a5" | "letter" | "a4",
        include_front_matter: frontMatter,
        include_toc: toc,
      }),
    onSuccess: () => {
      toast.success(`${format.toUpperCase()} export ready`);
      queryClient.invalidateQueries({ queryKey: queryKeys.exports(bookId) });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Export failed"),
  });

  async function download(exportId: string, fmt: string) {
    try {
      const result = await exportsApi.download(exportId);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : `Could not download ${fmt}`);
    }
  }

  const remove = useMutation({
    mutationFn: (exportId: string) => exportsApi.remove(exportId),
    onSuccess: () => {
      toast.success("Export deleted");
      queryClient.invalidateQueries({ queryKey: queryKeys.exports(bookId) });
    },
  });

  const exports = exportsQuery.data?.items ?? [];

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Export"
        description="Render your finished book to PDF, EPUB and DOCX."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">New export</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>Format</Label>
              <div className="grid gap-2 sm:grid-cols-3">
                {EXPORT_FORMATS.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setFormat(f)}
                    className={cn(
                      "rounded-lg border p-3 text-left transition-colors",
                      format === f ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:bg-accent",
                    )}
                  >
                    <span className="flex items-center gap-2 font-medium">
                      <FileText className="size-4" /> {FORMAT_META[f].label}
                    </span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {FORMAT_META[f].hint}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Interior template</Label>
                <Select value={template} onValueChange={setTemplate}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(templatesQuery.data ?? []).map((t) => (
                      <SelectItem key={t.slug} value={t.slug}>
                        <span className="flex items-center gap-2">
                          {t.name}
                          {t.is_premium && <Lock className="size-3 text-muted-foreground" />}
                        </span>
                      </SelectItem>
                    ))}
                    {templatesQuery.data?.length === 0 && (
                      <SelectItem value="classic">Classic</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Page size</Label>
                <Select value={pageSize} onValueChange={setPageSize}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PAGE_SIZES.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:gap-8">
              <label className="flex items-center gap-3">
                <Switch checked={frontMatter} onCheckedChange={setFrontMatter} />
                <span className="text-sm">Include front matter (title, copyright, disclaimer)</span>
              </label>
              <label className="flex items-center gap-3">
                <Switch checked={toc} onCheckedChange={setToc} />
                <span className="text-sm">Include table of contents</span>
              </label>
            </div>

            <Button onClick={() => create.mutate()} disabled={create.isPending}>
              {create.isPending ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
              {create.isPending ? "Rendering…" : `Export ${format.toUpperCase()}`}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Tips</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>PDF uses the high-fidelity renderer when available and falls back gracefully.</p>
            <p>EPUB reflows for Kindle, Apple Books and Kobo.</p>
            <p>DOCX opens in Word or Google Docs for final manual tweaks.</p>
            <Separator />
            <p className="text-xs">
              Exports render from the latest saved chapters. Save edits in the Workspace first.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <h2 className="mb-3 font-medium">Export history</h2>
        {exportsQuery.isLoading ? (
          <Skeleton className="h-24 rounded-xl" />
        ) : exports.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No exports yet"
            description="Your generated files will appear here, ready to download."
          />
        ) : (
          <Card>
            <CardContent className="divide-y p-0">
              {exports.map((exp) => {
                const meta = exportStatus(exp.status);
                return (
                  <div key={exp.id} className="flex items-center justify-between gap-3 p-4">
                    <div className="flex items-center gap-3">
                      <span className="grid size-9 place-items-center rounded-lg bg-muted font-semibold uppercase">
                        {exp.format}
                      </span>
                      <div>
                        <p className="text-sm font-medium">
                          {exp.format.toUpperCase()} · {exp.renderer ?? "renderer"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatBytes(exp.size_bytes)}
                          {exp.page_count ? ` · ${exp.page_count} pages` : ""} ·{" "}
                          {relativeTime(exp.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge meta={meta} />
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={exp.status !== "ready"}
                        onClick={() => download(exp.id, exp.format)}
                      >
                        <Download className="size-3.5" /> Download
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => remove.mutate(exp.id)}
                        aria-label="Delete export"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
