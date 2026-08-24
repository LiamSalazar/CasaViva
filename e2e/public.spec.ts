import { expect, test } from "@playwright/test";
import { failOnPageErrors } from "./helpers";

test("home, catálogo dinámico, paginación, detalle y favorito usan el sistema real", async ({ page }) => {
  test.setTimeout(60_000);
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/");
  const heroTitle = page.locator("h1");
  await expect(heroTitle).toBeVisible();
  await expect(heroTitle).not.toHaveText("");
  await expect(page.getByRole("link", { name: "Casas nuevas" })).toHaveAttribute(
    "href",
    "/propiedades?propertyType=house&condition=new",
  );
  await page.goto("/propiedades");
  await expect(page.getByRole("button", { name: /^Dúplex/ })).toBeVisible();
  await page.getByRole("button", { name: /^Dúplex/ }).click();
  await expect(page).toHaveURL(/propertyType=duplex/);
  const resultSummary = page.getByText(/\d+ propiedades/).first();
  await expect(resultSummary).toBeVisible();
  const total = Number((await resultSummary.textContent())?.match(/\d+/)?.[0]);
  expect(total).toBeGreaterThan(24);
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeEnabled();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
  const favorite = page.getByRole("button", { name: /favorito/i }).first();
  await favorite.click();
  await page.getByRole("link", { name: "Favoritos", exact: true }).click();
  await expect(page).toHaveURL(/\/favoritos$/);
  await expect(page.getByRole("heading", { name: "Favoritos", exact: true })).toBeVisible();
  await expect(page.locator('a[href="/propiedades/duplex-e2e-1"]')).toBeVisible();
  assertNoErrors();
});

test("slug inexistente muestra la página 404 sin traceback", async ({ page }) => {
  await page.goto("/propiedades/no-existe-e2e");
  await expect(page.getByRole("heading", { name: "Esta propiedad no está disponible" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Traceback");
});

test("detalle de guía fuera de la primera página usa su endpoint y las galerías abren fotos y planos", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/guias/guia-publica-e2e-00");
  await expect(page.getByRole("heading", { name: "Guía pública E2E 00" })).toBeVisible();

  await page.goto("/propiedades/duplex-e2e-1");
  await page.getByRole("button", { name: /2 Fotos/ }).click();
  await expect(page.getByRole("dialog", { name: "Galería de propiedad" })).toContainText("Foto 1 / 2");
  await page.getByRole("button", { name: "Cerrar" }).click();
  await page.getByRole("button", { name: /1 Planos/ }).click();
  await expect(page.getByRole("dialog", { name: "Galería de propiedad" })).toContainText("Plano 1 / 1");
  assertNoErrors();
});

test("@mobile mantiene accesibles home, resultados y detalle", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  await page.goto("/propiedades?propertyType=duplex");
  await expect(page.getByRole("button", { name: "Filtros" })).toBeVisible();
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
});
