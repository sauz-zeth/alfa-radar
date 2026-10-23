import type { EndpointOptions, Requester } from "../client";
import {
  businessListItemSchema,
  businessListQuerySchema,
  businessOptionsQuerySchema,
  businessOptionsResponseSchema,
  businessSchema,
  pageSchema,
  type BusinessListQuery,
  type BusinessOptionsQuery,
} from "../schemas";

export function createBusinessesEndpoints(request: Requester) {
  return {
    list: (query: BusinessListQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/businesses",
        query,
        querySchema: businessListQuerySchema,
        responseSchema: pageSchema(businessListItemSchema),
        signal: options.signal,
      }),

    options: (query: BusinessOptionsQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/businesses/options",
        query,
        querySchema: businessOptionsQuerySchema,
        responseSchema: businessOptionsResponseSchema,
        signal: options.signal,
      }),

    byUid: (uid: string, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: `/api/businesses/${encodeURIComponent(uid)}`,
        responseSchema: businessSchema,
        signal: options.signal,
      }),
  };
}

export type BusinessesApi = ReturnType<typeof createBusinessesEndpoints>;
