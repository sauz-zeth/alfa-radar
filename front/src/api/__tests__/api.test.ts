import { describe, expect, it } from "bun:test";

import {
  ApiError,
  createApiClient,
  type ApiClient,
} from "../index";

interface FetchCall {
  url: string;
  init: RequestInit;
}

function createFetch(
  handler: (call: FetchCall) => Response | Promise<Response>,
) {
  const calls: FetchCall[] = [];
  const fetchImpl = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const call = { url, init: init ?? {} };
    calls.push(call);
    return handler(call);
  }) as typeof fetch;
  return { fetchImpl, calls };
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function noContent(): Response {
  return new Response(null, { status: 204 });
}

function callAt(calls: FetchCall[], index: number): FetchCall {
  const call = calls[index];
  if (!call) {
    throw new Error(`Ожидался запрос #${index}`);
  }
  return call;
}

function lastCall(calls: FetchCall[]): FetchCall {
  return callAt(calls, calls.length - 1);
}

function authHeader(call: FetchCall): string | null {
  return new Headers(call.init.headers).get("Authorization");
}

function expectRequest(
  call: FetchCall,
  method: string,
  path: string,
  query: Record<string, string> = {},
  expectedAuth: string | null = "Bearer test-token",
): void {
  const url = new URL(call.url, "http://test.local");
  expect(call.init.method).toBe(method);
  expect(url.pathname).toBe(path);
  for (const [key, value] of Object.entries(query)) {
    expect(url.searchParams.get(key)).toBe(value);
  }
  expect(authHeader(call)).toBe(expectedAuth);
}

function expectJsonBody(call: FetchCall, body: unknown): void {
  expect(new Headers(call.init.headers).get("Content-Type")).toBe(
    "application/json",
  );
  expect(JSON.parse(String(call.init.body))).toEqual(body);
}

function setup(handler?: (call: FetchCall) => Response | Promise<Response>) {
  const { fetchImpl, calls } = createFetch(handler ?? (() => json({})));
  const api = createApiClient({
    fetch: fetchImpl,
    getToken: () => "test-token",
    validateResponses: false,
  });
  return { api, calls };
}

const USER = {
  id: "user-1",
  login: "demo",
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
};

const TOKEN_RESPONSE = {
  access_token: "jwt-token",
  token_type: "bearer",
  user: USER,
  onboarding: { completed: false, next_step: "business_selected" },
};

const EVENT_ID = "event-1";
const ITEM_ID = "tracked-1";

describe("auth", () => {
  it("register, login, me", async () => {
    const { api, calls } = setup();

    await api.auth.register({ login: "demo_user", password: "secret1" });
    expectRequest(callAt(calls, 0), "POST", "/api/auth/register");
    expectJsonBody(callAt(calls, 0), {
      login: "demo_user",
      password: "secret1",
    });

    await api.auth.login({ login: "demo_user", password: "secret1" });
    expectRequest(lastCall(calls), "POST", "/api/auth/login");
    expectJsonBody(lastCall(calls), {
      login: "demo_user",
      password: "secret1",
    });

    await api.auth.me();
    expectRequest(lastCall(calls), "GET", "/api/auth/me");
  });
});

describe("businesses", () => {
  it("list, options, byUid", async () => {
    const { api, calls } = setup();

    await api.businesses.list();
    expectRequest(callAt(calls, 0), "GET", "/api/businesses");
    expect(new URL(callAt(calls, 0).url, "http://test.local").search).toBe("");

    await api.businesses.list({
      search: "ромашка",
      city: "Москва",
      region: "Москва",
      segment: "large",
      okved: "62",
      product: "rko",
      fts: true,
      min_revenue: 1000000,
      max_revenue: 9000000,
      limit: 10,
      offset: 5,
    });
    expectRequest(lastCall(calls), "GET", "/api/businesses", {
      search: "ромашка",
      city: "Москва",
      region: "Москва",
      segment: "large",
      okved: "62",
      product: "rko",
      fts: "true",
      min_revenue: "1000000",
      max_revenue: "9000000",
      limit: "10",
      offset: "5",
    });

    await api.businesses.options({ search: "альфа", limit: 5 });
    expectRequest(lastCall(calls), "GET", "/api/businesses/options", {
      search: "альфа",
      limit: "5",
    });

    await api.businesses.byUid("uid-1");
    expectRequest(lastCall(calls), "GET", "/api/businesses/uid-1");
  });
});

