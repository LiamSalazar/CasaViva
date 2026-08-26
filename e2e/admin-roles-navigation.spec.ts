import { expect, test } from "@playwright/test";
import { failOnPageErrors, loginAdmin } from "./helpers";

test("Owner administra roles y la navegación mantiene icono y texto en línea", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await loginAdmin(page);
  await page.goto("/administracion/roles");
  await expect(page.getByRole("heading", { name: "Roles y permisos" })).toBeVisible();
  await expect(page.getByText("Administrador general")).toBeVisible();
  const link = page.getByRole("link", { name: "Propiedades" });
  await expect(link).toHaveCSS("display", "flex");
  await expect(link).toHaveCSS("white-space", "nowrap");
  const users = page.getByRole("link", { name: "Usuarios" });
  const roles = page.getByRole("link", { name: "Roles" });
  expect(Math.abs((await roles.boundingBox())!.y - (await users.boundingBox())!.y)).toBeLessThan(50);
  assertNoErrors();
});
