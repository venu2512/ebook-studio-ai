/**
 * Typed wrappers for every API endpoint the web app calls.
 *
 * Keeping them in one module means route components never hand-write URLs and
 * every request benefits from the shared auth/refresh handling in `client.ts`.
 */

import type {
  AdminJob,
  AdminUser,
  AdminUserUpdate,
  AgentCostRow,
  AgentRun,
  AIActionRequest,
  AIActionResponse,
  Asset,
  BillingSummary,
  Book,
  BookCreate,
  BookUpdate,
  BookWithProgress,
  Chapter,
  ChapterListItem,
  ChapterUpdate,
  ChapterVersion,
  ChapterVersionDetail,
  CheckoutRequest,
  CheckoutSession,
  CostEstimate,
  Cover,
  CreditPack,
  Credits,
  CreditTransaction,
  Export,
  ExportCreateRequest,
  ExportDownload,
  ForgotPasswordRequest,
  GenerateRequest,
  Job,
  LoginRequest,
  MarketingKit,
  MessageResponse,
  Outline,
  OutlineApprovalResponse,
  OutlineGenerateRequest,
  OutlineUpdateRequest,
  Page,
  Plan,
  RegisterRequest,
  ResetPasswordRequest,
  Template,
  TokenResponse,
  UsageSummary,
  User,
  UserUpdate,
} from "@ebook/shared";

import { api, tokenStore } from "./client";

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

export const authApi = {
  async register(payload: RegisterRequest): Promise<User> {
    const user = await api.post<User>("/api/v1/auth/register", payload, { anonymous: true });
    const token = readAccessTokenFromHeaders();
    if (token) tokenStore.set(token);
    return user;
  },
  async login(payload: LoginRequest): Promise<TokenResponse> {
    const tokens = await api.post<TokenResponse>("/api/v1/auth/login", payload, {
      anonymous: true,
    });
    tokenStore.set(tokens.access_token, tokens.refresh_token);
    return tokens;
  },
  async logout(): Promise<MessageResponse> {
    try {
      return await api.post<MessageResponse>("/api/v1/auth/logout", undefined, { anonymous: true });
    } finally {
      tokenStore.clear();
    }
  },
  me(): Promise<User> {
    return api.get<User>("/api/v1/auth/me");
  },
  forgotPassword(payload: ForgotPasswordRequest): Promise<MessageResponse> {
    return api.post<MessageResponse>("/api/v1/auth/forgot-password", payload, { anonymous: true });
  },
  resetPassword(payload: ResetPasswordRequest): Promise<MessageResponse> {
    return api.post<MessageResponse>("/api/v1/auth/reset-password", payload, { anonymous: true });
  },
  verifyEmail(token: string): Promise<MessageResponse> {
    return api.post<MessageResponse>("/api/v1/auth/verify-email", { token }, { anonymous: true });
  },
  async google(payload: { id_token?: string; code?: string }): Promise<TokenResponse> {
    const tokens = await api.post<TokenResponse>("/api/v1/auth/google", payload, {
      anonymous: true,
    });
    tokenStore.set(tokens.access_token, tokens.refresh_token);
    return tokens;
  },
};


/**
 * The register endpoint returns the user but sets `X-Access-Token`. Since the
 * browser fetch wrapper does not surface response headers, we fall back to
 * logging in immediately after registering when no token was captured.
 */
let capturedAccessToken: string | null = null;
export function captureAccessToken(token: string | null) {
  capturedAccessToken = token;
}
function readAccessTokenFromHeaders(): string | null {
  return capturedAccessToken;
}

export const usersApi = {
  me(): Promise<User> {
    return api.get<User>("/api/v1/users/me");
  },
  update(payload: UserUpdate): Promise<User> {
    return api.patch<User>("/api/v1/users/me", payload);
  },
  credits(): Promise<Credits> {
    return api.get<Credits>("/api/v1/users/me/credits");
  },
  transactions(limit = 20, offset = 0): Promise<Page<CreditTransaction>> {
    return api.get<Page<CreditTransaction>>(
      `/api/v1/users/me/credits/transactions${qs({ limit, offset })}`,
    );
  },
  deleteAccount(password: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>("/api/v1/users/me", { password, confirm: true });
  },
  exportData(): Promise<Record<string, unknown>> {
    return api.get<Record<string, unknown>>("/api/v1/users/me/export");
  },
};


