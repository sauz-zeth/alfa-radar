import type { EndpointOptions, Requester } from "../client";
import {
  categorySchema,
  categoryWeightRequestSchema,
  counterpartyRenameRequestSchema,
  counterpartySchema,
  notificationSettingsSchema,
  notificationTriggerSchema,
  profileBundleSchema,
  profileUpdateRequestSchema,
  reportingFilesSchema,
  reportingResponseSchema,
  type CategoryWeightRequest,
  type CounterpartyRenameRequest,
  type NotificationSettings,
  type ProfileUpdateRequest,
  type ReportingFiles,
} from "../schemas";

export function createProfileEndpoints(request: Requester) {
  return {
    get: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/profile",
        responseSchema: profileBundleSchema,
        signal: options.signal,
      }),

    update: (body: ProfileUpdateRequest, options: EndpointOptions = {}) =>
      request({
        method: "PATCH",
        path: "/api/profile",
        body,
        bodySchema: profileUpdateRequestSchema,
        responseSchema: profileBundleSchema,
        signal: options.signal,
      }),

    updateNotifications: (
      body: NotificationSettings,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "PATCH",
        path: "/api/profile/notifications",
        body,
        bodySchema: notificationSettingsSchema,
        responseSchema: notificationTriggerSchema.array(),
        signal: options.signal,
      }),

    categories: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/profile/categories",
        responseSchema: categorySchema.array(),
        signal: options.signal,
      }),

    patchCategory: (
      categoryId: number,
      body: CategoryWeightRequest,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "PATCH",
        path: `/api/profile/categories/${categoryId}`,
        body,
        bodySchema: categoryWeightRequestSchema,
        responseSchema: categorySchema.array(),
        signal: options.signal,
      }),

    counterparties: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/profile/counterparties",
        responseSchema: counterpartySchema.array(),
        signal: options.signal,
      }),

    renameCounterparty: (
      counterpartyId: string,
      body: CounterpartyRenameRequest,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "PATCH",
        path: `/api/profile/counterparties/${encodeURIComponent(counterpartyId)}`,
        body,
        bodySchema: counterpartyRenameRequestSchema,
        responseSchema: counterpartySchema.array(),
        signal: options.signal,
      }),

    reporting: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/profile/reporting",
        responseSchema: reportingResponseSchema,
        signal: options.signal,
      }),

    uploadReporting: (files: ReportingFiles, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/profile/reporting",
        form: files,
        formSchema: reportingFilesSchema,
        responseSchema: reportingResponseSchema,
        signal: options.signal,
      }),
  };
}

export type ProfileApi = ReturnType<typeof createProfileEndpoints>;
