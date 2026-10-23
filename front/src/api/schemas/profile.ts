import { z } from "zod";

import { unknownRecordSchema } from "./common";
import {
  categorySchema,
  counterpartySchema,
  profileSchema,
} from "./onboarding";

export const profileStatsSchema = z.object({
  industry: z.string().nullish(),
  city: z.string().nullish(),
  region: z.string().nullish(),
  revenue: z.number().nullish(),
  revenue_label: z.string(),
  revenue_segment: z.string().nullish(),
  employees: z.string().nullish(),
  age: z.string().nullish(),
  foreign_trade_country: z.string().nullish(),
  products: z.array(z.string()).default([]),
  tags: z.array(z.string()).default([]),
});

export const categoryGroupSchema = z.object({
  key: z.string(),
  name: z.string(),
  description: z.string(),
  weight_min: z.number(),
  weight_max: z.number(),
  items: z.array(categorySchema),
});

export const notificationTriggerSchema = z.object({
  key: z.string(),
  label: z.string(),
  channel: z.string(),
  enabled: z.boolean().default(true),
});

export const profileBundleSchema = z.object({
  profile: profileSchema,
  stats: profileStatsSchema,
  category_groups: z.array(categoryGroupSchema),
  categories: z.array(categorySchema),
  counterparties: z.array(counterpartySchema),
  counterparties_by_direction: z
    .record(z.string(), z.array(counterpartySchema))
    .default({}),
  notifications: z.array(notificationTriggerSchema).default([]),
  reporting: unknownRecordSchema,
});

export const notificationSettingsSchema = z.record(z.string(), z.boolean());

export type ProfileStats = z.infer<typeof profileStatsSchema>;
export type CategoryGroup = z.infer<typeof categoryGroupSchema>;
export type NotificationTrigger = z.infer<typeof notificationTriggerSchema>;
export type ProfileBundle = z.infer<typeof profileBundleSchema>;
export type NotificationSettings = z.infer<typeof notificationSettingsSchema>;
