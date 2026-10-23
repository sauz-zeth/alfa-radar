import type { EndpointOptions, Requester } from "../client";
import {
  healthDbResponseSchema,
  healthResponseSchema,
  rootResponseSchema,
} from "../schemas";

export function createHealthEndpoints(request: Requester) {
  return {
    get: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/health",
        responseSchema: healthResponseSchema,
        auth: false,
        signal: options.signal,
      }),

    db: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/health/db",
        responseSchema: healthDbResponseSchema,
        auth: false,
        signal: options.signal,
      }),

    root: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/",
        responseSchema: rootResponseSchema,
        auth: false,
        signal: options.signal,
      }),
  };
}

export type HealthApi = ReturnType<typeof createHealthEndpoints>;
