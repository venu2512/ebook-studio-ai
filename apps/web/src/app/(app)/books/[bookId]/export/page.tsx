"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookMarked, CheckCircle2, CheckSquare, Download, FileText, Loader2, Lock, ShoppingBag, Square, Trash2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

      <PublishingChecklists />
    </div>
  );
}

function PublishingChecklists() {
  const [kdpItems, setKdpItems] = React.useState<Record<string, boolean>>({
    epub: true,
    cover: true,
    title: false,
    desc: false,
    keywords: false,
    pricing: false,
  });

  const [gumroadItems, setGumroadItems] = React.useState<Record<string, boolean>>({
    bundle: true,
    cover: false,
    desc: false,
    pricing: false,
    email: false,
  });

  function toggleKdp(key: string) {
    setKdpItems((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function toggleGumroad(key: string) {
    setGumroadItems((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="mt-10">
      <div className="mb-4">
        <h2 className="font-serif text-xl font-semibold">Publishing checklists</h2>
        <p className="text-sm text-muted-foreground">
          Step-by-step readiness criteria for launching on Amazon KDP and Gumroad.
        </p>
      </div>

      <Tabs defaultValue="kdp" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="kdp" className="gap-2">
            <BookMarked className="size-4" /> Amazon KDP
          </TabsTrigger>
          <TabsTrigger value="gumroad" className="gap-2">
            <ShoppingBag className="size-4" /> Gumroad
          </TabsTrigger>
        </TabsList>

        <TabsContent value="kdp">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Amazon Kindle Direct Publishing (KDP) Checklist</span>
                <span className="text-xs font-normal text-muted-foreground">
                  {Object.values(kdpItems).filter(Boolean).length}/6 completed
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { key: "epub", label: "EPUB Format Validated", desc: "EPUB file generated passes schema structure and table of contents links check." },
                { key: "cover", label: "Cover Image Prepared", desc: "Recommended 2560 x 1600 px (1.6:1 ratio) high-resolution image in RGB color format." },
                { key: "title", label: "Metadata Consistency", desc: "Book title and subtitle exactly match interior title page and cover artwork." },
                { key: "desc", label: "Amazon Blurb & Description", desc: "Copy the HTML-formatted description with bullet points from the Marketing tab." },
                { key: "keywords", label: "7 Search Keywords & 2 BISAC Categories", desc: "Populate Amazon KDP backend keywords and categories using the generated Marketing kit." },
                { key: "pricing", label: "Pricing & Rights Configured", desc: "Select 70% royalty tier ($2.99–$9.99) and Worldwide distribution rights." },
              ].map((item) => (
                <div
                  key={item.key}
                  onClick={() => toggleKdp(item.key)}
                  className="flex items-start gap-3 rounded-lg border p-3 cursor-pointer hover:bg-accent/50 transition-colors"
                >
                  <button type="button" className="mt-0.5 text-primary">
                    {kdpItems[item.key] ? (
                      <CheckSquare className="size-4 text-primary" />
                    ) : (
                      <Square className="size-4 text-muted-foreground" />
                    )}
                  </button>
                  <div className="flex-1">
                    <p className={`text-sm font-medium ${kdpItems[item.key] ? "line-through text-muted-foreground" : ""}`}>
                      {item.label}
                    </p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="gumroad">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Gumroad & Payhip Independent Sale Checklist</span>
                <span className="text-xs font-normal text-muted-foreground">
                  {Object.values(gumroadItems).filter(Boolean).length}/5 completed
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { key: "bundle", label: "Multi-Format Deliverable Bundle", desc: "Export and upload all three files (PDF + EPUB + DOCX) so readers get their preferred format." },
                { key: "cover", label: "Product Banner & Square Thumbnail", desc: "1280 x 720 px banner cover art and 1:1 square thumbnail configured in Gumroad." },
                { key: "desc", label: "Sales Copy & Feature Bullets", desc: "Paste persuasive copy, reader promise, and key takeaways from the Marketing kit." },
                { key: "pricing", label: "Price & 'Pay What You Want'", desc: "Set fixed price (e.g. $9.99) and optionally enable 'Pay what you want' with a minimum price." },
                { key: "email", label: "Automated Thank-You Email Sequence", desc: "Configure Gumroad post-purchase email workflow using the 5-day email sequence from the Marketing tab." },
              ].map((item) => (
                <div
                  key={item.key}
                  onClick={() => toggleGumroad(item.key)}
                  className="flex items-start gap-3 rounded-lg border p-3 cursor-pointer hover:bg-accent/50 transition-colors"
                >
                  <button type="button" className="mt-0.5 text-primary">
                    {gumroadItems[item.key] ? (
                      <CheckSquare className="size-4 text-primary" />
                    ) : (
                      <Square className="size-4 text-muted-foreground" />
                    )}
                  </button>
                  <div className="flex-1">
                    <p className={`text-sm font-medium ${gumroadItems[item.key] ? "line-through text-muted-foreground" : ""}`}>
                      {item.label}
                    </p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

