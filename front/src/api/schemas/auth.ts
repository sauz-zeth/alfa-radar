import { z } from "zod";

export const registerRequestSchema = z.object({
  login: z
    .string()
    .min(3)
    .max(64)
    .regex(/^[A-Za-z0-9_.-]+$/),
  password: z.string().min(6).max(128),
});

export const loginRequestSchema = z.object({
  login: z.string(),
  password: z.string(),
});

export const userSchema = z.object({
  id: z.string(),
  login: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
});

export const onboardingBriefSchema = z.object({
  completed: z.boolean(),
  next_step: z.string(),
});

export const tokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default("bearer"),
  user: userSchema,
  onboarding: onboardingBriefSchema,
});

export type RegisterRequest = z.infer<typeof registerRequestSchema>;
export type LoginRequest = z.infer<typeof loginRequestSchema>;
export type User = z.infer<typeof userSchema>;
export type OnboardingBrief = z.infer<typeof onboardingBriefSchema>;
export type TokenResponse = z.infer<typeof tokenResponseSchema>;
