"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Coins, Search, Shield } from "lucide-react";
import { toast } from "sonner";
import type { AdminJob, AdminUser, AdminUserUpdate, AgentCostRow } from "@ebook/shared";
import { AGENT_LABELS, PLAN_LABELS, type AgentKey } from "@ebook/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import { EmptyState } from "@/components/app/empty-state";
import { StatusBadge } from "@/components/app/status-badge";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { jobStatus } from "@/lib/status";
import { absoluteTime, formatUsd, humanize, relativeTime } from "@/lib/format";
import { formatNumber } from "@/lib/utils";
import { useAuth } from "@/lib/auth/auth-provider";

const JOB_FILTERS = [
  { value: "", label: "All" },
  { value: "running", label: "Running" },
  { value: "queued", label: "Queued" },
  { value: "succeeded", label: "Succeeded" },
  { value: "failed", label: "Failed" },
];

export default function AdminPage() {
  const { isAdmin, isLoading } = useAuth();

  if (isLoading) return <Skeleton className="h-64 rounded-xl" />;

  if (!isAdmin) {
    return (
      <EmptyState
        icon={Shield}
        title="Administrators only"
        description="You don't have permission to view this area."
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Admin"
        description="Platform usage, agent costs, users and job monitoring."
      />
      <div className="space-y-8">
        <UsageOverview />
        <AgentCosts />
        <UsersPanel />
        <JobsPanel />
      </div>
    </div>
  );
}

function UsageOverview() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.adminUsage,
    queryFn: () => adminApi.usage(),
  });

  const stats: Array<{ label: string; value: React.ReactNode }> = [
    { label: "Users", value: data ? formatNumber(data.total_users) : "—" },
    { label: "Books", value: data ? formatNumber(data.total_books) : "—" },
    { label: "Jobs", value: data ? formatNumber(data.total_jobs) : "—" },
    { label: "Running", value: data ? formatNumber(data.running_jobs) : "—" },
    { label: "Failed", value: data ? formatNumber(data.failed_jobs) : "—" },
    { label: "Credits consumed", value: data ? formatNumber(data.credits_consumed) : "—" },
    { label: "Tokens", value: data ? formatNumber(data.total_tokens) : "—" },
    { label: "Spend", value: data ? formatUsd(data.total_cost_usd, 4) : "—" },
  ];

  return (
    <section>
      <h2 className="mb-3 font-medium">Usage</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              {isLoading ? (
                <Skeleton className="mt-2 h-7 w-16" />
              ) : (
                <p className="mt-1 text-2xl font-semibold tabular-nums">{stat.value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function AgentCosts() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.adminAgentCosts,
    queryFn: () => adminApi.agentCosts(),
  });
  const rows = data ?? [];

  return (
    <section>
      <h2 className="mb-3 font-medium">Agent costs</h2>
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-8 rounded" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">No agent runs recorded yet.</p>
          ) : (
            <ul className="divide-y">
              {rows.map((row) => (
                <AgentCostItem key={row.agent_name} row={row} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function AgentCostItem({ row }: { row: AgentCostRow }) {
  const label = AGENT_LABELS[row.agent_name as AgentKey] ?? humanize(row.agent_name);
  return (
    <li className="flex items-center gap-4 px-5 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">
          {formatNumber(row.runs)} runs · {formatNumber(row.tokens)} tokens
        </p>
      </div>
      {row.failures > 0 && <Badge variant="destructive">{row.failures} failed</Badge>}
      <span className="w-24 text-right text-sm font-semibold tabular-nums">
        {formatUsd(row.cost_usd, 4)}
      </span>
    </li>
  );
}

function UsersPanel() {
  const [search, setSearch] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [editing, setEditing] = React.useState<AdminUser | null>(null);

  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const params = { search: debounced || undefined, limit: 50 };
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.adminUsers(params),
    queryFn: () => adminApi.users(params),
  });
  const users = data?.items ?? [];

  return (
    <section>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-medium">Users</h2>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by email or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9 rounded" />
              ))}
            </div>
          ) : users.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">No users found.</p>
          ) : (
            <ul className="divide-y">
              {users.map((user) => (
                <li key={user.id} className="flex items-center gap-4 px-5 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{user.email}</p>
                    <p className="text-xs text-muted-foreground">
                      {user.full_name || "No name"} · joined {relativeTime(user.created_at)}
                    </p>
                  </div>
                  {!user.is_active && <Badge variant="muted">Inactive</Badge>}
                  <Badge variant="secondary" className="capitalize">
                    {PLAN_LABELS[user.plan] ?? user.plan}
                  </Badge>
                  {user.role === "admin" && <Badge variant="info">Admin</Badge>}
                  <span className="flex w-20 items-center justify-end gap-1 text-sm tabular-nums text-muted-foreground">
                    <Coins className="size-3.5" /> {formatNumber(user.credits_balance)}
                  </span>
                  <Button variant="outline" size="sm" onClick={() => setEditing(user)}>
                    Edit
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {editing && (
        <EditUserDialog
          user={editing}
          onClose={() => setEditing(null)}
        />
      )}
    </section>
  );
}

function EditUserDialog({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [plan, setPlan] = React.useState(user.plan);
  const [role, setRole] = React.useState(user.role);
  const [creditsDelta, setCreditsDelta] = React.useState("0");
  const [note, setNote] = React.useState("");

  const save = useMutation({
    mutationFn: (payload: AdminUserUpdate) => adminApi.updateUser(user.id, payload),
    onSuccess: () => {
      toast.success("User updated");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message || "Could not update the user"),
  });

  function submit() {
    const delta = Number.parseInt(creditsDelta, 10) || 0;
    const payload: AdminUserUpdate = { plan: plan as "free" | "pro" | "business" };
    if (role !== user.role) payload.role = role as "user" | "admin";
    if (delta !== 0) {
      payload.credits_delta = delta;
      payload.credits_note = note || null;
    }
    save.mutate(payload);
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="edit-plan">Plan</Label>
              <select
                id="edit-plan"
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {Object.entries(PLAN_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role">Role</Label>
              <select
                id="edit-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="edit-credits">Credits adjustment</Label>
              <Input
                id="edit-credits"
                type="number"
                value={creditsDelta}
                onChange={(e) => setCreditsDelta(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Positive adds, negative removes. Current: {user.credits_balance.toLocaleString()}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-note">Note (optional)</Label>
              <Input
                id="edit-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Reason for the change"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function JobsPanel() {
  const [status, setStatus] = React.useState("");
  const params = { status: status || undefined, limit: 50 };
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.adminJobs(params),
    queryFn: () => adminApi.jobs(params),
  });
  const jobs = data?.items ?? [];

  return (
    <section>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="flex items-center gap-2 font-medium">
          <Activity className="size-4" /> Recent jobs
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {JOB_FILTERS.map((f) => (
            <Button
              key={f.value || "all"}
              variant={status === f.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatus(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded" />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">No jobs found.</p>
          ) : (
            <ul className="divide-y">
              {jobs.map((job) => (
                <JobRow key={job.id} job={job} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function JobRow({ job }: { job: AdminJob }) {
  const meta = jobStatus(job.status);
  return (
    <li className="flex items-center gap-4 px-5 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {humanize(job.type)}
          {job.current_step && (
            <span className="ml-2 text-xs text-muted-foreground">· {humanize(job.current_step)}</span>
          )}
        </p>
        <p className="text-xs text-muted-foreground">
          {absoluteTime(job.created_at)} · {job.attempts} attempt
          {job.attempts === 1 ? "" : "s"}
        </p>
      </div>
      <div className="hidden w-32 sm:block">
        <Progress value={job.progress_pct} />
      </div>
      <span className="w-28 text-right text-xs text-muted-foreground">
        {relativeTime(job.finished_at ?? job.created_at)}
      </span>
      <StatusBadge meta={meta} />
    </li>
  );
}
