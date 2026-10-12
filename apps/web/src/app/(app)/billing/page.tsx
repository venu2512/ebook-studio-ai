"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, CreditCard, ExternalLink, Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { CheckoutRequest } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/app/page-header";
import { billingApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { formatUsd } from "@/lib/format";
import { ApiError } from "@/lib/api/client";
import { PLAN_LABELS } from "@ebook/shared";

export default function BillingPage() {
  const summaryQuery = useQuery({
    queryKey: queryKeys.billingSummary,
    queryFn: () => billingApi.summary(),
  });
  const plansQuery = useQuery({ queryKey: queryKeys.plans, queryFn: () => billingApi.plans() });
  const packsQuery = useQuery({
    queryKey: queryKeys.creditPacks,
    queryFn: () => billingApi.creditPacks(),
  });

  const checkout = useMutation({
    mutationFn: (payload: CheckoutRequest) => billingApi.checkout(payload),
    onSuccess: (session) => {
      window.location.href = session.url;
    },
    onError: (e) => toast.error(checkoutMessage(e)),
  });

  const portal = useMutation({
    mutationFn: () => billingApi.portal(),
    onSuccess: (session) => {
      window.location.href = session.url;
    },
    onError: (e) => toast.error(checkoutMessage(e)),
  });

  const summary = summaryQuery.data;
  const plans = plansQuery.data ?? [];
  const packs = packsQuery.data ?? [];

  return (
    <div>
      <PageHeader
        title="Billing &amp; credits"
        description="Manage your plan and top up credits for book generation."
        actions={
          summary?.stripe_customer_id ? (
            <Button
              variant="outline"
              onClick={() => portal.mutate()}
              disabled={portal.isPending}
            >
              <ExternalLink className="size-4" /> Manage subscription
            </Button>
          ) : undefined
        }
      />

      {summary && !summary.billing_enabled && (
        <Alert variant="info" className="mb-6">
          <Sparkles />
          <AlertTitle>Billing is not configured</AlertTitle>
          <AlertDescription>
            This deployment runs without payments. Credits still work and are topped up by an
            administrator.
          </AlertDescription>
        </Alert>
      )}

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Stat
          label="Current plan"
          value={summary ? (PLAN_LABELS[summary.plan] ?? summary.plan) : "—"}
          loading={summaryQuery.isLoading}
        />
        <Stat
          label="Credit balance"
          value={summary ? summary.credits_balance.toLocaleString() : "—"}
          loading={summaryQuery.isLoading}
        />
        <Stat
          label="Monthly allowance"
          value={summary ? summary.monthly_allowance.toLocaleString() : "—"}
          loading={summaryQuery.isLoading}
        />
      </div>

      <section className="mb-10">
        <h2 className="mb-3 font-medium">Plans</h2>
        {plansQuery.isLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-64 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                className={plan.is_current ? "border-primary ring-1 ring-primary" : undefined}
              >
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center justify-between text-base">
                    <span>{plan.name}</span>
                    {plan.is_current && <Badge variant="success">Current</Badge>}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-2xl font-semibold">
                    {formatUsd(plan.price_usd_month, 0)}
                    <span className="text-sm font-normal text-muted-foreground"> / month</span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {plan.monthly_credits.toLocaleString()} credits / month
                  </p>
                  <ul className="space-y-2">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="mt-0.5 size-4 shrink-0 text-success" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={plan.is_current ? "outline" : "default"}
                    disabled={plan.is_current || !plan.stripe_price_id || checkout.isPending}
                    onClick={() =>
                      checkout.mutate({
                        kind: "subscription",
                        plan: plan.id as "pro" | "business",
                      })
                    }
                  >
                    {plan.is_current
                      ? "Current plan"
                      : plan.id === "free"
                        ? "Included"
                        : checkout.isPending
                          ? "Redirecting…"
                          : `Upgrade to ${plan.name}`}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-medium">Credit packs</h2>
        {packsQuery.isLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {packs.map((pack) => (
              <Card key={pack.id}>
                <CardContent className="flex flex-col gap-4 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{pack.credits.toLocaleString()} credits</p>
                      <p className="text-sm text-muted-foreground">{formatUsd(pack.price_usd)}</p>
                    </div>
                    <CreditCard className="size-5 text-muted-foreground" />
                  </div>
                  <Separator />
                  <Button
                    variant="secondary"
                    className="w-full"
                    disabled={!pack.stripe_price_id || checkout.isPending}
                    onClick={() =>
                      checkout.mutate({
                        kind: "credits",
                        pack: pack.id as "credits_100" | "credits_500" | "credits_2000",
                      })
                    }
                  >
                    <Plus className="size-4" /> Buy {pack.name}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        {loading ? (
          <Skeleton className="mt-2 h-7 w-24" />
        ) : (
          <p className="mt-1 text-2xl font-semibold">{value}</p>
        )}
      </CardContent>
    </Card>
  );
}

function checkoutMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "billing_disabled") {
      return "Billing is not configured on this deployment.";
    }
    if (error.code === "price_not_configured") {
      return "No Stripe price configured for that option.";
    }
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}
