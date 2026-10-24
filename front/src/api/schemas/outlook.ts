import { z } from "zod";

export const outlookStatusSchema = z.enum([
  "draft",
  "sent",
  "delivered",
  "read",
  "replied",
]);

export const outlookImportanceSchema = z.enum(["normal", "high"]);

export const outlookRecipientSchema = z.object({
  name: z.string().default(""),
  email: z.string(),
});

export const outlookContactSchema = z.object({
  name: z.string(),
  email: z.string(),
  role: z.string(),
  source: z.string(),
});

export const outlookContactListSchema = z.object({
  items: z.array(outlookContactSchema),
});

export const outlookMessageSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  action_id: z.string().nullish(),
  subject: z.string(),
  body: z.string(),
  to: z.array(outlookRecipientSchema),
  cc: z.array(outlookRecipientSchema).default([]),
  importance: outlookImportanceSchema.default("normal"),
  due_at: z.string().nullish(),
  status: outlookStatusSchema,
  status_label: z.string(),
  thread_id: z.string(),
  attachment_name: z.string().nullish(),
  reminder_count: z.number().int().default(0),
  created_at: z.string(),
  updated_at: z.string(),
  sent_at: z.string().nullish(),
  read_at: z.string().nullish(),
  replied_at: z.string().nullish(),
  last_reminder_at: z.string().nullish(),
});

export const outlookStateSchema = z.object({
  connected: z.boolean(),
  provider: z.string().default("mock"),
  email: z.string().nullish(),
  scopes: z.array(z.string()).default([]),
  demo: z.boolean().default(true),
  messages: z.array(outlookMessageSchema).default([]),
});

export const outlookConnectRequestSchema = z.object({
  email: z.string().min(3).max(255),
});

export const outlookMessageCreateSchema = z.object({
  event_id: z.string().min(1),
  action_id: z.string().max(128).nullish(),
  to: z.array(outlookRecipientSchema).min(1),
  cc: z.array(outlookRecipientSchema).default([]),
  subject: z.string().min(1).max(255),
  body: z.string().min(1).max(20000),
  importance: outlookImportanceSchema.default("normal"),
  due_at: z.string().max(64).nullish(),
  attach_report: z.boolean().default(true),
  send_now: z.boolean().default(false),
});

export const outlookMessagePatchSchema = z.object({
  to: z.array(outlookRecipientSchema).nullish(),
  cc: z.array(outlookRecipientSchema).nullish(),
  subject: z.string().min(1).max(255).nullish(),
  body: z.string().min(1).max(20000).nullish(),
  importance: outlookImportanceSchema.nullish(),
  due_at: z.string().max(64).nullish(),
});

export const outlookStateQuerySchema = z.object({
  event_id: z.string().optional(),
});

export const outlookContactsQuerySchema = z.object({
  q: z.string().max(128).optional(),
});

export type OutlookStatus = z.infer<typeof outlookStatusSchema>;
export type OutlookImportance = z.infer<typeof outlookImportanceSchema>;
export type OutlookRecipient = z.infer<typeof outlookRecipientSchema>;
export type OutlookContact = z.infer<typeof outlookContactSchema>;
export type OutlookContactList = z.infer<typeof outlookContactListSchema>;
export type OutlookMessage = z.infer<typeof outlookMessageSchema>;
export type OutlookState = z.infer<typeof outlookStateSchema>;
export type OutlookConnectRequest = z.infer<typeof outlookConnectRequestSchema>;
export type OutlookMessageCreate = z.infer<typeof outlookMessageCreateSchema>;
export type OutlookMessagePatch = z.infer<typeof outlookMessagePatchSchema>;
export type OutlookStateQuery = z.infer<typeof outlookStateQuerySchema>;
export type OutlookContactsQuery = z.infer<typeof outlookContactsQuerySchema>;
