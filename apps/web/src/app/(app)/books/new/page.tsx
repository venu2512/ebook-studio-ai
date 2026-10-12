"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/app/page-header";
import { booksApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import {
  bookCreateSchema,
  CATEGORIES,
  categoriesLabel,
  isSensitiveCategory,
  LANGUAGES,
  TONES,
  wordsForPages,
  type BookCreateValues,
} from "@ebook/shared";

const STEPS = ["Topic", "Audience", "Style", "Review"] as const;

export default function NewBookPage() {
  const router = useRouter();
  const [step, setStep] = React.useState(0);
  const [keywordsText, setKeywordsText] = React.useState("");

  const form = useForm<BookCreateValues>({
    resolver: zodResolver(bookCreateSchema),
    mode: "onTouched",
    defaultValues: {
      topic: "",
      title: "",
      audience: "General readers",
      category: "General",
      language: "en",
      tone: "conversational",
      target_pages: 20,
      style_guide: "",
      author_name: "",
      keywords: [],
      template: "classic",
    },
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors },
  } = form;

  const values = watch();

  const create = useMutation({
    mutationFn: (payload: BookCreateValues) =>
      booksApi.create({
        ...payload,
        title: payload.title || null,
        target_word_count: wordsForPages(payload.target_pages),
        keywords: keywordsText
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
      }),
    onSuccess: (book) => {
      toast.success("Book created — generating your outline");
      router.push(`/books/${book.id}/outline?generate=1`);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 422) {
        toast.error("Some details need fixing. Check the highlighted fields.");
      } else {
        toast.error(error instanceof Error ? error.message : "Could not create the book");
      }
    },
  });

  const STEP_FIELDS: (keyof BookCreateValues)[][] = [
    ["topic"],
    ["audience", "category"],
    ["language", "tone", "target_pages"],
    [],
  ];

  async function next() {
    const valid = await trigger(STEP_FIELDS[step], { shouldFocus: true });
    if (valid) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  function back() {
    setStep((s) => Math.max(s - 1, 0));
  }

  const words = wordsForPages(values.target_pages || 20);
  const sensitive = isSensitiveCategory(values.category);

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Create a new book"
        description="Answer a few questions and the team will research, plan and start writing."
      />

      {/* Stepper */}
      <ol className="mb-8 flex items-center gap-2">
        {STEPS.map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-2">
            <button
              type="button"
              onClick={() => i < step && setStep(i)}
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                i < step
                  ? "bg-primary text-primary-foreground"
                  : i === step
                    ? "bg-primary/15 text-primary ring-1 ring-primary"
                    : "bg-muted text-muted-foreground",
              )}
            >
              {i < step ? <Check className="size-3.5" /> : i + 1}
            </button>
            <span
              className={cn(
                "hidden text-sm sm:inline",
                i === step ? "font-medium text-foreground" : "text-muted-foreground",
              )}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="h-px flex-1 bg-border" />}
          </li>
        ))}
      </ol>

      <form onSubmit={handleSubmit((v) => create.mutate(v))} noValidate>
        <Card>
          <CardContent className="p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.2 }}
                className="space-y-5"
              >
                {step === 0 && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="topic">What is your book about?</Label>
                      <Textarea
                        id="topic"
                        rows={4}
                        placeholder="e.g. A practical guide to building a freelance writing business from scratch"
                        {...register("topic")}
                      />
                      {errors.topic && (
                        <p className="text-xs text-destructive">{errors.topic.message}</p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Be specific — the more direction you give, the sharper the outline.
                      </p>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="title">Working title (optional)</Label>
                        <Input id="title" placeholder="Leave blank to let the Planner name it" {...register("title")} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="author_name">Author name (optional)</Label>
                        <Input id="author_name" placeholder="Printed on the cover" {...register("author_name")} />
                      </div>
                    </div>
                  </>
                )}

                {step === 1 && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="audience">Who is it for?</Label>
                      <Input
                        id="audience"
                        placeholder="e.g. Aspiring freelancers with no writing experience"
                        {...register("audience")}
                      />
                      {errors.audience && (
                        <p className="text-xs text-destructive">{errors.audience.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select
                        value={values.category}
                        onValueChange={(v) => setValue("category", v, { shouldValidate: true })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Choose a category" />
                        </SelectTrigger>
                        <SelectContent>
                          {CATEGORIES.map((c) => (
                            <SelectItem key={c} value={c}>
                              {categoriesLabel(c)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {sensitive && (
                        <Alert variant="warning" className="mt-2">
                          <AlertDescription>
                            {values.category} is a sensitive category. A disclaimer page and extra
                            fact-checking will be added automatically.
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="keywords">Keywords (optional)</Label>
                      <Input
                        id="keywords"
                        placeholder="Comma separated, e.g. freelancing, copywriting, clients"
                        value={keywordsText}
                        onChange={(e) => setKeywordsText(e.target.value)}
                      />
                    </div>
                  </>
                )}

                {step === 2 && (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Language</Label>
                        <Select
                          value={values.language}
                          onValueChange={(v) => setValue("language", v, { shouldValidate: true })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {LANGUAGES.map((l) => (
                              <SelectItem key={l.value} value={l.value}>
                                {l.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="target_pages">Length: {values.target_pages} pages</Label>
                        <input
                          id="target_pages"
                          type="range"
                          min={6}
                          max={200}
                          step={2}
                          className="w-full accent-[hsl(var(--primary))]"
                          {...register("target_pages", { valueAsNumber: true })}
                        />
                        <p className="text-xs text-muted-foreground">
                          ≈ {words.toLocaleString()} words
                        </p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Tone</Label>
                      <div className="grid gap-2 sm:grid-cols-3">
                        {TONES.map((t) => (
                          <button
                            key={t.value}
                            type="button"
                            onClick={() => setValue("tone", t.value, { shouldValidate: true })}
                            className={cn(
                              "rounded-lg border p-3 text-left text-sm transition-colors",
                              values.tone === t.value
                                ? "border-primary bg-primary/5 ring-1 ring-primary"
                                : "hover:bg-accent",
                            )}
                          >
                            <span className="block font-medium">{t.label}</span>
                            <span className="text-xs text-muted-foreground">{t.hint}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="style_guide">Style guide (optional)</Label>
                      <Textarea
                        id="style_guide"
                        rows={3}
                        placeholder="Anything the writer should always or never do — terminology, examples to use, things to avoid."
                        {...register("style_guide")}
                      />
                    </div>
                  </>
                )}

                {step === 3 && (
                  <div className="space-y-4">
                    <div className="rounded-lg border bg-muted/30 p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <Sparkles className="size-4 text-primary" />
                        <span className="font-medium">Ready to plan</span>
                      </div>
                      <dl className="grid gap-3 text-sm sm:grid-cols-2">
                        <Summary label="Topic" value={values.topic} full />
                        <Summary label="Title" value={values.title || "Auto-generated"} />
                        <Summary label="Author" value={values.author_name || "—"} />
                        <Summary label="Audience" value={values.audience} />
                        <Summary label="Category" value={values.category} />
                        <Summary
                          label="Language"
                          value={LANGUAGES.find((l) => l.value === values.language)?.label ?? values.language}
                        />
                        <Summary
                          label="Tone"
                          value={TONES.find((t) => t.value === values.tone)?.label ?? values.tone}
                        />
                        <Summary
                          label="Length"
                          value={`${values.target_pages} pages · ${words.toLocaleString()} words`}
                        />
                      </dl>
                      {keywordsText && (
                        <div className="mt-4 flex flex-wrap gap-1.5">
                          {keywordsText
                            .split(",")
                            .map((k) => k.trim())
                            .filter(Boolean)
                            .map((k) => (
                              <Badge key={k} variant="secondary">
                                {k}
                              </Badge>
                            ))}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Next you&apos;ll review the generated outline before any chapters are written.
                      Outline generation costs a small number of credits, estimated before it runs.
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </CardContent>
        </Card>

        <div className="mt-6 flex items-center justify-between">
          <Button type="button" variant="ghost" onClick={back} disabled={step === 0}>
            <ArrowLeft className="size-4" /> Back
          </Button>
          {step < STEPS.length - 1 ? (
            <Button type="button" onClick={next}>
              Continue <ArrowRight className="size-4" />
            </Button>
          ) : (
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create & generate outline"}
              {!create.isPending && <Sparkles className="size-4" />}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

function Summary({
  label,
  value,
  full,
}: {
  label: string;
  value: string;
  full?: boolean;
}) {
  return (
    <div className={full ? "sm:col-span-2" : undefined}>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm">{value}</dd>
    </div>
  );
}
