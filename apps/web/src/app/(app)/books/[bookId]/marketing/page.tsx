"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, Megaphone, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { MarketingKit } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { PageHeader } from "@/components/app/page-header";
import { BookNav } from "@/components/app/book-nav";
import { EmptyState } from "@/components/app/empty-state";
import { CopyButton } from "@/components/app/copy-button";
import { marketingApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { ApiError } from "@/lib/api/client";

export default function MarketingPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const queryClient = useQueryClient();

  const kitQuery = useQuery({
    queryKey: queryKeys.marketing(bookId),
    queryFn: () => marketingApi.get(bookId),
    retry: false,
  });

  const generate = useMutation({
    mutationFn: () => marketingApi.regenerate(bookId),
    onSuccess: (kit) => {
      queryClient.setQueryData(queryKeys.marketing(bookId), kit);
      toast.success("Marketing kit ready");
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : "Could not generate the marketing kit"),
  });

  const notGenerated =
    kitQuery.error instanceof ApiError && kitQuery.error.code === "marketing_not_found";
  const kit = kitQuery.data;

  return (
    <div>
      <BookNav bookId={bookId} />
      <PageHeader
        title="Marketing kit"
        description="Your blurb, keywords, launch posts and email sequence — generated from the finished book."
        actions={
          <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
            {generate.isPending ? (
              <RefreshCw className="size-4 animate-spin" />
            ) : kit ? (
              <RefreshCw className="size-4" />
            ) : (
              <Sparkles className="size-4" />
            )}
            {generate.isPending ? "Writing…" : kit ? "Regenerate" : "Generate kit"}
          </Button>
        }
      />

      {kitQuery.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40 rounded-xl" />
          <Skeleton className="h-40 rounded-xl" />
        </div>
      ) : !kit ? (
        <EmptyState
          icon={Megaphone}
          title={notGenerated ? "No marketing kit yet" : "Could not load the marketing kit"}
          description={
            notGenerated
              ? "Generate your blurb, keywords and launch copy once the book is written."
              : "Something went wrong fetching the kit. You can try generating it again."
          }
          action={
            <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
              <Sparkles className="size-4" />
              {generate.isPending ? "Writing…" : "Generate kit"}
            </Button>
          }
        />
      ) : (
        <MarketingKitView kit={kit} />
      )}
    </div>
  );
}

function MarketingKitView({ kit }: { kit: MarketingKit }) {
  const blurb = [kit.description, kit.short_description].filter(Boolean).join("\n\n");

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span>Book description</span>
            <CopyButton value={blurb} label="Copy blurb" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {kit.short_description && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Short blurb
              </p>
              <p className="mt-1 text-sm">{kit.short_description}</p>
            </div>
          )}
          {kit.description && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Full description
              </p>
              <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
                {kit.description}
              </p>
            </div>
          )}
          {kit.bullet_points.length > 0 && (
            <>
              <Separator />
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  What readers will learn
                </p>
                <ul className="mt-2 space-y-1.5">
                  {kit.bullet_points.map((point, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <span className="text-primary">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Discovery &amp; keywords</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <KeywordGroup label="Keywords" values={kit.keywords} variant="secondary" />
          <KeywordGroup label="Categories" values={kit.categories} variant="muted" />
          <KeywordGroup label="Amazon KDP categories" values={kit.kdp_categories} variant="muted" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Launch content</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="social">
            <TabsList>
              <TabsTrigger value="social">
                Social posts ({kit.social_posts.length})
              </TabsTrigger>
              <TabsTrigger value="email">
                Email sequence ({kit.email_sequence.length})
              </TabsTrigger>
              <TabsTrigger value="bio">Author bio</TabsTrigger>
            </TabsList>

            <TabsContent value="social" className="space-y-3">
              {kit.social_posts.length === 0 ? (
                <p className="text-sm text-muted-foreground">No social posts generated.</p>
              ) : (
                kit.social_posts.map((post, i) => (
                  <div key={i} className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <Badge variant="secondary" className="capitalize">
                        {post.platform}
                      </Badge>
                      <CopyButton value={post.text} label="Copy" />
                    </div>
                    <p className="whitespace-pre-line text-sm">{post.text}</p>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="email" className="space-y-3">
              {kit.email_sequence.length === 0 ? (
                <p className="text-sm text-muted-foreground">No email sequence generated.</p>
              ) : (
                kit.email_sequence.map((step, i) => (
                  <div key={i} className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 font-medium">
                        <Mail className="size-4 text-muted-foreground" />
                        Day {step.day}: {step.subject}
                      </span>
                      <CopyButton
                        value={`Subject: ${step.subject}\n\n${step.body}`}
                        label="Copy"
                      />
                    </div>
                    <p className="whitespace-pre-line text-sm text-muted-foreground">{step.body}</p>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="bio">
              {kit.author_bio ? (
                <div className="rounded-lg border p-4">
                  <div className="mb-2 flex justify-end">
                    <CopyButton value={kit.author_bio} label="Copy bio" />
                  </div>
                  <p className="whitespace-pre-line text-sm">{kit.author_bio}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No author bio generated.</p>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

function KeywordGroup({
  label,
  values,
  variant,
}: {
  label: string;
  values: string[];
  variant: "secondary" | "muted";
}) {
  if (values.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {values.map((value) => (
          <Badge key={value} variant={variant}>
            {value}
          </Badge>
        ))}
      </div>
    </div>
  );
}
