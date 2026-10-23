import { test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const shotBase = join(__dirname, "test-screenshots");

const user = {
  id: "u1",
  login: "demo",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

const profile = {
  id: "p1",
  user_id: "u1",
  entrepreneur_name: "Андрей Волков",
  business_name: "Уралпрокат",
  onboarding_step: "done",
  onboarding_completed: true,
};

const categories = [
  {
    category_id: 1,
    slug: "metallurgy",
    name: "Металлургия",
    short_name: "Металлургия",
    group: "industry",
    description: "",
    example: "",
    channels: [],
    weight: 0.8,
    rationale: "",
    is_manual: false,
  },
  {
    category_id: 2,
    slug: "export",
    name: "Экспорт",
    short_name: "Экспорт",
    group: "trade",
    description: "",
    example: "",
    channels: [],
    weight: 0.6,
    rationale: "",
    is_manual: false,
  },
];

const channels = [
  ["ch1", "Металл.Инсайд", "@metal_insight", true],
  ["ch2", "Сырьевой радар", "@raw_radar", true],
  ["ch3", "Прокатный цех", "@rolling_shop", true],
  ["ch4", "Экспортный пульс", "@export_pulse", true],
  ["ch5", "Восточный курс", "@east_course", true],
  ["ch6", "Грузовой узел", "@cargo_node", true],
  ["ch7", "Деловой вестник", "@biz_bulletin", true],
].map(([id, name, handle, recommended]) => ({
  id,
  name,
  handle,
  topics: "тематика",
  kind: "catalog",
  subscribed: true,
  recommended,
}));

test("sources page", async ({ page }) => {
  await page.addInitScript((u) => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("auth.user", JSON.stringify(u));
  }, user);

  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "test-token",
        token_type: "bearer",
        user,
        onboarding: { completed: true, next_step: "done" },
      }),
    }),
  );

  await page.route("**/api/onboarding/state", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ completed: true, next_step: "done", steps: [], profile }),
    }),
  );

  await page.route("**/api/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        profile,
        stats: { revenue_label: "—", products: [], tags: [] },
        category_groups: [],
        categories,
        counterparties: [],
        counterparties_by_direction: {},
        notifications: [],
        reporting: {},
      }),
    }),
  );

  await page.route("**/api/sources", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        channels,
        alfa_analytics: true,
        recommended_count: 15,
        custom_count: 0,
        catalog_total: 15,
      }),
    }),
  );

  await page.route("**/api/sources/catalog**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 15, query: "" }),
    }),
  );

  await page.goto("/sources", { waitUntil: "networkidle" });
  await page.waitForSelector(".channel-card", { timeout: 10000 });
  await page.setViewportSize({ width: 393, height: 1400 });
  await page.screenshot({ path: join(shotBase, "sources-page.png"), fullPage: true });
});
