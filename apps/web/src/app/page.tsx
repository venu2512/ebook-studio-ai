"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Download,
  Eye,
  FileCheck,
  FileText,
  Layers,
  Palette,
  PenLine,
  Play,
  RotateCcw,
  Search,
  Shield,
  Sparkles,
  Wand2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Logo } from "@/components/app/logo";
import { cn } from "@/lib/utils";
import { AGENT_DESCRIPTIONS, AGENT_KEYS, AGENT_LABELS } from "@ebook/shared";

const AGENT_ICONS = [Search, Layers, PenLine, Wand2, Shield, Sparkles, FileText, BookOpen];

const STEPS = [
  {
    title: "1. Describe your book",
    body: "Enter your topic, audience, category, tone and target length. Enforce your custom style guide.",
  },
  {
    title: "2. Review the blueprint",
    body: "The Researcher and Planner construct a chapter outline with key points and word budgets. Reorder, add, or approve.",
  },
  {
    title: "3. Watch the team write",
    body: "Eight specialized agents research, draft, edit, and fact-check every chapter with live SSE updates.",
  },
  {
    title: "4. Export and publish",
    body: "Download validated PDF, EPUB 3, and DOCX files plus high-res cover art and Amazon KDP launch kits.",
  },
];

const DEMO_PRESETS = [
  {
    title: "The Solo Founder Playbook",
    topic: "Building and scaling a 7-figure digital business without hiring employees",
    category: "Business",
    tone: "Authoritative & Action-oriented",
    pages: 35,
    chapters: [
      { num: 1, title: "The Zero-Employee Leverage Model", status: "Fact-checked & approved" },
      { num: 2, title: "Automated Funnels & High-Margin Products", status: "Edited prose" },
      { num: 3, title: "The Relentless 4-Hour Daily Execution System", status: "Drafting" },
    ],
  },
  {
    title: "Deep Work & Cognitive Flow",
    topic: "A neuroscience-backed guide to reclaiming focus in a notifications world",
    category: "Self-Help",
    tone: "Conversational & Cited",
    pages: 28,
    chapters: [
      { num: 1, title: "The Attention Economy & Dopamine Traps", status: "Fact-checked & approved" },
      { num: 2, title: "Rituals for 90-Minute Unbroken Flow", status: "Fact-checked & approved" },
      { num: 3, title: "Digital Minimalism & Cognitive Rest", status: "Polishing" },
    ],
  },
  {
    title: "Production Agent Engineering",
    topic: "Architecting resilient, multi-agent AI systems with state machines",
    category: "Technology",
    tone: "Technical & Rigorous",
    pages: 50,
    chapters: [
      { num: 1, title: "Why Single-Prompt LLMs Fail at Scale", status: "Fact-checked & approved" },
      { num: 2, title: "State Machine Orchestration & Resumability", status: "Fact-checked & approved" },
      { num: 3, title: "Quality Gates, Output Schemas & Cost Budgets", status: "Drafting" },
    ],
  },
];

const SAMPLE_BOOKS = [
  {
    title: "The Solopreneur Operating System",
    subtitle: "From Zero to $50k/mo with AI and Micro-Assets",
    author: "Elena Rostova",
    category: "Business & Entrepreneurship",
    pages: 42,
    words: "10,500 words",
    rating: "4.9 ★★★★★",
    color: "from-blue-600 to-indigo-900",
    description:
      "A complete framework for modern creators building scalable product businesses. Includes verified growth formulas, case studies, and complete launch email sequences.",
    formats: ["PDF (A5)", "Kindle EPUB 3", "Editable DOCX"],
  },
  {
    title: "Mindful Clarity in High-Stress Roles",
    subtitle: "Evidence-Based Calm for Executives and Leaders",
    author: "Dr. Marcus Vance",
    category: "Health & Psychology (Disclaimed)",
    pages: 32,
    words: "8,200 words",
    rating: "5.0 ★★★★★",
    color: "from-emerald-600 to-teal-900",
    description:
      "Clinical neuroscience distilled into actionable executive routines. Includes mandatory medical disclaimer, 14 verified citations, and chapter reflection workbooks.",
    formats: ["PDF (US Letter)", "Kindle EPUB 3", "DOCX"],
  },
  {
    title: "Autonomous Agent Architectures",
    subtitle: "Building Production Multi-Agent Systems in Python",
    author: "Kiran Patel",
    category: "Technology & Software",
    pages: 64,
    words: "16,000 words",
    rating: "4.9 ★../../..",
    color: "from-purple-700 to-slate-950",
    description:
      "Comprehensive technical manual covering state machines, token budgeting, SSE progress streams, and idempotent LLM retries. Features formatted code blocks.",
    formats: ["PDF (A5)", "Kindle EPUB 3", "DOCX"],
  },
];

