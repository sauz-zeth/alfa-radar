import { z } from "zod";

export const healthResponseSchema = z.object({
  status: z.string(),
  environment: z.string(),
});

export const healthDbResponseSchema = z.object({
  status: z.string(),
  database: z.string(),
});

export const rootResponseSchema = z.object({
  service: z.string(),
  docs: z.string(),
  openapi: z.string(),
  api_prefix: z.string(),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type HealthDbResponse = z.infer<typeof healthDbResponseSchema>;
export type RootResponse = z.infer<typeof rootResponseSchema>;
