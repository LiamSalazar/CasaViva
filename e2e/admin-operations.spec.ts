import { expect, test } from "@playwright/test";
import { failOnPageErrors, restoreAdminSession } from "./helpers";

test("Founder administra campaña y gasto sin borrar historia", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  const campaign = "Campaña operativa E2E";
  await restoreAdminSession(page, "marketing@example.test");
  await page.goto("/administracion/marketing");

  await page.getByRole("button", { name: "Nueva campaña" }).click();
  await page.getByLabel("Nombre").fill(campaign);
  await page.getByLabel("UTM campaign").fill("operativa_e2e");
  await page.getByLabel("Canal").selectOption("INSTAGRAM");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  const campaignRow = page.getByRole("row").filter({ hasText: campaign });
  await expect(campaignRow).toBeVisible();

  await page.getByRole("button", { name: "Registrar gasto" }).click();
  await page.getByLabel("Campaña").selectOption({ label: campaign });
  await page.getByLabel("Importe MXN").fill("3000");
  await page.getByRole("button", { name: "Guardar gasto" }).click();
  const spendPanel = page.getByRole("heading", { name: "Histórico de gasto real" }).locator("..");
  const spendRow = spendPanel.getByRole("row").filter({ hasText: campaign }).filter({ hasText: "$3,000" });
  await expect(spendRow).toContainText("Vigente");

  page.once("dialog", (dialog) => dialog.accept("Captura duplicada de prueba"));
  await spendRow.getByRole("button", { name: "Anular" }).click();
  await expect(spendPanel.getByRole("row").filter({ hasText: campaign }).filter({ hasText: "$3,000" })).toContainText("Anulado");
  await campaignRow.getByRole("button", { name: "Archivar" }).click();
  await expect(campaignRow.getByRole("button", { name: "Restaurar" })).toBeVisible();
  assertNoErrors();
});

test("Founder crea la jerarquía geográfica completa desde Catálogos", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await restoreAdminSession(page, "geo@example.test");
  await page.goto("/administracion/catalogos");
  const panel = page.getByRole("heading", { name: "Ubicaciones auxiliares" }).locator("..");
  const kind = panel.locator("select").first();

  await page.getByLabel("Nombre de ubicación").fill("Estado E2E");
  await panel.getByPlaceholder("Código").fill("EE");
  await panel.getByRole("button", { name: "Añadir" }).click();
  await expect(panel.getByText("Estado E2E", { exact: true })).toBeVisible();

  await kind.selectOption("municipalities");
  await page.getByLabel("Nombre de ubicación").fill("Municipio E2E");
  await page.getByLabel("Estado").selectOption({ label: "Estado E2E" });
  await panel.getByRole("button", { name: "Añadir" }).click();
  await expect(panel.getByText("Municipio E2E", { exact: true })).toBeVisible();

  await kind.selectOption("localities");
  await page.getByLabel("Nombre de ubicación").fill("Localidad E2E");
  await page.getByLabel("Municipio").selectOption({ label: "Municipio E2E" });
  await panel.getByRole("button", { name: "Añadir" }).click();
  await expect(panel.getByText("Localidad E2E", { exact: true })).toBeVisible();

  await kind.selectOption("neighborhoods");
  await page.getByLabel("Nombre de ubicación").fill("Colonia E2E");
  await page.getByLabel("Municipio").selectOption({ label: "Municipio E2E" });
  await page.getByLabel("Localidad").selectOption({ label: "Localidad E2E" });
  await panel.getByPlaceholder("Código postal").fill("55000");
  await panel.getByRole("button", { name: "Añadir" }).click();
  await expect(panel.getByText("Colonia E2E", { exact: true })).toBeVisible();
  assertNoErrors();
});

test("CMS persiste el Hero y una guía pasa de borrador a pública con imagen", async ({ page }) => {
  test.setTimeout(90_000);
  const assertNoErrors = failOnPageErrors(page);
  await restoreAdminSession(page, "content@example.test");
  await page.goto("/administracion/contenido");
  await page.getByLabel("Antetítulo").fill("Selección editorial E2E");
  await page.getByLabel("Título", { exact: true }).fill("Un hogar probado de extremo a extremo");
  await page.getByRole("button", { name: "Guardar contenido" }).click();
  await expect(page.getByText("Cambios guardados")).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Un hogar probado de extremo a extremo" })).toBeVisible();

  await page.goto("/administracion/guias/nueva");
  await page.getByLabel("Título").fill("Guía borrador E2E");
  await page.getByLabel("Extracto").fill("Extracto de la guía de integración.");
  await page.getByLabel("Contenido (Markdown simple)").fill("Contenido editorial persistente.");
  await page.getByLabel("Imagen principal").setInputFiles({
    name: "hero-e2e.png",
    mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPkEpFjYGBgYmBgYGBgAAAC5gBAXKUgWwAAAABJRU5ErkJggg==", "base64"),
  });
  await expect(page.getByText("Imagen cargada")).toBeVisible();
  await page.getByRole("button", { name: "Guardar guía" }).click();
  await expect(page).toHaveURL(/\/administracion\/guias$/);
  await expect(page.getByRole("row").filter({ hasText: "Guía borrador E2E" })).toContainText("Borrador");
  expect((await page.request.get("/api/v1/public/guides/guia-borrador-e2e/")).status()).toBe(404);

  await page.getByRole("row").filter({ hasText: "Guía borrador E2E" }).getByRole("link").click();
  await page.getByLabel("Publicada").check();
  await page.getByRole("button", { name: "Guardar guía" }).click();
  await expect(page).toHaveURL(/\/administracion\/guias$/);
  expect((await page.request.get("/api/v1/public/guides/guia-borrador-e2e/")).status()).toBe(200);
  await page.goto("/guias/guia-borrador-e2e");
  await expect(page.getByRole("heading", { name: "Guía borrador E2E" })).toBeVisible();
  assertNoErrors();
});

test("Founder actualiza redes y el sitio público refleja la configuración central", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  const instagram = "https://www.instagram.com/casaviva-e2e/";
  await restoreAdminSession(page, "content@example.test");
  await page.goto("/administracion/contenido");
  await page.getByLabel("Instagram", { exact: true }).fill(instagram);
  await page.getByRole("button", { name: "Guardar información de contacto" }).click();
  await expect(page.getByText("Información de contacto guardada")).toBeVisible();
  await page.goto("/contacto");
  const publicLinks = page.getByRole("link", { name: "Instagram de CasaViva" });
  await expect(publicLinks).toHaveCount(2);
  await expect(publicLinks.first()).toHaveAttribute("href", instagram);
  await expect(publicLinks.last()).toHaveAttribute("href", instagram);
  assertNoErrors();
});
