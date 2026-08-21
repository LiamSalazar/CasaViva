import { expect, test } from "@playwright/test";
import { failOnPageErrors } from "./helpers";

test("home, catálogo dinámico, paginación, detalle y favorito usan el sistema real", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Encuentra el lugar/ })).toBeVisible();
  await page.goto("/propiedades");
  await expect(page.getByRole("button", { name: /^Dúplex/ })).toBeVisible();
  await page.getByRole("button", { name: /^Dúplex/ }).click();
  await expect(page).toHaveURL(/propertyType=duplex/);
  await expect(page.getByText(/30 propiedades/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeEnabled();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
  const favorite = page.getByRole("button", { name: /favorito/i }).first();
  await favorite.click();
  await page.goto("/favoritos");
  await expect(page.getByText("Dúplex E2E 1")).toBeVisible();
  assertNoErrors();
});

test("slug inexistente muestra la página 404 sin traceback", async ({ page }) => {
  await page.goto("/propiedades/no-existe-e2e");
  await expect(page.getByRole("heading", { name: "Esta propiedad no está disponible" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Traceback");
});

test("@mobile mantiene accesibles home, resultados y detalle", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Encuentra el lugar/ })).toBeVisible();
  await page.goto("/propiedades?propertyType=duplex");
  await expect(page.getByRole("button", { name: "Filtros" })).toBeVisible();
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
});
