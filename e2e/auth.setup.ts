import { mkdir } from "node:fs/promises";
import { test as setup } from "@playwright/test";
import { loginAdmin, storageStatePath } from "./helpers";

const users = [
  "liam@example.test",
  "ana@example.test",
  "alfredo@example.test",
  "attribution@example.test",
  "catalog@example.test",
  "marketing@example.test",
  "content@example.test",
  "geo@example.test",
];

setup.beforeAll(async () => mkdir("playwright/.auth", { recursive: true }));

for (const email of users) {
  setup(`autentica ${email}`, async ({ page }) => {
    await loginAdmin(page, email);
    await page.context().storageState({ path: storageStatePath(email) });
  });
}