export const booksApi = {
  list(params: {
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<Page<BookWithProgress>> {
    return api.get<Page<BookWithProgress>>(`/api/v1/books${qs(params)}`);
  },
  create(payload: BookCreate): Promise<Book> {
    return api.post<Book>("/api/v1/books", payload);
  },
  get(bookId: string): Promise<Book> {
    return api.get<Book>(`/api/v1/books/${bookId}`);
  },
  update(bookId: string, payload: BookUpdate): Promise<Book> {
    return api.patch<Book>(`/api/v1/books/${bookId}`, payload);
  },
  remove(bookId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/api/v1/books/${bookId}`);
  },
  costEstimate(bookId: string): Promise<CostEstimate> {
    return api.get<CostEstimate>(`/api/v1/books/${bookId}/cost-estimate`);
  },
  bible(bookId: string): Promise<Record<string, unknown>> {
    return api.get<Record<string, unknown>>(`/api/v1/books/${bookId}/bible`);
  },
};

export const outlineApi = {
  generate(bookId: string, payload: OutlineGenerateRequest): Promise<Job> {
    return api.post<Job>(`/api/v1/books/${bookId}/outline`, payload);
  },
  get(bookId: string): Promise<Outline> {
    return api.get<Outline>(`/api/v1/books/${bookId}/outline`);
  },
  update(bookId: string, payload: OutlineUpdateRequest): Promise<Outline> {
    return api.patch<Outline>(`/api/v1/books/${bookId}/outline`, payload);
  },
  approve(bookId: string): Promise<OutlineApprovalResponse> {
    return api.post<OutlineApprovalResponse>(`/api/v1/books/${bookId}/outline/approve`);
  },
};

export const chaptersApi = {
  list(bookId: string): Promise<Page<ChapterListItem>> {
    return api.get<Page<ChapterListItem>>(`/api/v1/books/${bookId}/chapters`);
  },
  get(chapterId: string): Promise<Chapter> {
    return api.get<Chapter>(`/api/v1/chapters/${chapterId}`);
  },
  update(chapterId: string, payload: ChapterUpdate): Promise<Chapter> {
    return api.patch<Chapter>(`/api/v1/chapters/${chapterId}`, payload);
  },
  aiAction(chapterId: string, payload: AIActionRequest): Promise<AIActionResponse> {
    return api.post<AIActionResponse>(`/api/v1/chapters/${chapterId}/ai-action`, payload);
  },
  regenerate(chapterId: string, instructions?: string): Promise<Job> {
    return api.post<Job>(`/api/v1/chapters/${chapterId}/regenerate`, { instructions });
  },
  versions(chapterId: string): Promise<Page<ChapterVersion>> {
    return api.get<Page<ChapterVersion>>(`/api/v1/chapters/${chapterId}/versions`);
  },
  version(chapterId: string, version: number): Promise<ChapterVersionDetail> {
    return api.get<ChapterVersionDetail>(`/api/v1/chapters/${chapterId}/versions/${version}`);
  },
  restore(chapterId: string, version: number): Promise<Chapter> {
    return api.post<Chapter>(`/api/v1/chapters/${chapterId}/restore`, { version });
  },
};

export const jobsApi = {
  generate(bookId: string, payload: GenerateRequest): Promise<Job> {
    return api.post<Job>(`/api/v1/books/${bookId}/generate`, payload);
  },
  listForBook(bookId: string, limit = 20): Promise<Page<Job>> {
    return api.get<Page<Job>>(`/api/v1/books/${bookId}/jobs${qs({ limit })}`);
  },
  get(jobId: string): Promise<Job> {
    return api.get<Job>(`/api/v1/jobs/${jobId}`);
  },
  pipeline(jobId: string): Promise<import("@ebook/shared").PipelineState> {
    return api.get<import("@ebook/shared").PipelineState>(`/api/v1/jobs/${jobId}/pipeline`);
  },
  runs(jobId: string, includeOutput = false): Promise<Page<AgentRun>> {
    return api.get<Page<AgentRun>>(
      `/api/v1/jobs/${jobId}/runs${qs({ include_output: includeOutput })}`,
    );
  },
  cancel(jobId: string): Promise<Job> {
    return api.post<Job>(`/api/v1/jobs/${jobId}/cancel`);
  },
  retry(jobId: string): Promise<Job> {
    return api.post<Job>(`/api/v1/jobs/${jobId}/retry`);
  },
};

export const exportsApi = {
  create(bookId: string, payload: ExportCreateRequest): Promise<Export> {
    return api.post<Export>(`/api/v1/books/${bookId}/exports`, payload);
  },
  list(bookId: string): Promise<Page<Export>> {
    return api.get<Page<Export>>(`/api/v1/books/${bookId}/exports`);
  },
  download(exportId: string): Promise<ExportDownload> {
    return api.get<ExportDownload>(`/api/v1/exports/${exportId}/download`);
  },
  remove(exportId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/api/v1/exports/${exportId}`);
  },
  templates(kind?: "interior" | "cover"): Promise<Template[]> {
    return api.get<Template[]>(`/api/v1/templates${qs({ kind })}`);
  },
};

export const coverApi = {
  get(bookId: string): Promise<Cover> {
    return api.get<Cover>(`/api/v1/books/${bookId}/cover`);
  },
  regenerate(bookId: string, prompt?: string): Promise<Cover> {
    return api.post<Cover>(`/api/v1/books/${bookId}/cover`, { prompt });
  },
  assets(bookId: string): Promise<Asset[]> {
    return api.get<Asset[]>(`/api/v1/books/${bookId}/assets`);
  },
};

export const marketingApi = {
  get(bookId: string): Promise<MarketingKit> {
    return api.get<MarketingKit>(`/api/v1/books/${bookId}/marketing`);
  },
  regenerate(bookId: string): Promise<MarketingKit> {
    return api.post<MarketingKit>(`/api/v1/books/${bookId}/marketing`);
  },
};

export const billingApi = {
  plans(): Promise<Plan[]> {
    return api.get<Plan[]>("/api/v1/billing/plans");
  },
  creditPacks(): Promise<CreditPack[]> {
    return api.get<CreditPack[]>("/api/v1/billing/credits/packs");
  },
  summary(): Promise<BillingSummary> {
    return api.get<BillingSummary>("/api/v1/billing/summary");
  },
  checkout(payload: CheckoutRequest): Promise<CheckoutSession> {
    return api.post<CheckoutSession>("/api/v1/billing/checkout", payload);
  },
  portal(): Promise<{ url: string }> {
    return api.post<{ url: string }>("/api/v1/billing/portal");
  },
};

export const adminApi = {
  usage(): Promise<UsageSummary> {
    return api.get<UsageSummary>("/api/v1/admin/usage");
  },
  agentCosts(): Promise<AgentCostRow[]> {
    return api.get<AgentCostRow[]>("/api/v1/admin/agents/costs");
  },
  users(params: { search?: string; plan?: string; limit?: number; offset?: number } = {}): Promise<
    Page<AdminUser>
  > {
    return api.get<Page<AdminUser>>(`/api/v1/admin/users${qs(params)}`);
  },
  updateUser(userId: string, payload: AdminUserUpdate): Promise<AdminUser> {
    return api.patch<AdminUser>(`/api/v1/admin/users/${userId}`, payload);
  },
  jobs(params: { status?: string; limit?: number; offset?: number } = {}): Promise<Page<AdminJob>> {
    return api.get<Page<AdminJob>>(`/api/v1/admin/jobs${qs(params)}`);
  },
};
