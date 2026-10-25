import { z } from "zod";

export const channelSchema = z.object({
  id: z.string(),
  name: z.string(),
  handle: z.string().nullish(),
  topics: z.string(),
  kind: z.string().default("catalog"),
  subscribed: z.boolean().default(false),
  recommended: z.boolean().default(false),
  avatar_url: z.string().nullish(),
  feed_url: z.string().nullish(),
  source_type: z.enum(["telegram", "rss"]).default("telegram"),
  tg_subscribers: z.number().int().nullish(),
});

export const sourcesStateSchema = z.object({
  channels: z.array(channelSchema),
  alfa_analytics: z.boolean().default(true),
  recommended_count: z.number().int(),
  custom_count: z.number().int(),
  catalog_total: z.number().int(),
});

export const channelCatalogResponseSchema = z.object({
  query: z.string(),
  items: z.array(channelSchema),
  total: z.number().int(),
});

export const channelAddRequestSchema = z.object({
  query: z.string().min(1).max(200),
});

export const catalogQuerySchema = z.object({
  q: z.string().max(200).optional(),
});

export type Channel = z.infer<typeof channelSchema>;
export type SourcesState = z.infer<typeof sourcesStateSchema>;
export type ChannelCatalogResponse = z.infer<typeof channelCatalogResponseSchema>;
export type ChannelAddRequest = z.infer<typeof channelAddRequestSchema>;
export type CatalogQuery = z.infer<typeof catalogQuerySchema>;
