import type { EndpointOptions, Requester } from "../client";
import {
  outlookConnectRequestSchema,
  outlookContactListSchema,
  outlookContactsQuerySchema,
  outlookMessageCreateSchema,
  outlookMessagePatchSchema,
  outlookMessageSchema,
  outlookStateQuerySchema,
  outlookStateSchema,
  type OutlookConnectRequest,
  type OutlookContactsQuery,
  type OutlookMessageCreate,
  type OutlookMessagePatch,
  type OutlookStateQuery,
} from "../schemas";

export function createOutlookEndpoints(request: Requester) {
  return {
    state: (query: OutlookStateQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/outlook",
        query,
        querySchema: outlookStateQuerySchema,
        responseSchema: outlookStateSchema,
        signal: options.signal,
      }),

    connect: (body: OutlookConnectRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/outlook/connect",
        body,
        bodySchema: outlookConnectRequestSchema,
        responseSchema: outlookStateSchema,
        signal: options.signal,
      }),

    disconnect: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/outlook/disconnect",
        responseSchema: outlookStateSchema,
        signal: options.signal,
      }),

    contacts: (query: OutlookContactsQuery = {}, options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/outlook/contacts",
        query,
        querySchema: outlookContactsQuerySchema,
        responseSchema: outlookContactListSchema,
        signal: options.signal,
      }),

    createMessage: (body: OutlookMessageCreate, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/outlook/messages",
        body,
        bodySchema: outlookMessageCreateSchema,
        responseSchema: outlookMessageSchema,
        signal: options.signal,
      }),

    updateMessage: (
      messageId: string,
      body: OutlookMessagePatch,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "PATCH",
        path: `/api/outlook/messages/${encodeURIComponent(messageId)}`,
        body,
        bodySchema: outlookMessagePatchSchema,
        responseSchema: outlookMessageSchema,
        signal: options.signal,
      }),

    deleteMessage: (messageId: string, options: EndpointOptions = {}) =>
      request<void>({
        method: "DELETE",
        path: `/api/outlook/messages/${encodeURIComponent(messageId)}`,
        signal: options.signal,
      }),

    send: (messageId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/outlook/messages/${encodeURIComponent(messageId)}/send`,
        responseSchema: outlookMessageSchema,
        signal: options.signal,
      }),

    remind: (messageId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/outlook/messages/${encodeURIComponent(messageId)}/remind`,
        responseSchema: outlookMessageSchema,
        signal: options.signal,
      }),

    advance: (messageId: string, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: `/api/outlook/messages/${encodeURIComponent(messageId)}/advance`,
        responseSchema: outlookMessageSchema,
        signal: options.signal,
      }),
  };
}

export type OutlookApi = ReturnType<typeof createOutlookEndpoints>;
