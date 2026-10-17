"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, AlertTriangle, ArrowRight, Loader2, MailCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api/endpoints";

function VerifyEmailContent() {
  const params = useSearchParams();
  const tokenFromUrl = params.get("token") || "";

  const [token, setToken] = React.useState(tokenFromUrl);
  const [status, setStatus] = React.useState<"idle" | "loading" | "success" | "error">(
    tokenFromUrl ? "loading" : "idle",
  );
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const verifyToken = React.useCallback(async (tok: string) => {
    if (!tok.trim()) return;
    setStatus("loading");
    setErrorMessage(null);
    try {
      await authApi.verifyEmail(tok.trim());
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Invalid or expired verification token.",
      );
    }
  }, []);

  React.useEffect(() => {
    if (tokenFromUrl) {
      verifyToken(tokenFromUrl);
    }
  }, [tokenFromUrl, verifyToken]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-serif text-2xl font-bold">Verify your email</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Confirm your email address to unlock all features.
        </p>
      </div>

      {status === "loading" && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Loader2 className="size-10 animate-spin text-primary" />
          <p className="mt-4 text-sm font-medium">Verifying your email token…</p>
          <p className="mt-1 text-xs text-muted-foreground">This only takes a moment.</p>
        </div>
      )}

      {status === "success" && (
        <div className="rounded-xl border border-success/30 bg-success/5 p-6 text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-full bg-success/15 text-success">
            <CheckCircle2 className="size-6" />
          </div>
          <h2 className="mt-4 font-serif text-lg font-semibold">Email verified!</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your email has been successfully confirmed. You can now sign in to your account.
          </p>
          <Button asChild className="mt-6 w-full">
            <Link href="/login">
              Continue to sign in <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      )}

      {status === "error" && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-full bg-destructive/15 text-destructive">
            <AlertTriangle className="size-6" />
          </div>
          <h2 className="mt-4 font-serif text-lg font-semibold">Verification failed</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {errorMessage || "The link may be expired or already used."}
          </p>
          <div className="mt-6 space-y-3">
            <Button variant="outline" className="w-full" onClick={() => setStatus("idle")}>
              Try entering token manually
            </Button>
            <Button asChild variant="ghost" className="w-full">
              <Link href="/login">Return to sign in</Link>
            </Button>
          </div>
        </div>
      )}

      {status === "idle" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            verifyToken(token);
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="token">Verification token</Label>
            <Input
              id="token"
              placeholder="Paste verification token here…"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={!token.trim()}>
            <MailCheck className="size-4" /> Verify email
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Already verified?{" "}
            <Link href="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-sm text-muted-foreground">Loading verification…</div>}>
      <VerifyEmailContent />
    </React.Suspense>
  );
}
