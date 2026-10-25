import { z } from "zod";

import { unknownRecordSchema } from "./common";
import { feedItemSchema } from "./feed";
import { insightSchema, questionSchema } from "./insights";

export const trackedEventSchema = z.object({
  event_id: z.string(),
  title: z.string(),
  what_changed: z.string().nullish(),
  importance: z.number().int(),
  impact: z.string(),
  impact_label: z.string(),
  published_at: z.string(),
});

export const trackedItemSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  status: z.string(),
  title: z.string().nullish(),
  what_changed: z.string().nullish(),
  conclusions_changed: z.boolean().default(false),
  questions: z.array(questionSchema).default([]),
  report: unknownRecordSchema,
  analysis_pending: z.boolean().default(false),
  created_at: z.string(),
  updated_at: z.string(),
  event: feedItemSchema,
  events: z.array(trackedEventSchema).default([]),
  insight: insightSchema.nullish(),
});

export const trackedListResponseSchema = z.object({
  items: z.array(trackedItemSchema),
  total: z.number().int(),
});

export const agentReanalyzeRequestSchema = z.object({
  question: z.string().max(1000).nullish(),
});

export const trackedQuestionRequestSchema = z.object({
  question: z.string().min(3).max(1000),
});

export const trackedListQuerySchema = z.object({
  status: z.string().optional(),
});

export type TrackedEvent = z.infer<typeof trackedEventSchema>;
export type TrackedItem = z.infer<typeof trackedItemSchema>;
export type TrackedListResponse = z.infer<typeof trackedListResponseSchema>;
export type AgentReanalyzeRequest = z.infer<typeof agentReanalyzeRequestSchema>;
export type TrackedQuestionRequest = z.infer<typeof trackedQuestionRequestSchema>;
export type TrackedListQuery = z.infer<typeof trackedListQuerySchema>;