describe("onboarding", () => {
  it("state, business, profile, role, skip", async () => {
    const { api, calls } = setup();

    await api.onboarding.state();
    expectRequest(callAt(calls, 0), "GET", "/api/onboarding/state");

    await api.onboarding.business({ uid: "uid-1" });
    expectRequest(lastCall(calls), "POST", "/api/onboarding/business");
    expectJsonBody(lastCall(calls), { uid: "uid-1" });

    await api.onboarding.profile({
      entrepreneur_name: "Иван",
      business_name: "ООО Ромашка",
      role: "ceo",
    });
    expectRequest(lastCall(calls), "PATCH", "/api/onboarding/profile");
    expectJsonBody(lastCall(calls), {
      entrepreneur_name: "Иван",
      business_name: "ООО Ромашка",
      role: "ceo",
    });

    await api.onboarding.role({ role: "cfo" });
    expectRequest(lastCall(calls), "POST", "/api/onboarding/role");
    expectJsonBody(lastCall(calls), { role: "cfo" });

    await api.onboarding.skip({ step: "profile_filled" });
    expectRequest(lastCall(calls), "POST", "/api/onboarding/skip");
    expectJsonBody(lastCall(calls), { step: "profile_filled" });
  });

  it("counterparties and categories", async () => {
    const { api, calls } = setup();

    await api.onboarding.counterparties();
    expectRequest(callAt(calls, 0), "GET", "/api/onboarding/counterparties");

    await api.onboarding.suggestCounterparties();
    expectRequest(
      lastCall(calls),
      "POST",
      "/api/onboarding/counterparties/suggest",
    );

    await api.onboarding.renameCounterparties({
      items: [{ id: "cp-1", name: "Поставщик" }],
    });
    expectRequest(lastCall(calls), "PATCH", "/api/onboarding/counterparties");
    expectJsonBody(lastCall(calls), {
      items: [{ id: "cp-1", name: "Поставщик" }],
    });

    await api.onboarding.categories();
    expectRequest(lastCall(calls), "GET", "/api/onboarding/categories");

    await api.onboarding.suggestCategories();
    expectRequest(lastCall(calls), "POST", "/api/onboarding/categories/suggest");

    await api.onboarding.patchCategory(7, { weight: 0.5 });
    expectRequest(lastCall(calls), "PATCH", "/api/onboarding/categories/7");
    expectJsonBody(lastCall(calls), { weight: 0.5 });
  });

  it("reporting and complete", async () => {
    const { api, calls } = setup();

    await api.onboarding.reporting();
    expectRequest(callAt(calls, 0), "GET", "/api/onboarding/reporting");

    const balance = new File(["balance"], "balance.pdf", {
      type: "application/pdf",
    });
    await api.onboarding.uploadReporting({ balance });
    const upload = lastCall(calls);
    expectRequest(upload, "POST", "/api/onboarding/reporting");
    expect(upload.init.body).toBeInstanceOf(FormData);
    const form = upload.init.body as FormData;
    const file = form.get("balance");
    expect(file).toBeInstanceOf(Blob);
    expect((file as File).name).toBe("balance.pdf");
    expect(new Headers(upload.init.headers).get("Content-Type")).toBeNull();

    await api.onboarding.complete();
    expectRequest(lastCall(calls), "POST", "/api/onboarding/complete");
  });
});

