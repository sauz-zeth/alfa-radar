import { z } from "zod";

export const searchCompanySchema = z.object({
  uid: z.string(),
  name: z.string(),
  role: z.string(),
  city: z.string().nullish(),
  region: z.string().nullish(),
  okved: z.string().nullish(),
  revenue: z.number().nullish(),
  revenue_segment: z.string(),
  initials: z.string(),
});

export const searchNewsSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  impact: z.string(),
  impact_label: z.string(),
  importance: z.number().int(),
  published_at: z.string(),
  source_name: z.string(),
  source_count: z.number().int().default(1),
  is_hidden: z.boolean().default(false),
  is_tracked: z.boolean().default(false),
});

export const searchResponseSchema = z.object({
  query: z.string(),
  companies: z.array(searchCompanySchema),
  news: z.array(searchNewsSchema),
  total_companies: z.number().int(),
  total_news: z.number().int(),
});

export const searchHistoryItemSchema = z.object({
  id: z.string(),
  query: z.string(),
  created_at: z.string(),
});

export const searchHistoryResponseSchema = z.object({
  items: z.array(searchHistoryItemSchema),
});

export const searchQuerySchema = z.object({
  q: z.string().max(200).optional(),
});

export type SearchCompany = z.infer<typeof searchCompanySchema>;
export type SearchNews = z.infer<typeof searchNewsSchema>;
export type SearchResponse = z.infer<typeof searchResponseSchema>;
export type SearchHistoryItem = z.infer<typeof searchHistoryItemSchema>;
export type SearchHistoryResponse = z.infer<typeof searchHistoryResponseSchema>;
export type SearchQuery = z.infer<typeof searchQuerySchema>;
