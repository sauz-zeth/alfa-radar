import type { EndpointOptions, Requester } from "../client";
import {
  searchHistoryResponseSchema,
  searchQuerySchema,
  searchResponseSchema,
  type SearchQuery,
} from "../schemas";

export function createSearchEndpoints(request: Requester) {
  return {
    search: (query: SearchQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/search",
        query,
        querySchema: searchQuerySchema,
        responseSchema: searchResponseSchema,
        signal: options.signal,
      }),

    history: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/search/history",
        responseSchema: searchHistoryResponseSchema,
        signal: options.signal,
      }),

    clearHistory: (options: EndpointOptions = {}) =>
      request({
        method: "DELETE",
        path: "/api/search/history",
        responseSchema: searchHistoryResponseSchema,
        signal: options.signal,
      }),

    deleteHistoryItem: (itemId: string, options: EndpointOptions = {}) =>
      request({
        method: "DELETE",
        path: `/api/search/history/${encodeURIComponent(itemId)}`,
        responseSchema: searchHistoryResponseSchema,
        signal: options.signal,
      }),
  };
}

export type SearchApi = ReturnType<typeof createSearchEndpoints>;