describe("profile", () => {
  it("get, patch, notifications, categories, counterparties, reporting", async () => {
    const { api, calls } = setup();

    await api.profile.get();
    expectRequest(callAt(calls, 0), "GET", "/api/profile");

    await api.profile.update({
      entrepreneur_name: "Иван",
      business_name: "ООО Ромашка",
      role: "owner",
    });
    expectRequest(lastCall(calls), "PATCH", "/api/profile");
    expectJsonBody(lastCall(calls), {
      entrepreneur_name: "Иван",
      business_name: "ООО Ромашка",
      role: "owner",
    });

    await api.profile.updateNotifications({ news: true, digest: false });
    expectRequest(lastCall(calls), "PATCH", "/api/profile/notifications");
    expectJsonBody(lastCall(calls), { news: true, digest: false });

    await api.profile.categories();
    expectRequest(lastCall(calls), "GET", "/api/profile/categories");

    await api.profile.patchCategory(3, { weight: 0.25 });
    expectRequest(lastCall(calls), "PATCH", "/api/profile/categories/3");
    expectJsonBody(lastCall(calls), { weight: 0.25 });

    await api.profile.counterparties();
    expectRequest(lastCall(calls), "GET", "/api/profile/counterparties");

    await api.profile.renameCounterparty("cp-1", { name: "Покупатель" });
    expectRequest(
      lastCall(calls),
      "PATCH",
      "/api/profile/counterparties/cp-1",
    );
    expectJsonBody(lastCall(calls), { name: "Покупатель" });

    await api.profile.reporting();
    expectRequest(lastCall(calls), "GET", "/api/profile/reporting");

    const income = new File(["income"], "income.pdf", {
      type: "application/pdf",
    });
    await api.profile.uploadReporting({ income });
    const upload = lastCall(calls);
    expectRequest(upload, "POST", "/api/profile/reporting");
    expect(upload.init.body).toBeInstanceOf(FormData);
    const form = upload.init.body as FormData;
    expect(form.get("income")).toBeInstanceOf(Blob);
  });
});

describe("feed", () => {
  it("list, hidden, restore, like, detail, scenarios, track, feedback", async () => {
    const { api, calls } = setup();

    await api.feed.list();
    expectRequest(callAt(calls, 0), "GET", "/api/feed");

    await api.feed.list({
      impact: "risk",
      category: 4,
      q: "ставка",
      include_tracked: true,
      include_skipped: false,
      include_hidden: true,
      limit: 30,
      offset: 10,
    });
    expectRequest(lastCall(calls), "GET", "/api/feed", {
      impact: "risk",
      category: "4",
      q: "ставка",
      include_tracked: "true",
      include_skipped: "false",
      include_hidden: "true",
      limit: "30",
      offset: "10",
    });

    await api.feed.hidden({ tab: "weak" });
    expectRequest(lastCall(calls), "GET", "/api/feed/hidden", { tab: "weak" });

    await api.feed.restore(EVENT_ID);
    expectRequest(lastCall(calls), "POST", `/api/feed/${EVENT_ID}/restore`);

    await api.feed.like(EVENT_ID);
    expectRequest(lastCall(calls), "POST", `/api/feed/${EVENT_ID}/like`);

    await api.feed.detail(EVENT_ID);
    expectRequest(lastCall(calls), "GET", `/api/feed/${EVENT_ID}`);

    await api.feed.scenarios(EVENT_ID, { horizon: "6m" });
    expectRequest(lastCall(calls), "GET", `/api/feed/${EVENT_ID}/scenarios`, {
      horizon: "6m",
    });

    await api.feed.track(EVENT_ID);
    expectRequest(lastCall(calls), "POST", `/api/feed/${EVENT_ID}/track`);

    await api.feed.feedback(EVENT_ID, {
      action: "not_relevant",
      reason: "Не наш профиль",
    });
    expectRequest(lastCall(calls), "POST", `/api/feed/${EVENT_ID}/feedback`);
    expectJsonBody(lastCall(calls), {
      action: "not_relevant",
      reason: "Не наш профиль",
    });
  });
});

