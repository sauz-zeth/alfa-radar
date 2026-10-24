import { z } from "zod";

import type { EndpointOptions, Requester, Streamer } from "../client";
import {
  feedbackRequestSchema,
  feedItemDetailSchema,
  feedQuestionRequestSchema,
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
  type FeedQuestionRequest,
  type HiddenQuery,
  type ScenariosQuery,
} from "../schemas";

export function createFeedEndpoints(request: Requester, stream: Streamer) {
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

    askQuestion: (
      eventId: string,
      body: FeedQuestionRequest,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/questions`,
        body,
        bodySchema: feedQuestionRequestSchema,
        responseSchema: feedItemDetailSchema,
        signal: options.signal,
      }),

    askQuestionStream: (
      eventId: string,
      body: FeedQuestionRequest,
      options: EndpointOptions = {},
    ) =>
      stream({
        method: "POST",
        path: `/api/feed/${encodeURIComponent(eventId)}/questions/stream`,
        body,
        bodySchema: feedQuestionRequestSchema,
        signal: options.signal,
      }),

    untrack: (eventId: string, options: EndpointOptions = {}) =>
      request({
        method: "DELETE",
        path: `/api/feed/${encodeURIComponent(eventId)}/track`,
        responseSchema: z.object({ is_tracked: z.boolean() }),
        signal: options.signal,
      }),
  };
}

export type FeedApi = ReturnType<typeof createFeedEndpoints>;
