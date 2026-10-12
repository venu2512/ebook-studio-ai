"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image as ImageIcon, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { coverApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";

export default function CoverPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = React.useState("");

  const coverQuery = useQuery({
    queryKey: queryKeys.cover(bookId),
    queryFn: () => coverApi.get(bookId),
  });

  const regenerate = useMutation({
    mutationFn: (value?: string) => coverApi.regenerate(bookId, value),
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
        description="Generate a cover direction, then refine it with a custom prompt."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            {coverQuery.isLoading ? (
              <Skeleton className="aspect-[5/8] w-full max-w-sm rounded-lg" />
            ) : cover?.url ? (
              <img
                src={cover.url}
                alt="Book cover"
                className="mx-auto max-h-[520px] rounded-lg border shadow-lg"
              />
            ) : (
              <div className="mx-auto flex aspect-[5/8] max-w-sm flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/30 text-muted-foreground">
                <ImageIcon className="size-8" />
                <p className="text-sm">No cover yet</p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Art direction</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="prompt">Custom prompt (optional)</Label>
                <Input
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g. Minimal geometric illustration, deep indigo and gold"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => regenerate.mutate(prompt || undefined)}
                  disabled={regenerate.isPending}
                >
                  <Sparkles className="size-4" />
                  {regenerate.isPending ? "Generating…" : cover?.url ? "Regenerate" : "Generate cover"}
                </Button>
                {cover?.url && (
                  <Button
                    variant="outline"
                    onClick={() => regenerate.mutate(undefined)}
                    disabled={regenerate.isPending}
                  >
                    <RefreshCw className="size-4" /> New idea
                  </Button>
                )}
              </div>
              {cover?.prompt && (
                <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">Direction: </span>
                  {cover.prompt}
                </div>
              )}
              {cover?.palette && Object.keys(cover.palette).length > 0 && (
                <div className="space-y-2">
                  <Label className="text-xs">Palette</Label>
                  <div className="flex gap-2">
                    {Object.entries(cover.palette).map(([name, color]) => (
                      <div key={name} className="flex items-center gap-1.5">
                        <span
                          className="size-6 rounded border"
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
            Covers render deterministically by default. Configure an image provider to generate
            photographic art.
          </p>
        </div>
      </div>
    </div>
  );
}