describe("tracked", () => {
  it("list, detail, delete, archive, resume, questions, reanalyze, scenarios", async () => {
    const handler = (call: FetchCall) => {
      const path = new URL(call.url, "http://test.local").pathname;
      return call.init.method === "DELETE" && /^\/api\/tracked\/[^/]+$/.test(path)
        ? noContent()
        : json({});
    };
    const { api, calls } = setup(handler);

    await api.tracked.list({ status: "archived" });
    expectRequest(callAt(calls, 0), "GET", "/api/tracked", {
      status: "archived",
    });

    await api.tracked.detail(ITEM_ID);
    expectRequest(lastCall(calls), "GET", `/api/tracked/${ITEM_ID}`);

    const removed = await api.tracked.remove(ITEM_ID);
    expectRequest(lastCall(calls), "DELETE", `/api/tracked/${ITEM_ID}`);
    expect(removed).toBeUndefined();

    await api.tracked.archive(ITEM_ID);
    expectRequest(lastCall(calls), "POST", `/api/tracked/${ITEM_ID}/archive`);

    await api.tracked.resume(ITEM_ID);
    expectRequest(lastCall(calls), "POST", `/api/tracked/${ITEM_ID}/resume`);

    await api.tracked.questions(ITEM_ID, { question: "Что дальше?" });
    expectRequest(lastCall(calls), "POST", `/api/tracked/${ITEM_ID}/questions`);
    expectJsonBody(lastCall(calls), { question: "Что дальше?" });

    await api.tracked.reanalyze(ITEM_ID, { question: "Уточни прогноз" });
    expectRequest(lastCall(calls), "POST", `/api/tracked/${ITEM_ID}/reanalyze`);
    expectJsonBody(lastCall(calls), { question: "Уточни прогноз" });

    await api.tracked.scenarios(ITEM_ID, { horizon: "12m" });
    expectRequest(lastCall(calls), "GET", `/api/tracked/${ITEM_ID}/scenarios`, {
      horizon: "12m",
    });
  });
});

describe("sources", () => {
  it("state, catalog, channels", async () => {
    const { api, calls } = setup();

    await api.sources.state();
    expectRequest(callAt(calls, 0), "GET", "/api/sources");

    await api.sources.catalog({ q: "банк" });
    expectRequest(lastCall(calls), "GET", "/api/sources/catalog", { q: "банк" });

    await api.sources.addChannel({ query: "https://example.com/rss.xml" });
    expectRequest(lastCall(calls), "POST", "/api/sources/channels");
    expectJsonBody(lastCall(calls), { query: "https://example.com/rss.xml" });

    await api.sources.subscribe("channel-1");
    expectRequest(
      lastCall(calls),
      "POST",
      "/api/sources/channels/channel-1/subscribe",
    );

    await api.sources.unsubscribe("channel-1");
    expectRequest(
      lastCall(calls),
      "DELETE",
      "/api/sources/channels/channel-1",
    );

    await api.sources.unsubscribeAll();
    expectRequest(
      lastCall(calls),
      "POST",
      "/api/sources/channels/unsubscribe-all",
    );

    await api.sources.restore();
    expectRequest(lastCall(calls), "POST", "/api/sources/channels/restore");
  });
});

describe("search", () => {
  it("search, history, clear, delete item", async () => {
    const { api, calls } = setup();

    await api.search.search({ q: "альфа" });
    expectRequest(callAt(calls, 0), "GET", "/api/search", { q: "альфа" });

    await api.search.history();
    expectRequest(lastCall(calls), "GET", "/api/search/history");

    await api.search.clearHistory();
    expectRequest(lastCall(calls), "DELETE", "/api/search/history");

    await api.search.deleteHistoryItem("history-1");
    expectRequest(lastCall(calls), "DELETE", "/api/search/history/history-1");
  });
});

describe("health", () => {
  it("health, db, root without auth", async () => {
    const { api, calls } = setup();

    await api.health.get();
    expectRequest(callAt(calls, 0), "GET", "/health", {}, null);

    await api.health.db();
    expectRequest(lastCall(calls), "GET", "/health/db", {}, null);

    await api.health.root();
    expectRequest(lastCall(calls), "GET", "/", {}, null);
  });
});

