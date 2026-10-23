import type { EndpointOptions, Requester } from "../client";
import {
  feedbackRequestSchema,
  feedItemDetailSchema,
  feedItemSchema,
  feedListQuerySchema,
  hiddenQuerySchema,
  hiddenResponseSchema,
  likeResponseSchema,
  okSchema,
  pageSchema,
  scenarioSetSchema,
  scenariosQuerySchema,
  trackedItemSchema,
  type FeedbackRequest,
  type FeedListQuery,
  type HiddenQuery,
  type ScenariosQuery,
} from "../schemas";

export function createFeedEndpoints(request: Requester) {
  return {
    list: (query: FeedListQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/feed",
        query,
        querySchema: feedListQuerySchema,
        responseSchema: pageSchema(feedItemSchema),
        signal: options.signal,
      }),

    hidden: (query: HiddenQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/feed/hidden",
        query,
        querySchema: hiddenQuerySchema,
        responseSchema: hiddenResponseSchema,
        signal: options.signal,
      }),

    restore: (eventId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/restore`,
        responseSchema: okSchema,
        signal: options.signal,
      }),

    like: (eventId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/like`,
        responseSchema: likeResponseSchema,
        signal: options.signal,
      }),

    detail: (eventId: string, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: `/api/feed/${encodeURIComponent(eventId)}`,
        responseSchema: feedItemDetailSchema,
        signal: options.signal,
      }),

    scenarios: (
      eventId: string,
      query: ScenariosQuery = {},
      options: EndpointOptions = {},
    ) =>
      request({
        method: "GET",
        path: `/api/feed/${encodeURIComponent(eventId)}/scenarios`,
        query,
        querySchema: scenariosQuerySchema,
        responseSchema: scenarioSetSchema,
        signal: options.signal,
      }),

    track: (eventId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/track`,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    feedback: (
      eventId: string,
      body: FeedbackRequest,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/feedback`,
        body,
        bodySchema: feedbackRequestSchema,
        responseSchema: okSchema,
        signal: options.signal,
      }),
  };
}

export type FeedApi = ReturnType<typeof createFeedEndpoints>;
