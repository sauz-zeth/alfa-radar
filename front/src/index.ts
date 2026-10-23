import { serve } from "bun";
import index from "./index.html";

const PROXY_TARGET = process.env.PROXY_TARGET ?? "http://localhost:8000";
const PROXY_PREFIX = "/api";

async function proxy(request: Request): Promise<Response> {
  const { pathname, search } = new URL(request.url);
  const target = new URL(pathname + search, PROXY_TARGET);

  const headers = new Headers(request.headers);
  headers.set("host", target.host);

  const hasBody = request.method !== "GET" && request.method !== "HEAD" && request.body !== null;

  return fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    redirect: "manual",
    duplex: "half",
  } as RequestInit & { duplex: "half" });
}

const server = serve({
  routes: {
    [`${PROXY_PREFIX}/*`]: (request) => proxy(request),
    "/static/*": (request) => proxy(request),
    "/docs": (request) => proxy(request),
    "/docs/*": (request) => proxy(request),
    "/redoc": (request) => proxy(request),
    "/openapi.json": (request) => proxy(request),
    "/*": index,
  },

  development: process.env.NODE_ENV !== "production" && {
    hmr: true,
    console: true,
  },
});

console.log(`Server running at ${server.url}`);
console.log(`Proxying ${PROXY_PREFIX}/* to ${PROXY_TARGET}`);
