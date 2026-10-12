"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { resetPasswordSchema, type ResetPasswordValues } from "@ebook/shared";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirm_password: "" },
  });

  useEffect(() => {
    if (!token) toast.error("This reset link is missing its token.");
  }, [token]);

  async function onSubmit(values: ResetPasswordValues) {
    if (!token) {
      toast.error("Invalid reset link.");
      return;
    }
    try {
      await authApi.resetPassword({ token, new_password: values.password });
      setDone(true);
      toast.success("Password updated");
      setTimeout(() => router.replace("/login"), 1500);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Could not reset your password.";
      toast.error(message);
    }
  }

  if (done) {
    return (
      <div className="text-center">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-success/15 text-success">
          <CheckCircle2 className="size-6" />
        </div>
        <h1 className="font-serif text-2xl font-bold">Password updated</h1>
        <p className="mt-2 text-sm text-muted-foreground">Redirecting you to sign in…</p>
        <Button className="mt-6 w-full" asChild>
          <Link href="/login">Go to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-serif text-2xl font-bold">Choose a new password</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick something strong you haven&apos;t used before.
        </p>
      </div>

      {!token && (
        <Alert variant="warning" className="mb-4">
          <AlertDescription>
            This link is missing its reset token. Request a new email.
          </AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div className="space-y-2">
          <Label htmlFor="password">New password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            {...register("password")}
          />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            {...register("confirm_password")}
          />
          {errors.confirm_password && (
            <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
          )}
        </div>
        <Button type="submit" className="w-full" disabled={isSubmitting || !token}>
          {isSubmitting && <Spinner />} Update password
        </Button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="h-64" />}>
      <ResetForm />
    </Suspense>
  );
}
