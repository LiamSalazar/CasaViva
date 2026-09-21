import { mkdir } from "node:fs/promises";
import { test as setup } from "@playwright/test";
import { createAdminStorageState } from "./helpers";

const users = [
  "liam@example.test",
  "ana@example.test",
  "alfredo@example.test",
  "attribution@example.test",
  "catalog@example.test",
  "marketing@example.test",
  "content@example.test",
  "content-limited@example.test",
  "geo@example.test",
];

setup.beforeAll(async () => mkdir("playwright/.auth", { recursive: true }));

for (const email of users) {
  setup(`autentica ${email}`, async ({ request }) => {
    await createAdminStorageState(request, email);
  });
}
