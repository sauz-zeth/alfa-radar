import type { EndpointOptions, Requester } from "../client";
import {
  catalogQuerySchema,
  channelAddRequestSchema,
  channelCatalogResponseSchema,
  sourcesStateSchema,
  type CatalogQuery,
  type ChannelAddRequest,
} from "../schemas";

export function createSourcesEndpoints(request: Requester) {
  return {
    state: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/sources",
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),

    catalog: (query: CatalogQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/sources/catalog",
        query,
        querySchema: catalogQuerySchema,
        responseSchema: channelCatalogResponseSchema,
        signal: options.signal,
      }),

    addChannel: (body: ChannelAddRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/sources/channels",
        body,
        bodySchema: channelAddRequestSchema,
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),

    subscribe: (channelId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/sources/channels/${encodeURIComponent(channelId)}/subscribe`,
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),

    unsubscribe: (channelId: string, options: EndpointOptions = {}) =>
      request({
        method: "DELETE",
        path: `/api/sources/channels/${encodeURIComponent(channelId)}`,
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),

    unsubscribeAll: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/sources/channels/unsubscribe-all",
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),

    restore: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/sources/channels/restore",
        responseSchema: sourcesStateSchema,
        signal: options.signal,
      }),
  };
}

export type SourcesApi = ReturnType<typeof createSourcesEndpoints>;
