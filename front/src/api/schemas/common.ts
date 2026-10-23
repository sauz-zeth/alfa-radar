import { z } from "zod";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export const pageSchema = <T extends z.ZodType>(
  item: T,
): z.ZodType<Page<z.infer<T>>> =>
  z.object({
    items: z.array(item),
    total: z.number().int(),
    limit: z.number().int(),
    offset: z.number().int(),
  });

export const unknownRecordSchema = z.record(z.string(), z.unknown());

export const okSchema = z.object({
  ok: z.boolean(),
});

export type OkResponse = z.infer<typeof okSchema>;
