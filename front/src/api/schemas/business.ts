import { z } from "zod";

export const businessListItemSchema = z.object({
  uid: z.string(),
  org_type: z.string().nullish(),
  eco_mark_label: z.string().nullish(),
  main_okved_code: z.string().nullish(),
  main_okved_name: z.string().nullish(),
  amount_workers_fns_gradation: z.string().nullish(),
  revenue: z.number().nullish(),
  revenue_segment: z.string(),
  city: z.string().nullish(),
  region: z.string().nullish(),
  fts_country_name: z.string().nullish(),
  cl_product_rko_mark: z.boolean().default(false),
  cl_product_loa_mark: z.boolean().default(false),
  tags: z.array(z.string()).default([]),
});

export const businessSchema = businessListItemSchema.extend({
  okfs_name: z.string().nullish(),
  company_age_years_gradation: z.string().nullish(),
  negative_mark: z.number().nullish(),
  amount_workers_spark_gradation: z.string().nullish(),
  client_type: z.string().nullish(),
  cl_product_gar_mark: z.boolean().default(false),
  cl_product_lea_mark: z.boolean().default(false),
  cl_product_dep_mark: z.boolean().default(false),
  cl_product_zpp_mark: z.boolean().default(false),
  fts_flag: z.boolean().default(false),
  factoring_mark: z.boolean().default(false),
  group_id: z.string().nullish(),
});

export const businessOptionsResponseSchema = z.object({
  mode: z.string(),
  items: z.array(businessListItemSchema),
  total: z.number().int(),
});

export const businessSelectRequestSchema = z.object({
  uid: z.string(),
});

export const businessListQuerySchema = z.object({
  search: z.string().max(128).optional(),
  city: z.string().optional(),
  region: z.string().optional(),
  segment: z.string().optional(),
  okved: z.string().optional(),
  product: z.string().optional(),
  fts: z.boolean().optional(),
  min_revenue: z.number().optional(),
  max_revenue: z.number().optional(),
  limit: z.number().int().min(1).max(100).optional(),
  offset: z.number().int().min(0).optional(),
});

export const businessOptionsQuerySchema = z.object({
  search: z.string().max(128).optional(),
  limit: z.number().int().min(1).max(50).optional(),
});

export type BusinessListItem = z.infer<typeof businessListItemSchema>;
export type Business = z.infer<typeof businessSchema>;
export type BusinessOptionsResponse = z.infer<typeof businessOptionsResponseSchema>;
export type BusinessSelectRequest = z.infer<typeof businessSelectRequestSchema>;
export type BusinessListQuery = z.infer<typeof businessListQuerySchema>;
export type BusinessOptionsQuery = z.infer<typeof businessOptionsQuerySchema>;
