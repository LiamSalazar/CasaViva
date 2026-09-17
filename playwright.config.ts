import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "auth", testMatch: /auth\.setup\.ts/ },
    { name: "chromium", testIgnore: /auth\.setup\.ts/, dependencies: ["auth"], use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", grep: /@mobile/, testIgnore: /auth\.setup\.ts/, dependencies: ["auth"], use: { ...devices["iPhone 13"], browserName: "chromium" } },
  ],
  webServer: [
    {
      command: "cd backend && ANTIBOT_ENABLED=true TURNSTILE_SECRET_KEY=e2e-not-a-real-secret TURNSTILE_TEST_TOKEN=e2e-valid-token .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload",
      url: "http://127.0.0.1:8000/api/v1/public/search-options/",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DJANGO_SETTINGS_MODULE: "config.settings.postgres_test",
        POSTGRES_TEST_USER: "casaviva_app",
        POSTGRES_TEST_PASSWORD: "casaviva-app-test",
        ANTIBOT_ENABLED: "true",
        TURNSTILE_SECRET_KEY: "e2e-not-a-real-secret",
        TURNSTILE_TEST_TOKEN: "e2e-valid-token",
      },
    },
    {
      command: "NEXT_PUBLIC_ANTIBOT_ENABLED=true NEXT_PUBLIC_TURNSTILE_SITE_KEY=1x00000000000000000000AA NEXT_PUBLIC_TURNSTILE_TEST_TOKEN=e2e-valid-token npm run dev -- --webpack --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        ...process.env,
        DJANGO_INTERNAL_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_ANTIBOT_ENABLED: "true",
        NEXT_PUBLIC_TURNSTILE_SITE_KEY: "1x00000000000000000000AA",
        NEXT_PUBLIC_TURNSTILE_TEST_TOKEN: "e2e-valid-token",
      },
    },
  ],
});
