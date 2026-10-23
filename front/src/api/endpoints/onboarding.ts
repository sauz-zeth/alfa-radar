import type { EndpointOptions, Requester } from "../client";
import {
  businessSelectRequestSchema,
  categorySchema,
  categoryWeightRequestSchema,
  counterpartyRenameBatchSchema,
  counterpartySchema,
  onboardingStateSchema,
  profileUpdateRequestSchema,
  reportingFilesSchema,
  reportingResponseSchema,
  roleRequestSchema,
  skipStepRequestSchema,
  type BusinessSelectRequest,
  type CategoryWeightRequest,
  type CounterpartyRenameBatch,
  type ProfileUpdateRequest,
  type ReportingFiles,
  type RoleRequest,
  type SkipStepRequest,
} from "../schemas";

export function createOnboardingEndpoints(request: Requester) {
  return {
    state: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/onboarding/state",
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),

    business: (body: BusinessSelectRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/business",
        body,
        bodySchema: businessSelectRequestSchema,
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),

    profile: (body: ProfileUpdateRequest, options: EndpointOptions = {}) =>
      request({
        method: "PATCH",
        path: "/api/onboarding/profile",
        body,
        bodySchema: profileUpdateRequestSchema,
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),

    role: (body: RoleRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/role",
        body,
        bodySchema: roleRequestSchema,
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),

    skip: (body: SkipStepRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/skip",
        body,
        bodySchema: skipStepRequestSchema,
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),

    counterparties: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/onboarding/counterparties",
        responseSchema: counterpartySchema.array(),
        signal: options.signal,
      }),

    suggestCounterparties: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/counterparties/suggest",
        responseSchema: counterpartySchema.array(),
        signal: options.signal,
      }),

    renameCounterparties: (
      body: CounterpartyRenameBatch,
      options: EndpointOptions = {},
    ) =>
      request({
        method: "PATCH",
        path: "/api/onboarding/counterparties",
        body,
        bodySchema: counterpartyRenameBatchSchema,
        responseSchema: counterpartySchema.array(),
        signal: options.signal,
      }),

    categories: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/onboarding/categories",
        responseSchema: categorySchema.array(),
        signal: options.signal,
      }),

    suggestCategories: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/categories/suggest",
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
        path: `/api/onboarding/categories/${categoryId}`,
        body,
        bodySchema: categoryWeightRequestSchema,
        responseSchema: categorySchema.array(),
        signal: options.signal,
      }),

    reporting: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/onboarding/reporting",
        responseSchema: reportingResponseSchema,
        signal: options.signal,
      }),

    uploadReporting: (files: ReportingFiles, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/reporting",
        form: files,
        formSchema: reportingFilesSchema,
        responseSchema: reportingResponseSchema,
        signal: options.signal,
      }),

    complete: (options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/onboarding/complete",
        responseSchema: onboardingStateSchema,
        signal: options.signal,
      }),
  };
}

export type OnboardingApi = ReturnType<typeof createOnboardingEndpoints>;
