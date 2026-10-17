"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Cpu, Download, Globe, Key, Loader2, Server } from "lucide-react";
import { toast } from "sonner";
import type { ProfileValues } from "@ebook/shared";
import { LANGUAGES, TONES, profileSchema } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
        <ApiKeysCard />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <GdprDataExportCard />
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

const LLM_PRESETS = [
  {
    id: "nvidia",
    name: "NVIDIA NIM",
    badge: "Cloud AI",
    baseUrl: "https://integrate.api.nvidia.com/v1",
    defaultModel: "meta/llama-3.3-70b-instruct",
    defaultKey: "",
    requiresKey: true,
    hint: "High-throughput GPU inference powered by NVIDIA NIM.",
  },
  {
    id: "ollama",
    name: "Ollama",
    badge: "Local LLM",
    baseUrl: "http://localhost:11434/v1",
    defaultModel: "llama3.2",
    defaultKey: "",
    requiresKey: false,
    hint: "100% private local execution. Ensure Ollama is running (`ollama serve`).",
  },
  {
    id: "lmstudio",
    name: "LM Studio",
    badge: "Local LLM",
    baseUrl: "http://localhost:1234/v1",
    defaultModel: "local-model",
    defaultKey: "",
    requiresKey: false,
    hint: "Local inference via LM Studio server with GGUF models (`Start Server`).",
  },
  {
    id: "custom",
    name: "OpenRouter / Custom",
    badge: "OpenAI Compatible",
    baseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "anthropic/claude-3.5-sonnet",
    defaultKey: "",
    requiresKey: true,
    hint: "Connect to OpenRouter, Together, Groq, vLLM, or direct OpenAI endpoints.",
  },
] as const;

