import { expect, test } from "@playwright/test";

test("no crea analítica antes de elegir y Limitar la mantiene desactivada", async ({ page }) => {
  const analyticsRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/public/analytics/")) analyticsRequests.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Limitar analítica" })).toBeVisible();
  await page.waitForTimeout(300);
  expect(analyticsRequests).toEqual([]);
  await page.getByRole("button", { name: "Limitar analítica" }).click();
  await page.goto("/propiedades");
  await page.waitForTimeout(300);
  expect(analyticsRequests).toEqual([]);
  expect(await page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeNull();
});
