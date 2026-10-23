import { defineConfig } from "@playwright/test";

const PORT = 5273;

export default defineConfig({
  testMatch: "playwright.test.ts",
  use: { baseURL: `http://localhost:${PORT}` },
  webServer: {
    command: "bun src/index.ts",
    url: `http://localhost:${PORT}`,
    env: { PORT: String(PORT) },
    reuseExistingServer: true,
  },
});
