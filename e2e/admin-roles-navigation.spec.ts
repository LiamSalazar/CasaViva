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

test("Cerrar sesión permanece visible con sidebar alto y zoom normal", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 600 });
  await loginAdmin(page);
  const logout = page.getByRole("button", { name: "Cerrar sesión" });
  for (const height of [600, 768]) {
    await page.setViewportSize({ width: 1366, height });
    await page.goto("/administracion/roles");
    await expect(logout).toBeVisible();
    await expect(logout).toBeEnabled();
    const box = await logout.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y + box!.height).toBeLessThanOrEqual(height);
  }
  await logout.click();
  await expect(page).toHaveURL(/\/administracion\/acceso/);
});
