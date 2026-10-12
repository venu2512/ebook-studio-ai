/**
 * API DTOs shared by the web app and any TypeScript consumers.
 *
 * These mirror the Pydantic schemas under `apps/api/app/schemas`. Keep the
 * field names identical to the JSON produced by the API.
 */

export type ISODate = string;
export type UUID = string;

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorBody {
  error: ErrorDetail;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface MessageResponse {
  message: string;
}

/* ------------------------------------------------------------------ */
/* Auth & users                                                        */
/* ------------------------------------------------------------------ */

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string | null;
  csrf_token?: string | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface User {
  id: UUID;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  plan: "free" | "pro" | "business";
  is_verified: boolean;
  credits_balance: number;
  default_language: string;
  default_tone: string | null;
  created_at: ISODate;
  last_login_at: ISODate | null;
}

export interface UserUpdate {
  full_name?: string | null;
  avatar_url?: string | null;
  default_language?: string | null;
  default_tone?: string | null;
  settings_json?: Record<string, unknown> | null;
}

export interface Credits {
  balance: number;
  plan: string;
  monthly_allowance: number;
  credits_per_1k_tokens: number;
}

export interface CreditTransaction {
  id: UUID;
  amount: number;
  balance_after: number;
  reason: string;
  description: string | null;
  created_at: ISODate;
}

/* ------------------------------------------------------------------ */
/* Books                                                               */
/* ------------------------------------------------------------------ */

export interface BookCreate {
  topic: string;
  title?: string | null;
  audience: string;
  category: string;
  language: string;
  tone: string;
  target_pages: number;
  target_word_count?: number | null;
  style_guide?: string | null;
  author_name?: string | null;
  keywords?: string[];
  template?: string;
  chapter_count?: number | null;
}

export interface BookUpdate {
  title?: string | null;
  subtitle?: string | null;
  topic?: string | null;
  audience?: string | null;
  category?: string | null;
  language?: string | null;
  tone?: string | null;
  target_pages?: number | null;
  target_word_count?: number | null;
  style_guide?: string | null;
  author_name?: string | null;
  description?: string | null;
  keywords?: string[] | null;
  metadata_json?: Record<string, unknown> | null;
}

export interface DesignMeta {
  palette?: Record<string, string>;
  cover_prompt?: string;
  typography?: Record<string, unknown>;
  interior_template?: string;
}

export interface Book {
  id: UUID;
  user_id: UUID;
  title: string;
  subtitle: string | null;
  topic: string;
  audience: string;
  category: string;
  language: string;
  tone: string;
  style_guide: string | null;
  target_pages: number;
  target_word_count: number;
  author_name: string | null;
  status: string;
  cover_asset_id: UUID | null;
  description: string | null;
  keywords: string[];
  estimated_credits: number;
  credits_charged: number;
  token_budget: number;
  tokens_used: number;
  cost_usd: number;
  metadata_json: { design?: DesignMeta; chapter_count?: number } & Record<string, unknown>;
  is_sensitive: boolean;
  created_at: ISODate;
  updated_at: ISODate;
  deleted_at: ISODate | null;
}

export interface BookListItem {
  id: UUID;
  title: string;
  subtitle: string | null;
  topic: string;
  category: string;
  language: string;
  status: string;
  target_pages: number;
  target_word_count: number;
  cover_asset_id: UUID | null;
  created_at: ISODate;
  updated_at: ISODate;
}

export interface BookWithProgress extends BookListItem {
  chapter_count: number;
  completed_chapters: number;
  progress_pct: number;
  current_job_status: string | null;
}

export interface CostEstimate {
  estimated_tokens: number;
  estimated_credits: number;
  user_balance: number;
  affordable: boolean;
  breakdown: Record<string, number>;
}

/* ------------------------------------------------------------------ */
/* Outline                                                             */
/* ------------------------------------------------------------------ */

export interface OutlineChapter {
  title: string;
  summary: string;
  key_points: string[];
  word_budget: number;
}

export interface OutlinePart {
  title: string;
  chapters: OutlineChapter[];
}

export interface OutlineStructure {
  parts: OutlinePart[];
  title?: string;
  subtitle?: string | null;
  title_options?: string[];
  reader_promise?: string;
}

export interface Outline {
  id: UUID;
  book_id: UUID;
  version: number;
  structure: OutlineStructure;
  total_word_budget: number;
  approved_at: ISODate | null;
  created_at: ISODate;
}

export interface OutlineGenerateRequest {
  chapter_count?: number | null;
  extra_instructions?: string | null;
  reuse_research?: boolean;
}

export interface OutlineUpdateRequest {
  structure: OutlineStructure;
  title?: string | null;
  subtitle?: string | null;
  reader_promise?: string | null;
}

export interface OutlineApprovalResponse {
  status: string;
  approved_at: ISODate;
  chapter_count: number;
  total_word_budget: number;
}

/* ------------------------------------------------------------------ */
/* Chapters                                                            */
/* ------------------------------------------------------------------ */

export interface Flag {
  type?: string;
  message?: string;
  severity?: string;
  [key: string]: unknown;
}

export interface Chapter {
  id: UUID;
  book_id: UUID;
  order_index: number;
  part_title: string | null;
  title: string;
  summary: string | null;
  key_points: string[];
  content: string | null;
  word_count: number;
  target_word_count: number;
  status: string;
  current_version: number;
  flags: Flag[];
  fact_checks: Flag[];
  created_at: ISODate;
  updated_at: ISODate;
}

export interface ChapterListItem {
  id: UUID;
  order_index: number;
  title: string;
  status: string;
  word_count: number;
  target_word_count: number;
  part_title: string | null;
  updated_at: ISODate;
}

export interface ChapterUpdate {
  title?: string | null;
  content?: string | null;
  summary?: string | null;
  status?: string | null;
  editor_notes?: string | null;
  create_version?: boolean;
}

export type AIAction = "rewrite" | "expand" | "shorten" | "change_tone" | "improve";

export interface AIActionRequest {
  action: AIAction;
  tone?: string | null;
  selection?: string | null;
  instructions?: string | null;
}

export interface AIActionResponse {
  chapter_id: UUID;
  action: string;
  content: string;
  word_count: number;
  flags: Flag[];
}

export interface ChapterVersion {
  id: UUID;
  chapter_id: UUID;
  version: number;
  word_count: number;
  source: string;
  editor_notes: string | null;
  created_at: ISODate;
}

export interface ChapterVersionDetail extends ChapterVersion {
  content: string;
}

/* ------------------------------------------------------------------ */
/* Jobs & pipeline                                                     */
/* ------------------------------------------------------------------ */

export interface Job {
  id: UUID;
  book_id: UUID;
  user_id: UUID;
  type: string;
  status: string;
  current_step: string | null;
  completed_steps: string[];
  progress_pct: number;
  error_code: string | null;
  error: string | null;
  attempts: number;
  reserved_credits: number;
  charged: boolean;
  started_at: ISODate | null;
  finished_at: ISODate | null;
  cancel_requested: boolean;
  created_at: ISODate;
}

export interface AgentRun {
  id: UUID;
  job_id: UUID;
  agent_name: string;
  status: string;
  attempt: number;
  step_key: string | null;
  model: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  duration_ms: number;
  error: string | null;
  created_at: ISODate;
}

export interface AgentRunDetail extends AgentRun {
  output: Record<string, unknown>;
  prompt: string | null;
}

export interface PipelineStep {
  key: string;
  agent: string;
  label: string;
  status: "pending" | "running" | "succeeded" | "failed" | "skipped";
  detail: string | null;
  progress_pct: number;
  elapsed_ms: number | null;
  tokens: number;
  cost_usd: number;
}

export interface PipelineState {
  job_id: UUID;
  status: string;
  progress_pct: number;
  steps: PipelineStep[];
  message: string | null;
}

export interface GenerateRequest {
  type?: "full_book" | "chapter" | "cover" | "export";
  chapter_id?: UUID | null;
  format?: "pdf" | "epub" | "docx" | null;
  template?: string | null;
  force?: boolean;
}

/* ------------------------------------------------------------------ */
/* Exports & cover                                                     */
/* ------------------------------------------------------------------ */

export interface ExportCreateRequest {
  format: "pdf" | "epub" | "docx";
  template?: string;
  page_size?: "a5" | "letter" | "a4";
  include_front_matter?: boolean;
  include_toc?: boolean;
}

export interface Export {
  id: UUID;
  book_id: UUID;
  format: string;
  template: string;
  status: string;
  size_bytes: number;
  page_count: number | null;
  checksum: string | null;
  validation: Record<string, unknown>;
  error: string | null;
  renderer: string | null;
  created_at: ISODate;
}

export interface ExportDownload {
  export_id: UUID;
  url: string;
  expires_in: number;
  filename: string;
  size_bytes: number;
}

export interface Template {
  id: UUID;
  name: string;
  slug: string;
  kind: "interior" | "cover";
  description: string | null;
  config: Record<string, unknown>;
  preview_url: string | null;
  is_premium: boolean;
}

export interface Cover {
  asset_id: UUID | null;
  url: string | null;
  prompt: string | null;
  palette: Record<string, string>;
}

export interface Asset {
  id: UUID;
  kind: string;
  url: string | null;
  mime_type: string | null;
  size_bytes: number;
  width: number | null;
  height: number | null;
  created_at: ISODate;
}

/* ------------------------------------------------------------------ */
/* Marketing                                                           */
/* ------------------------------------------------------------------ */

export interface SocialPost {
  platform: string;
  text: string;
}

export interface EmailStep {
  day: number;
  subject: string;
  body: string;
}

export interface MarketingKit {
  id: UUID;
  book_id: UUID;
  description: string | null;
  short_description: string | null;
  keywords: string[];
  categories: string[];
  kdp_categories: string[];
  bullet_points: string[];
  social_posts: SocialPost[];
  email_sequence: EmailStep[];
  author_bio: string | null;
  created_at: ISODate;
}

/* ------------------------------------------------------------------ */
/* Billing                                                             */
/* ------------------------------------------------------------------ */

export interface Plan {
  id: string;
  name: string;
  price_usd_month: number;
  monthly_credits: number;
  features: string[];
  stripe_price_id: string | null;
  is_current: boolean;
}

export interface CreditPack {
  id: string;
  name: string;
  credits: number;
  price_usd: number;
  stripe_price_id: string | null;
}

export interface BillingSummary {
  plan: string;
  credits_balance: number;
  monthly_allowance: number;
  billing_enabled: boolean;
  stripe_customer_id: string | null;
}

export interface CheckoutRequest {
  kind: "subscription" | "credits";
  price_id?: string | null;
  plan?: "pro" | "business" | null;
  pack?: "credits_100" | "credits_500" | "credits_2000" | null;
  success_url?: string | null;
  cancel_url?: string | null;
}

export interface CheckoutSession {
  url: string;
  session_id: string;
}

/* ------------------------------------------------------------------ */
/* Admin                                                               */
/* ------------------------------------------------------------------ */

export interface AdminUser {
  id: UUID;
  email: string;
  full_name: string | null;
  role: string;
  plan: string;
  is_active: boolean;
  is_verified: boolean;
  credits_balance: number;
  created_at: ISODate;
  last_login_at: ISODate | null;
}

export interface UsageSummary {
  total_users: number;
  total_books: number;
  total_jobs: number;
  failed_jobs: number;
  running_jobs: number;
  total_tokens: number;
  total_cost_usd: number;
  credits_consumed: number;
}

export interface AdminJob {
  id: UUID;
  book_id: UUID;
  user_id: UUID;
  type: string;
  status: string;
  current_step: string | null;
  progress_pct: number;
  error: string | null;
  attempts: number;
  created_at: ISODate;
  finished_at: ISODate | null;
}

export interface AgentCostRow {
  agent_name: string;
  runs: number;
  tokens: number;
  cost_usd: number;
  failures: number;
}

export interface AdminUserUpdate {
  full_name?: string | null;
  role?: "user" | "admin";
  plan?: "free" | "pro" | "business";
  is_active?: boolean | null;
  is_verified?: boolean | null;
  credits_delta?: number | null;
  credits_note?: string | null;
}