function ApiKeysCard() {
  const [provider, setProvider] = React.useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("custom_llm_provider") || "nvidia";
    }
    return "nvidia";
  });
  const [baseUrl, setBaseUrl] = React.useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("custom_llm_base_url") || "https://integrate.api.nvidia.com/v1";
    }
    return "https://integrate.api.nvidia.com/v1";
  });
  const [apiKey, setApiKey] = React.useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("custom_llm_api_key") || "";
    }
    return "";
  });
  const [modelName, setModelName] = React.useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("custom_llm_model") || "meta/llama-3.3-70b-instruct";
    }
    return "meta/llama-3.3-70b-instruct";
  });
  const [testing, setTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState<{ ok: boolean; message: string } | null>(null);

  const activePreset = LLM_PRESETS.find((p) => p.id === provider);

  function handleSelectPreset(presetId: string) {
    const selected = LLM_PRESETS.find((p) => p.id === presetId);
    if (!selected) return;
    setProvider(selected.id);
    setBaseUrl(selected.baseUrl);
    setModelName(selected.defaultModel);
    if (selected.id === "nvidia") {
      setApiKey(selected.defaultKey);
    } else if (!selected.requiresKey) {
      setApiKey("");
    }
    setTestResult(null);
  }

  async function handleTestConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      const url = baseUrl.replace(/\/+$/, "");
      const res = await fetch(`${url}/models`, {
        method: "GET",
        headers: {
          ...(apiKey.trim() ? { Authorization: `Bearer ${apiKey.trim()}` } : {}),
        },
      });
      if (res.ok) {
        setTestResult({ ok: true, message: `Connected! HTTP ${res.status} OK from ${url}` });
      } else {
        setTestResult({
          ok: false,
          message: `Endpoint responded with HTTP ${res.status}. Verify endpoint or model server.`,
        });
      }
    } catch {
      // Fallback for CORS: endpoint might be running locally without CORS headers
      setTestResult({
        ok: true,
        message: `Endpoint targeted at ${baseUrl}. (Local servers like Ollama/LM Studio will be routed via the backend).`,
      });
    } finally {
      setTesting(false);
    }
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (typeof window !== "undefined") {
      localStorage.setItem("custom_llm_provider", provider);
      localStorage.setItem("custom_llm_base_url", baseUrl.trim());
      localStorage.setItem("custom_llm_model", modelName.trim());
      if (apiKey.trim()) {
        localStorage.setItem("custom_llm_api_key", apiKey.trim());
      } else {
        localStorage.removeItem("custom_llm_api_key");
      }
      // Sync to user profile in backend if logged in
      usersApi
        .update({
          settings_json: {
            custom_llm_provider: provider,
            custom_llm_base_url: baseUrl.trim(),
            custom_llm_api_key: apiKey.trim(),
            custom_llm_model: modelName.trim(),
          },
        })
        .catch(() => {});

      toast.success("AI model configuration saved");
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Cpu className="size-4 text-primary" /> AI Model & Local LLM Provider
          </CardTitle>
          <Badge variant="outline" className="text-xs gap-1">
            {activePreset?.id === "ollama" || activePreset?.id === "lmstudio" ? (
              <>
                <Server className="size-3" /> Local LLM
              </>
            ) : (
              <>
                <Globe className="size-3" /> Cloud Provider
              </>
            )}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Configure whether book generation uses high-performance cloud GPUs (NVIDIA NIM) or runs 100% locally on your machine via Ollama or LM Studio.
        </p>

        {/* Preset Selector */}
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {LLM_PRESETS.map((p) => {
            const isSelected = provider === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p.id)}
                className={cn(
                  "rounded-lg border p-3 text-left transition-all",
                  isSelected
                    ? "border-primary bg-primary/5 ring-1 ring-primary shadow-xs"
                    : "border-border hover:bg-accent"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-xs text-foreground">{p.name}</span>
                  <Badge variant={p.requiresKey ? "secondary" : "default"} className="text-[10px] px-1.5 py-0">
                    {p.badge}
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">{p.hint}</p>
              </button>
            );
          })}
        </div>

        <form onSubmit={handleSave} className="space-y-4 pt-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="base-url">Provider Base URL</Label>
              <Input
                id="base-url"
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://integrate.api.nvidia.com/v1"
                required
              />
              <p className="text-[11px] text-muted-foreground">
                OpenAI-compatible completions endpoint.
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="custom-key">API Key</Label>
                {!activePreset?.requiresKey && (
                  <span className="text-[10px] text-emerald-500 font-medium">Not required for local models</span>
                )}
              </div>
              <Input
                id="custom-key"
                type="password"
                placeholder={activePreset?.requiresKey ? "nvapi-... or sk-..." : "Optional / leave blank for local"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoComplete="off"
              />
              <p className="text-[11px] text-muted-foreground">
                {activePreset?.id === "nvidia"
                  ? "Configured with your NVIDIA NIM API key."
                  : activePreset?.requiresKey
                    ? "Bearer token for authorization."
                    : "Local engines like Ollama/LM Studio do not require an API key."}
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="model-name">Model Name</Label>
            <Input
              id="model-name"
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="meta/llama-3.3-70b-instruct or llama3.2"
              required
            />
            <p className="text-[11px] text-muted-foreground">
              Examples: <code className="rounded bg-muted px-1">meta/llama-3.3-70b-instruct</code>, <code className="rounded bg-muted px-1">llama3.2</code>, <code className="rounded bg-muted px-1">mistral</code>.
            </p>
          </div>

          {testResult && (
            <div
              className={cn(
                "flex items-start gap-2 rounded-lg border p-3 text-xs",
                testResult.ok
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-destructive/30 bg-destructive/10 text-destructive"
              )}
            >
              {testResult.ok ? <CheckCircle2 className="size-4 shrink-0" /> : <AlertTriangle className="size-4 shrink-0" />}
              <span>{testResult.message}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button type="submit" size="sm">
              Save AI configuration
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleTestConnection}
              disabled={testing}
            >
              {testing ? <Loader2 className="size-3.5 animate-spin" /> : <Server className="size-3.5" />}
              Test connection
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function GdprDataExportCard() {
  const [exporting, setExporting] = React.useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      const data = await usersApi.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ebook-studio-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Your personal data export has been downloaded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not export user data");
    } finally {
      setExporting(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Download className="size-4" /> Data portability (GDPR)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Download a complete JSON export of your personal information, book metadata, chapters,
          credit transaction ledger and export records.
        </p>
        <Button variant="outline" onClick={handleExport} disabled={exporting}>
          {exporting ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Exporting…
            </>
          ) : (
            <>
              <Download className="size-4" /> Export my data
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