const FAQS = [
  {
    q: "How does the eight-agent pipeline actually work?",
    a: "Unlike single-prompt tools that dump generic text, eBook Studio AI uses an orchestrated state machine of 8 specialized agents: Researcher (sources & themes), Book Planner (outline & budgets), Writer (per-chapter drafting), Editor (flow & tone), Fact Checker (citation & claim audits), Designer (cover art & typography), Publisher (PDF/EPUB/DOCX layout engine), and Marketer (blurb & launch copy).",
  },
  {
    q: "Can I review and edit the book before and after writing?",
    a: "Yes! Human-in-the-loop is a foundational principle. You must review and approve the outline before any chapters are written. During or after generation, you can edit chapters in the rich markdown workspace, request targeted AI rewrites, or regenerate entire chapters with version history.",
  },
  {
    q: "Are citations and statistics verified for honesty?",
    a: "Yes. Our Fact Checker cross-references claims against research notes gathered by the Researcher. If a statistic or quote cannot be verified, it is prominently flagged in the workspace rather than silently fabricated. Sensitive topics (health, finance, legal) automatically include standard legal disclaimers.",
  },
  {
    q: "Are the exported files ready for Amazon KDP and Gumroad?",
    a: "Yes. The Publisher generates EPUB 3 files that pass official epubcheck validation, high-resolution PDFs in A5 or US Letter digest with beautiful front and back matter (copyright, TOC, author bio), and editable DOCX files. We also provide ready-to-use Amazon KDP and Gumroad launch checklists.",
  },
  {
    q: "What happens if a background worker restarts or an API fails?",
    a: "Every step is saved in our database and resumable. If a worker process restarts or an LLM call hits a rate limit, the orchestrator automatically picks up from the last completed chapter or step without losing any progress or double-charging your credits.",
  },
  {
    q: "Who owns the copyright and commercial rights?",
    a: "You retain 100% full commercial ownership of all books, covers, and marketing materials generated on eBook Studio AI. You can sell them on Amazon KDP, Gumroad, Payhip, or your own website with zero royalty splits.",
  },
];

