import { expect, test } from "@playwright/test";
import { failOnPageErrors, loginAdmin } from "./helpers";

test("catálogo crea desarrolladora, desarrollo, modelo y relación dinámica", async ({ page }) => {
  test.setTimeout(90_000);
  const assertNoErrors = failOnPageErrors(page);
  const developer = "Desarrolladora E2E dinámica";
  const development = "Desarrollo E2E dinámico";
  const model = "Modelo E2E dinámico";

  await loginAdmin(page, "catalog@example.test");
  await page.goto("/administracion/desarrolladoras");
  await page.getByRole("button", { name: "Nuevo registro" }).click();
  await page.getByLabel("Nombre").fill(developer);
  await page.getByLabel("Razón social").fill("Razón social de pruebas");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: developer })).toBeVisible();

  await page.goto("/administracion/desarrollos/nuevo");
  await page.getByLabel("Nombre").fill(development);
  await page.getByLabel("Desarrolladora").selectOption({ label: developer });
  await page.getByLabel("Estado y municipio").selectOption({ index: 1 });
  await page.getByLabel("Dirección").fill("Calle Catálogo 10");
  await page.getByRole("button", { name: "Guardar desarrollo" }).click();
  await expect(page).toHaveURL(/\/administracion\/desarrollos$/);
  await expect(page.getByRole("row").filter({ hasText: development })).toBeVisible();

  await page.goto("/administracion/modelos");
  await page.getByRole("button", { name: "Nuevo registro" }).click();
  await page.getByLabel("Nombre").fill(model);
  await page.getByLabel("Desarrolladora").selectOption({ label: developer });
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  const modelRow = page.getByRole("row").filter({ hasText: model });
  await expect(modelRow).toBeVisible();
  await modelRow.getByRole("combobox").selectOption({ label: development });
  await modelRow.getByRole("button", { name: "Relacionar" }).click();
  await expect(modelRow).toContainText(development);

  await page.goto("/administracion/propiedades/nueva");
  await page.getByLabel("Origen").selectOption("DEVELOPER");
  await page.getByLabel("Desarrolladora", { exact: true }).selectOption({ label: developer });
  await page.getByLabel("Desarrollo").selectOption({ label: development });
  await expect(page.getByLabel("Modelo").locator("option", { hasText: model })).toHaveCount(1);
  await page.getByLabel("Modelo").selectOption({ label: model });
  await page.getByLabel("Título").fill("Propiedad de desarrolladora E2E");
  await page.locator("label.field").filter({ has: page.getByText("Tipo", { exact: true }) }).locator("select").selectOption({ index: 1 });
  await page.getByLabel("Condición").selectOption("new");
  await page.getByLabel("Estado de inventario").selectOption("available");
  await page.getByLabel("Precio MXN").fill("1300000");
  await page.getByLabel("Publicada").check();
  await page.getByRole("button", { name: "Guardar propiedad" }).click();
  // La primera visita al listado puede compilar la ruta bajo `next dev`.
  // El POST ya terminó antes de navegar, pero la transición puede tardar más
  // que el timeout genérico de Playwright en una instalación limpia.
  await expect(page).toHaveURL(/\/administracion\/propiedades$/, { timeout: 30_000 });
  await expect(page.getByRole("row").filter({ hasText: "Propiedad de desarrolladora E2E" })).toBeVisible();
  expect((await page.request.get("/api/v1/public/listings/propiedad-de-desarrolladora-e2e/")).status()).toBe(200);
  assertNoErrors();
});
