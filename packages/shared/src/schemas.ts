/**
 * Zod schemas for client-side validation (React Hook Form).
 *
 * The API validates authoritatively; these mirror its rules so the user gets
 * immediate, friendly feedback before a request is made.
 */

import { z } from "zod";

import { CATEGORIES, LANGUAGES, TONES, WORDS_PER_PAGE } from "./constants";

export const emailSchema = z
  .string()
  .min(1, "Email is required")
  .email("Enter a valid email address");

export const passwordSchema = z
  .string()
  .min(8, "Use at least 8 characters")
  .max(128, "Keep it under 128 characters");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Password is required"),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    full_name: z.string().max(200, "Keep it under 200 characters").optional().or(z.literal("")),
    email: emailSchema,
    password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });
export type RegisterValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({ email: emailSchema });
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export const bookCreateSchema = z.object({
  topic: z
    .string()
    .min(3, "Describe your topic in at least 3 characters")
    .max(500, "Keep it under 500 characters"),
  title: z.string().max(300).optional().or(z.literal("")),
  audience: z.string().max(400).default("General readers"),
  category: z.string().max(120).default("General"),
  language: z.string().default("en"),
  tone: z.string().default("conversational"),
  target_pages: z.coerce.number().int().min(6).max(500).default(20),
  target_word_count: z.coerce.number().int().min(1500).max(150000).optional(),
  style_guide: z.string().max(4000).optional().or(z.literal("")),
  author_name: z.string().max(200).optional().or(z.literal("")),
  keywords: z.array(z.string()).max(20).default([]),
  template: z.string().default("classic"),
  chapter_count: z.coerce.number().int().min(3).max(40).optional(),
});
export type BookCreateValues = z.infer<typeof bookCreateSchema>;

/** Convenience helper: default word count derived from a page target. */
export function wordsForPages(pages: number): number {
  return Math.max(1500, Math.round(pages * WORDS_PER_PAGE));
}

export const outlineChapterSchema = z.object({
  title: z.string().min(1, "Every chapter needs a title").max(300),
  summary: z.string().default(""),
  key_points: z.array(z.string()).default([]),
  word_budget: z.coerce.number().int().min(0).default(0),
});

export const outlinePartSchema = z.object({
  title: z.string().default("Part I"),
  chapters: z.array(outlineChapterSchema).default([]),
});

export const outlineStructureSchema = z.object({
  parts: z.array(outlinePartSchema).default([]),
  title: z.string().optional(),
  subtitle: z.string().nullable().optional(),
  title_options: z.array(z.string()).optional(),
  reader_promise: z.string().optional(),
});

export const profileSchema = z.object({
  full_name: z.string().max(200).optional().or(z.literal("")),
  default_language: z.string().max(10).optional(),
  default_tone: z.string().max(50).optional().or(z.literal("")),
});
export type ProfileValues = z.infer<typeof profileSchema>;

export const creditPackIds = ["credits_100", "credits_500", "credits_2000"] as const;

export const KNOWN_LANGUAGES = LANGUAGES.map((l) => l.value);
export const KNOWN_TONES = TONES.map((t) => t.value);
export const KNOWN_CATEGORIES = [...CATEGORIES];