describe("client behavior", () => {
  it("validates responses by default", async () => {
    const { fetchImpl } = createFetch(() => json(TOKEN_RESPONSE));
    const api = createApiClient({ fetch: fetchImpl });
    const result = await api.auth.me();
    expect(result).toEqual(TOKEN_RESPONSE);
  });

  it("throws ApiError on invalid response", async () => {
    const invalid = { access_token: "jwt" };
    const { fetchImpl } = createFetch(() => json(invalid));
    const api: ApiClient = createApiClient({ fetch: fetchImpl });
    const error = await api.auth.me().catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(200);
    expect(apiError.detail).toContain("Невалидный ответ API");
    expect(apiError.url).toBe("/api/auth/me");
    expect(apiError.payload).toEqual(invalid);
  });

  it("skips response validation when disabled", async () => {
    const invalid = { access_token: "jwt" };
    const { fetchImpl } = createFetch(() => json(invalid));
    const api = createApiClient({
      fetch: fetchImpl,
      validateResponses: false,
    });
    const result = await api.auth.me();
    expect(result).toEqual(invalid as never);
  });

  it("throws ApiError with status and detail from the backend", async () => {
    const { fetchImpl } = createFetch(() =>
      json({ detail: "Неверный логин или пароль" }, 401),
    );
    const api = createApiClient({ fetch: fetchImpl });
    const error = (await api.auth
      .login({ login: "demo", password: "wrong" })
      .catch((reason: unknown) => reason)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(error.detail).toBe("Неверный логин или пароль");
    expect(error.url).toBe("/api/auth/login");
    expect(error.payload).toEqual({ detail: "Неверный логин или пароль" });
  });

  it("formats FastAPI validation errors", async () => {
    const { fetchImpl } = createFetch(() =>
      json(
        {
          detail: [
            { loc: ["body", "login"], msg: "Field required", type: "missing" },
            { loc: ["body", "password"], msg: "Too short", type: "string" },
          ],
        },
        422,
      ),
    );
    const api = createApiClient({ fetch: fetchImpl });
    const error = (await api.auth
      .login({ login: "", password: "" })
      .catch((reason: unknown) => reason)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.detail).toBe("Field required; Too short");
  });

  it("returns undefined for 204 No Content", async () => {
    const { fetchImpl, calls } = createFetch(() => noContent());
    const api = createApiClient({ fetch: fetchImpl });
    const result = await api.tracked.remove("item-1");
    expect(result).toBeUndefined();
    expect(callAt(calls, 0).init.method).toBe("DELETE");
  });

  it("passes AbortSignal and rejects on cancellation", async () => {
    let receivedSignal: AbortSignal | null | undefined;
    const fetchImpl = ((_input: RequestInfo | URL, init?: RequestInit) => {
      receivedSignal = init?.signal;
      return new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal;
        if (!signal) {
          return;
        }
        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }) as typeof fetch;
    const api = createApiClient({ fetch: fetchImpl });
    const controller = new AbortController();
    const request = api.auth.me({ signal: controller.signal });
    controller.abort();
    const error = await request.catch((reason: unknown) => reason);
    expect((error as Error).name).toBe("AbortError");
    expect(receivedSignal).toBe(controller.signal);
    expect(controller.signal.aborted).toBe(true);
  });

  it("validates request bodies before fetching", async () => {
    const { api, calls } = setup();
    const error = (await api.auth
      .register({ login: "ab", password: "123" })
      .catch((reason: unknown) => reason)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.detail).toContain("Невалидные данные запроса");
    expect(calls.length).toBe(0);
  });

  it("validates query params before fetching", async () => {
    const { api, calls } = setup();
    const error = (await api.feed
      .list({ category: 0 })
      .catch((reason: unknown) => reason)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.detail).toContain("Невалидные параметры запроса");
    expect(calls.length).toBe(0);
  });

  it("requires at least one reporting file", async () => {
    const { api, calls } = setup();
    const error = (await api.onboarding
      .uploadReporting({})
      .catch((reason: unknown) => reason)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.detail).toContain("Загрузите хотя бы одну форму отчётности");
    expect(calls.length).toBe(0);
  });

  it("supports async token providers and missing tokens", async () => {
    let token: string | null = null;
    const { fetchImpl, calls } = createFetch(() => json({}));
    const api = createApiClient({
      fetch: fetchImpl,
      getToken: async () => token,
      validateResponses: false,
    });

    await api.auth.me();
    expect(authHeader(callAt(calls, 0))).toBeNull();

    token = "async-token";
    await api.auth.me();
    expect(authHeader(lastCall(calls))).toBe("Bearer async-token");
  });

  it("applies a custom base URL", async () => {
    const { fetchImpl, calls } = createFetch(() => json({}));
    const api = createApiClient({
      baseUrl: "https://api.example.com/",
      fetch: fetchImpl,
      validateResponses: false,
    });
    await api.health.root();
    expect(callAt(calls, 0).url).toBe("https://api.example.com/");
  });
});
