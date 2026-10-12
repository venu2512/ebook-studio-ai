"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Check,
  FileText,
  Layers,
  PenLine,
  Search,
  Shield,
  Sparkles,
  Wand2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Logo } from "@/components/app/logo";
import { AGENT_DESCRIPTIONS, AGENT_KEYS, AGENT_LABELS } from "@ebook/shared";

const AGENT_ICONS = [Search, Layers, PenLine, Wand2, Shield, Sparkles, FileText, BookOpen];

const STEPS = [
  {
    title: "Describe your book",
    body: "Give a topic, audience, category, tone and length. That is all it takes to start.",
  },
  {
    title: "Review the blueprint",
    body: "The Researcher and Planner draft an outline with parts, chapters and word budgets. Edit anything.",
  },
  {
    title: "Watch the team write",
    body: "Live progress as each specialist works. Pause, retry a step, or restart at any time.",
  },
  {
    title: "Export and launch",
    body: "Download PDF, EPUB and DOCX, plus a cover and a full marketing kit.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
            <a href="#agents" className="transition-colors hover:text-foreground">The team</a>
            <a href="#pricing" className="transition-colors hover:text-foreground">Pricing</a>
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

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-[-10rem] h-[28rem] w-[28rem] -translate-x-1/2 rounded-full bg-primary/20 blur-3xl" />
          <div className="absolute right-0 top-40 h-72 w-72 rounded-full bg-fuchsia-500/10 blur-3xl" />
        </div>
        <div className="container flex flex-col items-center py-20 text-center lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="info" className="mb-6 gap-1.5 px-3 py-1">
              <Sparkles className="size-3.5" /> Eight AI specialists, one finished book
            </Badge>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="max-w-4xl text-balance font-serif text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
          >
            Turn a topic into a <span className="gradient-text">complete eBook</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground"
          >
            Research, outline, drafting, editing, fact-checking, design, publishing and marketing —
            handled end to end by an agent team you stay in control of.
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
              <Link href="/login">Sign in</Link>
            </Button>
          </motion.div>
          <p className="mt-4 text-xs text-muted-foreground">
            Free plan includes 100 credits. No card required.
          </p>

          {/* Book mock */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mt-16 w-full max-w-4xl"
          >
            <div className="rounded-2xl border bg-card p-2 shadow-2xl">
              <div className="rounded-xl bg-gradient-to-br from-primary/5 to-fuchsia-500/5 p-8">
                <div className="mx-auto grid max-w-2xl grid-cols-1 gap-4 text-left sm:grid-cols-2">
                  {AGENT_KEYS.map((key, i) => {
                    const Icon = AGENT_ICONS[i];
                    return (
                      <div
                        key={key}
                        className="flex items-start gap-3 rounded-lg border bg-background/80 p-4"
                      >
                        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                          <Icon className="size-4" />
                        </span>
                        <div>
                          <p className="text-sm font-medium">{AGENT_LABELS[key]}</p>
                          <p className="text-xs text-muted-foreground">{AGENT_DESCRIPTIONS[key]}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t bg-muted/30 py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">From idea to bookshelf in four steps</h2>
            <p className="mt-3 text-muted-foreground">
              You direct, the agents do the heavy lifting. Every stage is reviewable and editable.
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

      {/* Agents */}
      <section id="agents" className="py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">A studio, not a single prompt</h2>
            <p className="mt-3 text-muted-foreground">
              Each specialist has a focused job, a structured output and a quality gate.
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
                  <Card className="h-full">
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

      {/* Pricing */}
      <section id="pricing" className="border-t bg-muted/30 py-20">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-bold">Simple, credit-based pricing</h2>
            <p className="mt-3 text-muted-foreground">
              One credit is roughly 1,000 tokens of blended model cost. Estimate before you run.
            </p>
          </div>
          <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-3">
            {[
              { name: "Free", price: "$0", credits: "100 credits / mo", features: ["1 concurrent book", "PDF, EPUB & DOCX export", "Marketing kit"] },
              { name: "Pro", price: "$19", credits: "2,000 credits / mo", featured: true, features: ["Unlimited books", "Priority generation", "Cover regeneration", "Version history"] },
              { name: "Business", price: "$79", credits: "10,000 credits / mo", features: ["Everything in Pro", "Team-ready volume", "Bulk exports"] },
            ].map((plan) => (
              <Card
                key={plan.name}
                className={plan.featured ? "relative border-primary shadow-lg" : ""}
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
                  <ul className="mt-6 space-y-2 text-sm">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2">
                        <Check className="size-4 text-success" /> {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="mt-6 w-full"
                    variant={plan.featured ? "default" : "outline"}
                    asChild
                  >
                    <Link href="/register">Get started</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t py-10">
        <div className="container flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Logo />
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} eBook Studio AI. Built for authors who ship.
          </p>
        </div>
      </footer>
    </div>
  );
}
