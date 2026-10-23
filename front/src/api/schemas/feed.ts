import { z } from "zod";

import { unknownRecordSchema } from "./common";
import {
  insightSchema,
  sourcePostSchema,
  scoreComponentSchema,
} from "./insights";

export const categoryBriefSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  short_name: z.string(),
});

export const feedItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  what_it_means: z.string(),
  source_name: z.string(),
  source_url: z.string().nullish(),
  published_at: z.string(),
  impact: z.string(),
  impact_label: z.string(),
  importance: z.number().int(),
  categories: z.array(categoryBriefSchema),
  matched_categories: z.array(categoryBriefSchema),
  matched_counterparties: z.array(z.string()),
  match_reason: z.string(),
  is_tracked: z.boolean(),
  is_liked: z.boolean().default(false),
  likes: z.number().int().default(0),
  source_count: z.number().int().default(1),
  sources: z.array(sourcePostSchema).default([]),
  facts: z.array(unknownRecordSchema).default([]),
  score_breakdown: z.array(scoreComponentSchema).default([]),
  score_why: z.string().default(""),
  impact_share: z.string().default(""),
  is_important_mention: z.boolean().default(false),
  chain_key: z.string().nullish(),
  update_label: z.string().nullish(),
  prognosis_note: z.string(),
  detail_note: z.string(),
});

export const feedItemDetailSchema = feedItemSchema.extend(insightSchema.shape);

export const feedbackRequestSchema = z.object({
  action: z.enum(["track", "skip", "important", "not_relevant"]),
  reason: z.string().max(255).nullish(),
});

export const hiddenItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  impact: z.string(),
  impact_label: z.string(),
  importance: z.number().int(),
  reason: z.string(),
  age_days: z.number().int(),
  expires_in_days: z.number().int(),
  published_at: z.string(),
  source_name: z.string(),
  action: z.string(),
});

export const hiddenTabSchema = z.object({
  key: z.string(),
  label: z.string(),
  count: z.number().int(),
});

export const hiddenResponseSchema = z.object({
  tab: z.string(),
  description: z.string(),
  total: z.number().int(),
  tabs: z.array(hiddenTabSchema),
  items: z.array(hiddenItemSchema),
});

export const likeResponseSchema = z.object({
  liked: z.boolean(),
  likes: z.number().int(),
});

export const hiddenTabKeySchema = z.enum(["stale", "weak", "skipped"]);

export const impactSchema = z.enum(["risk", "opportunity", "mixed", "neutral"]);

export const feedListQuerySchema = z.object({
  impact: impactSchema.optional(),
  category: z.number().int().min(1).max(30).optional(),
  q: z.string().max(200).optional(),
  include_tracked: z.boolean().optional(),
  include_skipped: z.boolean().optional(),
  include_hidden: z.boolean().optional(),
  limit: z.number().int().min(1).max(100).optional(),
  offset: z.number().int().min(0).optional(),
});

export const hiddenQuerySchema = z.object({
  tab: hiddenTabKeySchema.optional(),
});

export const scenariosQuerySchema = z.object({
  horizon: z.enum(["3m", "6m", "12m"]).optional(),
});

export type CategoryBrief = z.infer<typeof categoryBriefSchema>;
export type FeedItem = z.infer<typeof feedItemSchema>;
export type FeedItemDetail = z.infer<typeof feedItemDetailSchema>;
export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;
export type HiddenItem = z.infer<typeof hiddenItemSchema>;
export type HiddenTab = z.infer<typeof hiddenTabSchema>;
export type HiddenResponse = z.infer<typeof hiddenResponseSchema>;
export type LikeResponse = z.infer<typeof likeResponseSchema>;
export type HiddenTabKey = z.infer<typeof hiddenTabKeySchema>;
export type Impact = z.infer<typeof impactSchema>;
export type FeedListQuery = z.infer<typeof feedListQuerySchema>;
export type HiddenQuery = z.infer<typeof hiddenQuerySchema>;
export type ScenariosQuery = z.infer<typeof scenariosQuerySchema>;