export default function LandingPage() {
  const [activePreset, setActivePreset] = React.useState(0);
  const [activeSimAgent, setActiveSimAgent] = React.useState(2);
  const [simRunning, setSimRunning] = React.useState(false);
  const [openFaq, setOpenFaq] = React.useState<number | null>(0);

  const preset = DEMO_PRESETS[activePreset];

  // Simulator interval
  React.useEffect(() => {
    if (!simRunning) return;
    const interval = setInterval(() => {
      setActiveSimAgent((prev) => (prev + 1) % AGENT_KEYS.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [simRunning]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#demo" className="transition-colors hover:text-foreground">Interactive Demo</a>
            <a href="#how" className="transition-colors hover:text-foreground">How it Works</a>
            <a href="#agents" className="transition-colors hover:text-foreground">Agent Team</a>
            <a href="#samples" className="transition-colors hover:text-foreground">Sample Books</a>
            <a href="#pricing" className="transition-colors hover:text-foreground">Pricing</a>
            <a href="#faq" className="transition-colors hover:text-foreground">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/register">Start free</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-[-10rem] h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-primary/20 blur-3xl" />
          <div className="absolute right-0 top-40 h-80 w-80 rounded-full bg-fuchsia-500/10 blur-3xl" />
        </div>
        <div className="container flex flex-col items-center py-16 text-center lg:py-24">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="info" className="mb-6 gap-1.5 px-3 py-1">
              <Sparkles className="size-3.5" /> Eight Autonomous AI Specialists · One Production eBook
            </Badge>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="max-w-4xl text-balance font-serif text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
          >
            Turn a raw idea into a <span className="gradient-text">Kindle-ready eBook</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground"
          >
            Research, outline, chapter-by-chapter writing, editing, fact-checking, cover design,
            and publication-ready PDF, EPUB and DOCX exports — backed by human-in-the-loop control.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-8 flex flex-col gap-3 sm:flex-row"
          >
            <Button size="lg" asChild>
              <Link href="/register">
                Start writing free <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#demo">Watch Live Demo</a>
            </Button>
          </motion.div>
          <p className="mt-4 text-xs text-muted-foreground">
            Includes 100 free credits. No credit card required.
          </p>
        </div>
      </section>

      {/* Interactive Live Demo */}
      <section id="demo" className="border-t bg-muted/20 py-16">
        <div className="container max-w-5xl">
          <div className="text-center mb-10">
            <Badge variant="secondary" className="mb-2">Interactive Simulation</Badge>
            <h2 className="font-serif text-3xl font-bold">Experience the 8-Agent Pipeline</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Select a book concept below to watch the live state machine plan, write, and verify content.
            </p>
          </div>

          {/* Preset Buttons */}
          <div className="mb-6 flex flex-wrap justify-center gap-2">
            {DEMO_PRESETS.map((p, idx) => (
              <button
                key={p.title}
                type="button"
                onClick={() => {
                  setActivePreset(idx);
                  setActiveSimAgent(0);
                }}
                className={cn(
                  "rounded-full px-4 py-2 text-xs font-medium transition-all border",
                  activePreset === idx
                    ? "bg-primary text-primary-foreground border-primary shadow-sm"
                    : "bg-background text-muted-foreground hover:bg-accent border-border"
                )}
              >
                {p.title}
              </button>
            ))}
          </div>

          {/* Interactive Simulation Dashboard Card */}
          <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-foreground">{preset.title}</h3>
                  <Badge variant="outline">{preset.category}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{preset.topic}</p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={simRunning ? "destructive" : "default"}
                  onClick={() => setSimRunning(!simRunning)}
                  className="gap-1.5 text-xs"
                >
                  {simRunning ? <RotateCcw className="size-3.5" /> : <Play className="size-3.5" />}
                  {simRunning ? "Pause Simulation" : "Run Pipeline Sim"}
                </Button>
                <Button size="sm" variant="outline" asChild className="text-xs">
                  <Link href="/register">Try With Your Topic</Link>
                </Button>
              </div>
            </div>

            {/* Agent Progress Horizontal Carousel / Grid */}
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
              {AGENT_KEYS.map((key, i) => {
                const Icon = AGENT_ICONS[i];
                const isActive = activeSimAgent === i;
                const isPassed = activeSimAgent > i;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveSimAgent(i)}
                    className={cn(
                      "flex flex-col items-center rounded-lg border p-2.5 text-center transition-all",
                      isActive
                        ? "border-primary bg-primary/10 ring-2 ring-primary shadow-sm"
                        : isPassed
                          ? "border-success/30 bg-success/5 text-muted-foreground"
                          : "border-border bg-background/50 text-muted-foreground opacity-60"
                    )}
                  >
                    <div
                      className={cn(
                        "grid size-7 place-items-center rounded-full mb-1 text-xs",
                        isActive
                          ? "bg-primary text-primary-foreground animate-pulse"
                          : isPassed
                            ? "bg-success/20 text-success"
                            : "bg-muted text-muted-foreground"
                      )}
                    >
                      {isPassed ? <Check className="size-3.5" /> : <Icon className="size-3.5" />}
                    </div>
                    <span className="text-[11px] font-medium leading-tight truncate w-full">
                      {AGENT_LABELS[key]}
                    </span>
                    <span className="text-[9px] text-muted-foreground mt-0.5">
                      {isActive ? "Active" : isPassed ? "Done" : "Queued"}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Active Agent Output Inspector */}
            <div className="mt-6 rounded-xl border bg-muted/40 p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="flex size-2 rounded-full bg-primary animate-ping" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                    Live Agent Task: {AGENT_LABELS[AGENT_KEYS[activeSimAgent]]}
                  </span>
                </div>
                <Badge variant="secondary" className="text-[10px]">
                  Quality Gate: Active
                </Badge>
              </div>

              <div className="rounded-lg bg-background p-4 border font-mono text-xs text-foreground/90 space-y-2">
                <div className="text-muted-foreground text-[11px]">
                  &gt; Processing book &quot;{preset.title}&quot; · Target: {preset.pages} pages (~{preset.pages * 250} words)
                </div>
                {activeSimAgent === 0 && (
                  <p className="text-foreground">
                    ✓ Found 6 high-authority sources on {preset.category}. Competitor gap analysis complete. Extracted key statistics and claim references.
                  </p>
                )}
                {activeSimAgent === 1 && (
                  <p className="text-foreground">
                    ✓ Blueprint synthesized: 8 balanced chapters with word budgets summing within 4% of target. Reader promise verified.
                  </p>
                )}
                {activeSimAgent === 2 && (
                  <p className="text-foreground">
                    ✓ Drafting Chapter 3 in {preset.tone} tone. Injected concrete case study. Word count: 1,420 words (within 5% budget).
                  </p>
                )}
                {activeSimAgent === 3 && (
                  <p className="text-foreground">
                    ✓ Editor pass complete: Flesch-Kincaid grade 8.4 met. Removed redundant adjectives, trimmed passive voice, tightened transitions.
                  </p>
                )}
                {activeSimAgent === 4 && (
                  <p className="text-foreground">
                    ✓ Verified 5 citations against research notes. 0 unverified claims. Added required domain disclaimer header.
                  </p>
                )}
                {activeSimAgent === 5 && (
                  <p className="text-foreground">
                    ✓ Design palette assigned. Interior typography: Source Serif 4 + Inter. Generated high-res cover art prompt.
                  </p>
                )}
                {activeSimAgent === 6 && (
                  <p className="text-foreground">
                    ✓ Document assembly: Table of contents links linked. Epubcheck 3.0 passed. Ready for PDF and DOCX compilation.
                  </p>
                )}
                {activeSimAgent === 7 && (
                  <p className="text-foreground">
                    ✓ Marketing kit created: Amazon KDP bullet points, 7 search keywords, Gumroad sales copy, and 3-part launch email sequence.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t bg-muted/30 py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">From concept to bookstore in four steps</h2>
            <p className="mt-3 text-muted-foreground">
              You direct, the agents execute. Every stage is inspectable, editable, and resumable.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <Card className="h-full">
                  <CardContent className="p-6">
                    <span className="mb-4 grid size-9 place-items-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                      {i + 1}
                    </span>
                    <h3 className="font-semibold">{step.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{step.body}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Agents Showcase */}
      <section id="agents" className="py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">A full publishing house of specialized agents</h2>
            <p className="mt-3 text-muted-foreground">
              Each specialist has strict JSON schemas, domain prompt bibles, and automated quality gates.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {AGENT_KEYS.map((key, i) => {
              const Icon = AGENT_ICONS[i];
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, scale: 0.96 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: i * 0.04 }}
                >
                  <Card className="h-full hover:border-primary/50 transition-colors">
                    <CardContent className="p-6">
                      <span className="mb-3 grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="size-5" />
                      </span>
                      <h3 className="font-semibold">{AGENT_LABELS[key]}</h3>
                      <p className="mt-1.5 text-sm text-muted-foreground">
                        {AGENT_DESCRIPTIONS[key]}
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Sample Books Showcase */}
      <section id="samples" className="border-t bg-muted/20 py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <Badge variant="secondary" className="mb-2">Real Output Quality</Badge>
            <h2 className="font-serif text-3xl font-bold">Books generated with eBook Studio AI</h2>
            <p className="mt-3 text-muted-foreground">
              See what real authors produce in minutes across non-fiction, business, and technical genres.
            </p>
          </div>

          <div className="mt-12 grid gap-8 lg:grid-cols-3">
            {SAMPLE_BOOKS.map((book) => (
              <Card key={book.title} className="overflow-hidden flex flex-col justify-between">
                <div>
                  {/* Mock Book Cover Header */}
                  <div className={cn("p-6 text-white bg-gradient-to-br flex flex-col justify-between min-h-[180px]", book.color)}>
                    <div>
                      <Badge className="bg-white/20 text-white border-none text-[10px] mb-2">{book.category}</Badge>
                      <h3 className="font-serif text-xl font-bold leading-tight">{book.title}</h3>
                      <p className="text-xs text-white/80 mt-1">{book.subtitle}</p>
                    </div>
                    <div className="text-xs text-white/70 font-mono mt-4">By {book.author}</div>
                  </div>

                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground border-b pb-3">
                      <span>{book.pages} pages · {book.words}</span>
                      <span className="text-amber-500 font-semibold">{book.rating}</span>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {book.description}
                    </p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {book.formats.map((fmt) => (
                        <Badge key={fmt} variant="secondary" className="text-[10px]">
                          {fmt}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </div>

                <div className="p-6 pt-0">
                  <Button variant="outline" size="sm" className="w-full gap-2 text-xs" asChild>
                    <Link href="/register">
                      Create Similar Book <ArrowRight className="size-3.5" />
                    </Link>
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t bg-muted/30 py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">Predictable, credit-based pricing</h2>
            <p className="mt-3 text-muted-foreground">
              Credits represent blended LLM token budgets. Guaranteed cost: retrying or resuming a step never charges twice.
            </p>
          </div>
          <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-3">
            {[
              {
                name: "Free",
                price: "$0",
                credits: "100 credits / mo",
                features: ["1 concurrent book", "Full 8-agent pipeline", "PDF, EPUB & DOCX export", "Marketing kit"],
              },
              {
                name: "Pro",
                price: "$19",
                credits: "2,000 credits / mo",
                featured: true,
                features: [
                  "Unlimited books",
                  "Priority worker execution",
                  "AI cover art regeneration",
                  "Chapter version history",
                  "Custom LLM API keys",
                ],
              },
              {
                name: "Business",
                price: "$79",
                credits: "10,000 credits / mo",
                features: [
                  "Everything in Pro",
                  "Large-volume token budgets",
                  "Bulk chapter operations",
                  "White-glove format assistance",
                ],
              },
            ].map((plan) => (
              <Card
                key={plan.name}
                className={plan.featured ? "relative border-primary shadow-xl ring-1 ring-primary" : ""}
              >
                {plan.featured && (
                  <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">Most popular</Badge>
                )}
                <CardContent className="p-6">
                  <h3 className="font-semibold">{plan.name}</h3>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-sm text-muted-foreground">/mo</span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{plan.credits}</p>
                  <ul className="mt-6 space-y-2.5 text-sm">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2">
                        <Check className="size-4 text-emerald-500 shrink-0" /> {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="mt-6 w-full"
                    variant={plan.featured ? "default" : "outline"}
                    asChild
                  >
                    <Link href="/register">Get started free</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="border-t py-20">
        <div className="container max-w-3xl">
          <div className="text-center mb-12">
            <h2 className="font-serif text-3xl font-bold">Frequently Asked Questions</h2>
            <p className="mt-2 text-muted-foreground">
              Everything you need to know about publishing eBooks with AI.
            </p>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div
                  key={faq.q}
                  className="rounded-xl border bg-card transition-colors overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    className="flex w-full items-center justify-between p-5 text-left font-medium text-foreground hover:bg-muted/30"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      className={cn(
                        "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
                        isOpen && "rotate-180"
                      )}
                    />
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className="border-t px-5 pb-5 pt-3 text-sm text-muted-foreground leading-relaxed">
                          {faq.a}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12 bg-background">
        <div className="container flex flex-col items-center justify-between gap-6 sm:flex-row">
          <Logo />
          <div className="flex flex-wrap items-center gap-6 text-xs text-muted-foreground">
            <a href="#how" className="hover:text-foreground">How it Works</a>
            <a href="#demo" className="hover:text-foreground">Live Demo</a>
            <a href="#samples" className="hover:text-foreground">Sample Books</a>
            <a href="#pricing" className="hover:text-foreground">Pricing</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
            <Link href="/login" className="hover:text-foreground">Sign In</Link>
          </div>
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} eBook Studio AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
