/**
 * Domain constants shared between the API and the web app.
 *
 * These mirror `apps/api/app/db/models/enums.py` and
 * `apps/api/app/schemas/book.py`. Keep them in sync.
 */

export const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "pt", label: "Portuguese" },
  { value: "it", label: "Italian" },
  { value: "nl", label: "Dutch" },
  { value: "hi", label: "Hindi" },
  { value: "ja", label: "Japanese" },
  { value: "zh", label: "Chinese" },
] as const;

export const TONES = [
  { value: "conversational", label: "Conversational", hint: "Warm and easy to read" },
  { value: "professional", label: "Professional", hint: "Polished and businesslike" },
  { value: "academic", label: "Academic", hint: "Rigorous and cited" },
  { value: "friendly", label: "Friendly", hint: "Approachable and upbeat" },
  { value: "authoritative", label: "Authoritative", hint: "Confident and expert" },
  { value: "motivational", label: "Motivational", hint: "Inspiring and action-oriented" },
] as const;

export const CATEGORIES = [
  "Business",
  "Self-Help",
  "Technology",
  "Health",
  "Finance",
  "Education",
  "Fiction",
  "Biography",
  "Cooking",
  "Travel",
  "Parenting",
  "General",
] as const;

/** Categories that trigger a mandatory disclaimer and extra fact-checking. */
export const SENSITIVE_CATEGORIES = [
  "health",
  "medical",
  "legal",
  "finance",
  "financial",
  "investing",
  "psychology",
  "therapy",
  "medication",
  "insurance",
] as const;

export const WORDS_PER_PAGE = 250;

/** Display label for a category slug (currently identity, kept for i18n). */
export function categoriesLabel(value: string): string {
  return value;
}

/** True when a category requires a disclaimer and extra fact-checking. */
export function isSensitiveCategory(category: string | null | undefined): boolean {
  if (!category) return false;
  return (SENSITIVE_CATEGORIES as readonly string[]).includes(category.trim().toLowerCase());
}

export const BOOK_STATUSES = [
  "draft",
  "planning",
  "awaiting_approval",
  "writing",
  "editing",
  "designing",
  "ready",
  "failed",
  "cancelled",
] as const;
export type BookStatus = (typeof BOOK_STATUSES)[number];

export const JOB_STATUSES = [
  "queued",
  "running",
  "succeeded",
  "failed",
  "cancelled",
] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const CHAPTER_STATUSES = [
  "pending",
  "generating",
  "drafted",
  "edited",
  "fact_checked",
  "approved",
  "failed",
] as const;
export type ChapterStatus = (typeof CHAPTER_STATUSES)[number];

export const AGENT_KEYS = [
  "researcher",
  "planner",
  "writer",
  "editor",
  "fact_checker",
  "designer",
  "publisher",
  "marketer",
] as const;
export type AgentKey = (typeof AGENT_KEYS)[number];

export const AGENT_LABELS: Record<AgentKey, string> = {
  researcher: "Researcher",
  planner: "Book Planner",
  writer: "Writer",
  editor: "Editor",
  fact_checker: "Fact Checker",
  designer: "Designer",
  publisher: "Publisher",
  marketer: "Marketing Specialist",
};

export const AGENT_DESCRIPTIONS: Record<AgentKey, string> = {
  researcher: "Gathers themes, sources and gaps on your topic",
  planner: "Designs the parts, chapters and word budgets",
  writer: "Drafts each chapter in your voice",
  editor: "Tightens prose, removes filler, enforces consistency",
  fact_checker: "Verifies claims and flags anything unverified",
  designer: "Chooses the cover art direction and typography",
  publisher: "Renders PDF, EPUB and DOCX with front matter",
  marketer: "Writes the description, keywords and launch copy",
};

export const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  business: "Business",
};

export const EXPORT_FORMATS = ["pdf", "epub", "docx"] as const;
export type ExportFormat = (typeof EXPORT_FORMATS)[number];

export const PAGE_SIZES = [
  { value: "a5", label: "A5 — digest (5.8×8.3 in)" },
  { value: "a4", label: "A4 — document (8.3×11.7 in)" },
  { value: "letter", label: "Letter (8.5×11 in)" },
] as const;

export const COVER_STYLES = [
  "minimal",
  "bold",
  "illustrated",
  "photographic",
  "abstract",
  "vintage",
] as const;
