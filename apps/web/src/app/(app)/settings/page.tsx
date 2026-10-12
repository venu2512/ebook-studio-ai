"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { ProfileValues } from "@ebook/shared";
import { LANGUAGES, TONES, profileSchema } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/app/page-header";
import { useAuth } from "@/lib/auth/auth-provider";
import { usersApi } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/client";
import { queryKeys } from "@/lib/query/keys";
import { relativeTime, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <PageHeader title="Settings" description="Manage your profile, defaults and account." />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <ProfileForm />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Email" value={user?.email ?? "—"} />
            <Row label="Plan" value={user?.plan ?? "—"} valueClassName="capitalize" />
            <Row label="Role" value={user?.role ?? "—"} valueClassName="capitalize" />
            <Row label="Credits" value={user ? user.credits_balance.toLocaleString() : "—"} />
            <Row label="Verified" value={user?.is_verified ? "Yes" : "No"} />
            <Row label="Member since" value={shortDate(user?.created_at)} />
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <CreditHistory />
        <DangerZone />
      </div>
    </div>
  );
}

function ProfileForm() {
  const { user, refresh } = useAuth();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name ?? "",
      default_language: user?.default_language ?? "en",
      default_tone: user?.default_tone ?? "",
    },
  });

  React.useEffect(() => {
    if (user) {
      reset({
        full_name: user.full_name ?? "",
        default_language: user.default_language,
        default_tone: user.default_tone ?? "",
      });
    }
  }, [user, reset]);

  const save = useMutation({
    mutationFn: (values: ProfileValues) =>
      usersApi.update({
        full_name: values.full_name || null,
        default_language: values.default_language ?? null,
        default_tone: values.default_tone || null,
      }),
    onSuccess: async () => {
      toast.success("Profile saved");
      await refresh();
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
    onError: (e: Error) => toast.error(e.message || "Could not save your profile"),
  });

  if (!user) return <Skeleton className="h-48 rounded-lg" />;

  return (
    <form
      onSubmit={handleSubmit((values) => save.mutate(values))}
      className="space-y-4"
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="full_name">Name</Label>
        <Input id="full_name" placeholder="Ada Lovelace" {...register("full_name")} />
        {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="default_language">Default language</Label>
          <select
            id="default_language"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            {...register("default_language")}
          >
            {LANGUAGES.map((language) => (
              <option key={language.value} value={language.value}>
                {language.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="default_tone">Default tone</Label>
          <select
            id="default_tone"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            {...register("default_tone")}
          >
            <option value="">No preference</option>
            {TONES.map((tone) => (
              <option key={tone.value} value={tone.value}>
                {tone.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting || save.isPending || !isDirty}>
          {(isSubmitting || save.isPending) && <Loader2 className="size-4 animate-spin" />}
          Save changes
        </Button>
        {!isDirty && <span className="text-xs text-muted-foreground">No unsaved changes</span>}
      </div>
    </form>
  );
}

function Row({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: React.ReactNode;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("truncate font-medium", valueClassName)}>{value}</span>
    </div>
  );
}

function CreditHistory() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.transactions(),
    queryFn: () => usersApi.transactions(),
  });
  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Credit history</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32 rounded-lg" />
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No credit activity yet.</p>
        ) : (
          <ul className="divide-y">
            {items.map((tx) => (
              <li key={tx.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium capitalize">
                    {tx.description || tx.reason}
                  </p>
                  <p className="text-xs text-muted-foreground">{relativeTime(tx.created_at)}</p>
                </div>
                <span
                  className={cn(
                    "text-sm font-semibold tabular-nums",
                    tx.amount >= 0 ? "text-success" : "text-destructive",
                  )}
                >
                  {tx.amount >= 0 ? "+" : ""}
                  {tx.amount.toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function DangerZone() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [password, setPassword] = React.useState("");

  const deleteAccount = useMutation({
    mutationFn: () => usersApi.deleteAccount(password),
    onSuccess: () => {
      toast.success("Your account has been deleted");
      tokenStore.clear();
      queryClient.clear();
      router.replace("/");
    },
    onError: (e: Error) => toast.error(e.message || "Could not delete your account"),
  });

  return (
    <Card className="border-destructive/30">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base text-destructive">
          <AlertTriangle className="size-4" /> Danger zone
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert variant="destructive">
          <AlertTitle>Delete account</AlertTitle>
          <AlertDescription>
            Permanently removes your account, books and exports. This cannot be undone.
          </AlertDescription>
        </Alert>
        <Button variant="destructive" onClick={() => setOpen(true)}>
          Delete my account
        </Button>
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              Enter your password to confirm. All books and exports will be removed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Password</Label>
            <Input
              id="confirm-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!password || deleteAccount.isPending}
              onClick={() => deleteAccount.mutate()}
            >
              {deleteAccount.isPending && <Loader2 className="size-4 animate-spin" />}
              Delete forever
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
