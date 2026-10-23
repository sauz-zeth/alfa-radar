import { z } from "zod";

import { businessSchema } from "./business";
import { unknownRecordSchema } from "./common";

export const roleSchema = z.enum([
  "owner",
  "ceo",
  "cfo",
  "chief_accountant",
  "treasurer",
  "c_level",
  "other_decision_maker",
]);

export const categorySchema = z.object({
  category_id: z.number().int(),
  slug: z.string(),
  name: z.string(),
  short_name: z.string(),
  group: z.string(),
  description: z.string(),
  example: z.string(),
  channels: z.array(z.string()),
  weight: z.number(),
  rationale: z.string(),
  is_manual: z.boolean(),
});

export const counterpartySchema = z.object({
  id: z.string(),
  company_uid: z.string().nullish(),
  direction: z.string(),
  total_amount: z.number(),
  payments_count: z.number().int(),
  share: z.number(),
  importance: z.number().int(),
  default_name: z.string(),
  custom_name: z.string().nullish(),
  display_name: z.string(),
  note: z.string(),
});

export const counterpartyRenameItemSchema = z.object({
  id: z.string(),
  name: z.string().max(128).nullish(),
});

export const counterpartyRenameBatchSchema = z.object({
  items: z.array(counterpartyRenameItemSchema),
});

export const counterpartyRenameRequestSchema = z.object({
  name: z.string().max(128).nullish(),
});

export const profileSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  company_uid: z.string().nullish(),
  entrepreneur_name: z.string(),
  business_name: z.string(),
  role: z.string().nullish(),
  role_label: z.string().nullish(),
  tags: z.array(z.string()).default([]),
  onboarding_step: z.string(),
  onboarding_completed: z.boolean(),
  reporting_summary: unknownRecordSchema.default({}),
  company: businessSchema.nullish(),
});

export const profileUpdateRequestSchema = z.object({
  entrepreneur_name: z.string().max(128).nullish(),
  business_name: z.string().max(255).nullish(),
  role: roleSchema.nullish(),
});

export const roleRequestSchema = z.object({
  role: roleSchema,
});

export const categoryWeightRequestSchema = z.object({
  weight: z.number().min(0).max(1),
});

export const onboardingStepStateSchema = z.object({
  key: z.string(),
  title: z.string(),
  done: z.boolean(),
  optional: z.boolean().default(false),
});

export const onboardingStateSchema = z.object({
  completed: z.boolean(),
  next_step: z.string(),
  steps: z.array(onboardingStepStateSchema),
  profile: profileSchema.nullish(),
});

export const reportingUploadSchema = z.object({
  id: z.string(),
  form_type: z.string(),
  filename: z.string(),
  content_type: z.string().nullish(),
  extracted: unknownRecordSchema,
  status: z.string(),
});

export const reportingResponseSchema = z.object({
  uploads: z.array(reportingUploadSchema),
  summary: unknownRecordSchema,
  accepted_forms: z.array(z.string()),
});

export const skipStepRequestSchema = z.object({
  step: z.string(),
});

export const reportingFileSchema = z.custom<Blob>(
  (value) => typeof Blob !== "undefined" && value instanceof Blob,
  "Ожидается файл",
);

export const reportingFilesSchema = z
  .object({
    balance: reportingFileSchema.optional(),
    income: reportingFileSchema.optional(),
    cash_flow: reportingFileSchema.optional(),
  })
  .refine((value) => Boolean(value.balance || value.income || value.cash_flow), {
    message: "Загрузите хотя бы одну форму отчётности",
  });

export type Role = z.infer<typeof roleSchema>;
export type Category = z.infer<typeof categorySchema>;
export type Counterparty = z.infer<typeof counterpartySchema>;
export type CounterpartyRenameItem = z.infer<typeof counterpartyRenameItemSchema>;
export type CounterpartyRenameBatch = z.infer<typeof counterpartyRenameBatchSchema>;
export type CounterpartyRenameRequest = z.infer<typeof counterpartyRenameRequestSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type ProfileUpdateRequest = z.infer<typeof profileUpdateRequestSchema>;
export type RoleRequest = z.infer<typeof roleRequestSchema>;
export type CategoryWeightRequest = z.infer<typeof categoryWeightRequestSchema>;
export type OnboardingStepState = z.infer<typeof onboardingStepStateSchema>;
export type OnboardingState = z.infer<typeof onboardingStateSchema>;
export type ReportingUpload = z.infer<typeof reportingUploadSchema>;
export type ReportingResponse = z.infer<typeof reportingResponseSchema>;
export type SkipStepRequest = z.infer<typeof skipStepRequestSchema>;
export type ReportingFiles = z.infer<typeof reportingFilesSchema>;
