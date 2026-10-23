import type { EndpointOptions, Requester } from "../client";
import {
  agentReanalyzeRequestSchema,
  scenarioSetSchema,
  scenariosQuerySchema,
  trackedItemSchema,
  trackedListQuerySchema,
  trackedListResponseSchema,
  trackedQuestionRequestSchema,
  type AgentReanalyzeRequest,
  type ScenariosQuery,
  type TrackedListQuery,
  type TrackedQuestionRequest,
} from "../schemas";

export function createTrackedEndpoints(request: Requester) {
  return {
    list: (query: TrackedListQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/tracked",
        query,
        querySchema: trackedListQuerySchema,
        responseSchema: trackedListResponseSchema,
        signal: options.signal,
      }),

    detail: (itemId: string, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: `/api/tracked/${encodeURIComponent(itemId)}`,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    remove: (itemId: string, options: EndpointOptions = {}) =>
      request<void>({
        method: "DELETE",
        path: `/api/tracked/${encodeURIComponent(itemId)}`,
        signal: options.signal,
      }),

    archive: (itemId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/tracked/${encodeURIComponent(itemId)}/archive`,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    resume: (itemId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/tracked/${encodeURIComponent(itemId)}/resume`,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    questions: (
      itemId: string,
      body: TrackedQuestionRequest,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "POST",
        path: `/api/tracked/${encodeURIComponent(itemId)}/questions`,
        body,
        bodySchema: trackedQuestionRequestSchema,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    reanalyze: (
      itemId: string,
      body: AgentReanalyzeRequest = {},
      options: EndpointOptions = {},
    ) =>
      request({
        method: "POST",
        path: `/api/tracked/${encodeURIComponent(itemId)}/reanalyze`,
        body,
        bodySchema: agentReanalyzeRequestSchema,
        responseSchema: trackedItemSchema,
        signal: options.signal,
      }),

    scenarios: (
      itemId: string,
      query: ScenariosQuery = {},
      options: EndpointOptions = {},
    ) =>
      request({
        method: "GET",
        path: `/api/tracked/${encodeURIComponent(itemId)}/scenarios`,
        query,
        querySchema: scenariosQuerySchema,
        responseSchema: scenarioSetSchema,
        signal: options.signal,
      }),
  };
}

export type TrackedApi = ReturnType<typeof createTrackedEndpoints>;
