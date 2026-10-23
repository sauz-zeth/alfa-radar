import type { ZodError, z } from "zod";

import { createAuthEndpoints, type AuthApi } from "./endpoints/auth";
import { createBusinessesEndpoints, type BusinessesApi } from "./endpoints/businesses";
import { createFeedEndpoints, type FeedApi } from "./endpoints/feed";
import { createHealthEndpoints, type HealthApi } from "./endpoints/health";
import { createOnboardingEndpoints, type OnboardingApi } from "./endpoints/onboarding";
import { createProfileEndpoints, type ProfileApi } from "./endpoints/profile";
import { createSearchEndpoints, type SearchApi } from "./endpoints/search";
import { createSourcesEndpoints, type SourcesApi } from "./endpoints/sources";
import { createTrackedEndpoints, type TrackedApi } from "./endpoints/tracked";
import { ApiError } from "./errors";

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

export type TokenProvider = () => string | null | Promise<string | null>;

export interface ApiClientConfig {
  baseUrl?: string;
  getToken?: TokenProvider;
  fetch?: typeof fetch;
  validateResponses?: boolean;
  headers?: HeadersInit;
}

export interface EndpointOptions {
  signal?: AbortSignal;
}

export interface RequestOptions<T> {
  path: string;
  method?: HttpMethod;
  query?: QueryParams;
  querySchema?: z.ZodType;
  body?: unknown;
  bodySchema?: z.ZodType;
  form?: unknown;
  formSchema?: z.ZodType;
  responseSchema?: z.ZodType<T>;
  signal?: AbortSignal;
  auth?: boolean;
  headers?: HeadersInit;
}

export type Requester = <T>(options: RequestOptions<T>) => Promise<T>;

export interface ApiClient {
  request: Requester;
  auth: AuthApi;
  businesses: BusinessesApi;
  onboarding: OnboardingApi;
  profile: ProfileApi;
  feed: FeedApi;
  tracked: TrackedApi;
  sources: SourcesApi;
  search: SearchApi;
  health: HealthApi;
}

const JSON_CONTENT_TYPE = "application/json";

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function formatIssues(error: ZodError): string {
  return error.issues
    .map((issue) => `${issue.path.join(".") || "value"}: ${issue.message}`)
    .join("; ");
}

function appendQuery(search: URLSearchParams, query: QueryParams | undefined): void {
  if (!query) {
    return;
  }
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null) {
          search.append(key, String(item));
        }
      }
      continue;
    }
    search.append(key, String(value));
  }
}

function buildFormData(value: unknown): FormData {
  const form = new FormData();
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (item === undefined || item === null) {
      continue;
    }
    if (typeof Blob !== "undefined" && item instanceof Blob) {
      form.append(key, item);
    } else {
      form.append(key, String(item));
    }
  }
  return form;
}

function parsePayload(text: string): unknown {
  if (!text) {
    return undefined;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractDetail(payload: unknown, statusText: string): string {
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .filter(Boolean);
      if (messages.length > 0) {
        return messages.join("; ");
      }
    }
  }
  if (typeof payload === "object" && payload !== null) {
    return JSON.stringify(payload);
  }
  return statusText || "Ошибка запроса";
}

function createRequester(config: ApiClientConfig): Requester {
  const baseUrl = normalizeBaseUrl(config.baseUrl ?? "");
  const getToken = config.getToken;
  const fetchImpl =
    config.fetch ??
    ((input: RequestInfo | URL, init?: RequestInit) =>
      globalThis.fetch(input, init));
  const validateResponses = config.validateResponses ?? true;

  return async <T>(options: RequestOptions<T>): Promise<T> => {
    let query = options.query;
    if (options.querySchema) {
      const parsed = options.querySchema.safeParse(options.query ?? {});
      if (!parsed.success) {
        throw new ApiError({
          status: 0,
          detail: `Невалидные параметры запроса: ${formatIssues(parsed.error)}`,
          url: options.path,
          payload: options.query,
        });
      }
      query = parsed.data as QueryParams;
    }

    const search = new URLSearchParams();
    appendQuery(search, query);
    const queryString = search.toString();
    const url = `${baseUrl}${options.path}${queryString ? `?${queryString}` : ""}`;

    let body: BodyInit | undefined;
    let jsonBody = false;
    if (options.form !== undefined || options.formSchema !== undefined) {
      let formValue = options.form;
      if (options.formSchema) {
        const parsed = options.formSchema.safeParse(options.form ?? {});
        if (!parsed.success) {
          throw new ApiError({
            status: 0,
            detail: `Невалидные данные запроса: ${formatIssues(parsed.error)}`,
            url,
            payload: options.form,
          });
        }
        formValue = parsed.data;
      }
      body = buildFormData(formValue);
    } else if (options.body !== undefined) {
      let bodyValue: unknown = options.body;
      if (options.bodySchema) {
        const parsed = options.bodySchema.safeParse(options.body);
        if (!parsed.success) {
          throw new ApiError({
            status: 0,
            detail: `Невалидные данные запроса: ${formatIssues(parsed.error)}`,
            url,
            payload: options.body,
          });
        }
        bodyValue = parsed.data;
      }
      body = JSON.stringify(bodyValue);
      jsonBody = true;
    }

    const headers = new Headers(config.headers);
    new Headers(options.headers).forEach((value, key) => headers.set(key, value));
    if (!headers.has("Accept")) {
      headers.set("Accept", JSON_CONTENT_TYPE);
    }
    if (jsonBody) {
      headers.set("Content-Type", JSON_CONTENT_TYPE);
    }
    if (options.auth !== false && getToken) {
      const token = await getToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    const response = await fetchImpl(url, {
      method: options.method ?? "GET",
      headers,
      body,
      signal: options.signal,
    });

    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    const payload = parsePayload(text);

    if (!response.ok) {
      throw new ApiError({
        status: response.status,
        detail: extractDetail(payload, response.statusText),
        url,
        payload,
      });
    }

    if (!text) {
      return undefined as T;
    }

    if (options.responseSchema && validateResponses) {
      const parsed = options.responseSchema.safeParse(payload);
      if (!parsed.success) {
        throw new ApiError({
          status: response.status,
          detail: `Невалидный ответ API: ${formatIssues(parsed.error)}`,
          url,
          payload,
        });
      }
      return parsed.data;
    }

    return payload as T;
  };
}

export function createApiClient(config: ApiClientConfig = {}): ApiClient {
  const request = createRequester(config);
  return {
    request,
    auth: createAuthEndpoints(request),
    businesses: createBusinessesEndpoints(request),
    onboarding: createOnboardingEndpoints(request),
    profile: createProfileEndpoints(request),
    feed: createFeedEndpoints(request),
    tracked: createTrackedEndpoints(request),
    sources: createSourcesEndpoints(request),
    search: createSearchEndpoints(request),
    health: createHealthEndpoints(request),
  };
}
