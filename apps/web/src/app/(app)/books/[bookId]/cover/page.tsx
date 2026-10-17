"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Image as ImageIcon, Palette, RefreshCw, Sparkles, Type } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { coverApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";

const COVER_TEMPLATES = [
  { value: "classic", label: "Classic Typography" },
  { value: "bold_modern", label: "Bold Modern" },
  { value: "minimalist", label: "Minimalist Editorial" },
  { value: "framed", label: "Elegant Border" },
];

const COVER_FONTS = [
  { value: "serif", label: "Classic Serif (Georgia)" },
  { value: "sans", label: "Modern Sans (Helvetica)" },
  { value: "display", label: "Playfair Display" },
  { value: "mono", label: "Technical Mono" },
];

export default function CoverPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = React.useState("");
  const [template, setTemplate] = React.useState("classic");
  const [font, setFont] = React.useState("serif");
  const [thumbnailMode, setThumbnailMode] = React.useState(false);
  const [customPrimary, setCustomPrimary] = React.useState("#1e293b");
  const [customAccent, setCustomAccent] = React.useState("#f59e0b");

  const coverQuery = useQuery({
    queryKey: queryKeys.cover(bookId),
    queryFn: () => coverApi.get(bookId),
  });

  const regenerate = useMutation({
    mutationFn: (value?: string) => {
      const fullPrompt = [
        value || "",
        `Template style: ${template}`,
        `Typography: ${font}`,
        `Palette: primary ${customPrimary}, accent ${customAccent}`,
      ]
        .filter(Boolean)
        .join(". ");
      return coverApi.regenerate(bookId, fullPrompt);
    },
    onSuccess: (cover) => {
      queryClient.setQueryData(queryKeys.cover(bookId), cover);
      toast.success("Cover regenerated");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Could not generate the cover"),
  });

  const cover = coverQuery.data;

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Cover studio"
        description="Design your cover art, select typography, pick palettes, and verify thumbnail legibility."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => setThumbnailMode((prev) => !prev)}
            className="gap-2"
          >
            <Eye className="size-4" />
            {thumbnailMode ? "Standard view" : "Thumbnail view (Amazon preview)"}
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Live Preview Card */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Live Preview</CardTitle>
              <span className="text-xs text-muted-foreground">
                {thumbnailMode ? "Thumbnail test size (100×150 px)" : "Full cover view (500×750 px)"}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center p-6">
            {coverQuery.isLoading ? (
              <Skeleton className="aspect-[5/8] w-full max-w-sm rounded-lg" />
            ) : cover?.url ? (
              <div
                className={`transition-all duration-300 flex flex-col items-center justify-center ${
                  thumbnailMode ? "w-28 p-1 border-2 border-primary/40 rounded-md bg-muted/40" : "w-full max-w-sm"
                }`}
              >
                <img
                  src={cover.url}
                  alt="Book cover"
                  className={`mx-auto rounded-lg border shadow-lg object-contain transition-all duration-300 ${
                    thumbnailMode ? "max-h-40" : "max-h-[520px]"
                  }`}
                />
                {thumbnailMode && (
                  <p className="mt-2 text-[10px] text-center text-muted-foreground">
                    Title must remain legible at this scale
                  </p>
                )}
              </div>
            ) : (
              <div className="mx-auto flex aspect-[5/8] max-w-sm flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/30 text-muted-foreground">
                <ImageIcon className="size-8" />
                <p className="text-sm">No cover yet</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Controls Card */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Palette className="size-4" /> Cover options &amp; style
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Template layout</Label>
                  <Select value={template} onValueChange={setTemplate}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COVER_TEMPLATES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-1.5">
                    <Type className="size-3.5" /> Typography font
                  </Label>
                  <Select value={font} onValueChange={setFont}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COVER_FONTS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>
                          {f.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Color accents</Label>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={customPrimary}
                      onChange={(e) => setCustomPrimary(e.target.value)}
                      className="size-8 cursor-pointer rounded border p-0.5 bg-background"
                      title="Primary background/text color"
                    />
                    <span className="text-xs text-muted-foreground">Base tone</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={customAccent}
                      onChange={(e) => setCustomAccent(e.target.value)}
                      className="size-8 cursor-pointer rounded border p-0.5 bg-background"
                      title="Accent highlight color"
                    />
                    <span className="text-xs text-muted-foreground">Accent</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="prompt">Art direction prompt (optional)</Label>
                <Input
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g. Minimal geometric illustration, deep indigo and gold"
                />
              </div>

              <div className="flex flex-wrap gap-2 pt-2">
                <Button
                  onClick={() => regenerate.mutate(prompt || undefined)}
                  disabled={regenerate.isPending}
                >
                  <Sparkles className="size-4" />
                  {regenerate.isPending ? "Generating…" : cover?.url ? "Regenerate cover" : "Generate cover"}
                </Button>
                {cover?.url && (
                  <Button
                    variant="outline"
                    onClick={() => regenerate.mutate(undefined)}
                    disabled={regenerate.isPending}
                  >
                    <RefreshCw className="size-4" /> New variation
                  </Button>
                )}
              </div>

              {cover?.prompt && (
                <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">Active direction: </span>
                  {cover.prompt}
                </div>
              )}

              {cover?.palette && Object.keys(cover.palette).length > 0 && (
                <div className="space-y-2">
                  <Label className="text-xs">Generated Palette</Label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(cover.palette).map(([name, color]) => (
                      <div key={name} className="flex items-center gap-1.5">
                        <span
                          className="size-6 rounded border shadow-sm"
                          style={{ backgroundColor: color }}
                        />
                        <span className="text-xs text-muted-foreground capitalize">{name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          <p className="text-xs text-muted-foreground">
            Covers render deterministically by default with typography overlays. Configure an image provider in settings to generate photorealistic or custom illustrations.
          </p>
        </div>
      </div>
    </div>
  );
}
