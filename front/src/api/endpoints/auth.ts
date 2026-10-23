import type { EndpointOptions, Requester } from "../client";
import {
  loginRequestSchema,
  registerRequestSchema,
  tokenResponseSchema,
  type LoginRequest,
  type RegisterRequest,
} from "../schemas/auth";

export function createAuthEndpoints(request: Requester) {
  return {
    register: (body: RegisterRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/auth/register",
        body,
        bodySchema: registerRequestSchema,
        responseSchema: tokenResponseSchema,
        signal: options.signal,
      }),

    login: (body: LoginRequest, options: EndpointOptions = {}) =>
      request({
        method: "POST",
        path: "/api/auth/login",
        body,
        bodySchema: loginRequestSchema,
        responseSchema: tokenResponseSchema,
        signal: options.signal,
      }),

    me: (options: EndpointOptions = {}) =>
      request({
        method: "GET",
        path: "/api/auth/me",
        responseSchema: tokenResponseSchema,
        signal: options.signal,
      }),
  };
}

export type AuthApi = ReturnType<typeof createAuthEndpoints>;
