import { z } from "zod";

import { unknownRecordSchema } from "./common";

export const sourcePostSchema = z.object({
  name: z.string(),
  time: z.string(),
  tone: z.string().default("neutral"),
  text: z.string(),
  is_primary: z.boolean().default(false),
  handle: z.string().nullish(),
  url: z.string().nullish(),
  image_url: z.string().nullish(),
  status: z.string().default("single"),
  status_label: z.string().default("Один канал"),
});

export const scoreComponentSchema = z.object({
  key: z.string(),
  label: z.string(),
  value: z.number().int(),
  max: z.number().int().default(5),
  text: z.string(),
});

export const sourceComparisonSchema = z.object({
  agree: z.array(z.string()).default([]),
  differ: z.array(z.string()).default([]),
  single: z.array(z.string()).default([]),
});

export const thesisSchema = z.object({
  category: z.string(),
  text: z.string(),
  status: z.string(),
  sources: z.array(z.string()).default([]),
});

export const alfaAnalyticsSchema = z.object({
  author: z.string(),
  text: z.string(),
});

export const scenarioSchema = z.object({
  name: z.string(),
  effect: z.number(),
  effect_label: z.string(),
  probability: z.number().int(),
  note: z.string(),
  formula: z.string(),
  share: z.string().nullish(),
  origin: z.string().nullish(),
  is_base: z.boolean().default(false),
});

export const assumptionSchema = z.object({
  key: z.string(),
  label: z.string(),
  effect: z.string(),
});

export const scenarioSetSchema = z.object({
  horizon: z.string(),
  horizon_label: z.string(),
  lever_label: z.string(),
  lever_values: z.array(z.string()),
  scenarios: z.array(scenarioSchema),
  assumptions: z.array(assumptionSchema),
  note: z.string(),
  needs_profile: z.array(z.string()).default([]),
  forecast_note: z.string().nullish(),
});

export const questionSchema = z.object({
  id: z.string(),
  text: z.string(),
  status: z.string(),
  status_code: z.string().default("waiting"),
  answer: z.string().nullish(),
  source: z.string().nullish(),
  date: z.string().nullish(),
  internal: z.boolean().default(false),
});

export const timelinePointSchema = z.object({
  date: z.string(),
  text: z.string(),
  importance: z.number().int(),
  is_current: z.boolean().default(false),
});

export const actionSchema = z.object({
  id: z.string().nullish(),
  title: z.string(),
  role: z.string(),
  description: z.string().nullish(),
  deadline: z.string(),
  deadline_label: z.string().nullish(),
  origin: z.string().default("AI"),
  is_primary: z.boolean().default(false),
});

export const agentStepSchema = z.object({
  type: z.string(),
  text: z.string(),
  is_correction: z.boolean().default(false),
  at: z.string().nullish(),
});

export const impactTileSchema = z.object({
  type: z.enum(["metric", "statement", "accent"]),
  value: z.string().nullish(),
  label: z.string(),
  note: z.string().nullish(),
  span: z.enum(["half", "full"]).default("half"),
});

export const chatMessageSchema = z.object({
  question: z.string(),
  answer: z.string(),
  origin: z.string().default("AI"),
});

export const productSchema = z.object({
  name: z.string(),
  description: z.string(),
  benefit: z.string(),
});

export const insightSchema = z.object({
  sources: z.array(sourcePostSchema),
  score_breakdown: z.array(scoreComponentSchema),
  score_why: z.string(),
  impact_share: z.string(),
  comparison: sourceComparisonSchema,
  theses: z.array(thesisSchema),
  alfa: alfaAnalyticsSchema.nullish(),
  impact_tiles: z.array(impactTileSchema).default([]),
  scenarios: scenarioSetSchema,
  open_questions: z.array(questionSchema),
  timeline: z.array(timelinePointSchema),
  checklist: z.array(z.string()),
  actions: z.array(actionSchema),
  agent_log: z.array(agentStepSchema),
  product: productSchema.nullish(),
  chat: z.array(chatMessageSchema).default([]),
  facts: z.array(unknownRecordSchema).default([]),
  questions_answered: z.number().int().default(0),
  questions_waiting: z.number().int().default(0),
  timeline_total: z.number().int().default(0),
  timeline_current_index: z.number().int().default(0),
  analysis_finished_at: z.string().nullish(),
  analysis_pending: z.boolean().default(false),
});

export const horizonSchema = z.enum(["3m", "6m", "12m"]);

export type SourcePost = z.infer<typeof sourcePostSchema>;
export type ScoreComponent = z.infer<typeof scoreComponentSchema>;
export type SourceComparison = z.infer<typeof sourceComparisonSchema>;
export type Thesis = z.infer<typeof thesisSchema>;
export type AlfaAnalytics = z.infer<typeof alfaAnalyticsSchema>;
export type Scenario = z.infer<typeof scenarioSchema>;
export type Assumption = z.infer<typeof assumptionSchema>;
export type ScenarioSet = z.infer<typeof scenarioSetSchema>;
export type Question = z.infer<typeof questionSchema>;
export type TimelinePoint = z.infer<typeof timelinePointSchema>;
export type Action = z.infer<typeof actionSchema>;
export type AgentStep = z.infer<typeof agentStepSchema>;
export type ImpactTile = z.infer<typeof impactTileSchema>;
export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type Product = z.infer<typeof productSchema>;
export type Insight = z.infer<typeof insightSchema>;
export type Horizon = z.infer<typeof horizonSchema>;
