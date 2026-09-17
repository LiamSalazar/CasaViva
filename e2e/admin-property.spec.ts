import { expect, test } from "@playwright/test";
import { failOnPageErrors, restoreAdminSession } from "./helpers";

test("propiedad particular conserva campos, precio, publicación, consulta, archivo y restauración", async ({ page }) => {
  test.setTimeout(90_000);
  const assertNoErrors = failOnPageErrors(page);
  const title = "Particular integral E2E";
  const slug = "particular-integral-e2e";

  // Alfredo prueba el mismo CRUD empresarial que Ana sin reutilizar el TOTP
  // consumido por el escenario Owner ejecutado inmediatamente antes.
  await restoreAdminSession(page, "alfredo@example.test");
  await page.goto("/administracion/propiedades/nueva");
  await expect(page.getByRole("heading", { name: "Nueva propiedad", level: 1 })).toBeVisible();

  await page.getByLabel("Título").fill(title);
  await expect(page.getByLabel("Slug")).toHaveValue(slug);
  const propertyType = page.locator("label.field").filter({
    has: page.getByText("Tipo", { exact: true }),
  }).locator("select");
  await propertyType.selectOption("duplex");
  await page.getByLabel("Condición").selectOption("used");
  await page.getByLabel("Estado de inventario").selectOption("available");
  await page.getByLabel("Publicada").check();
  await page.getByLabel("Promoción autorizada por el proveedor").check();
  await page.getByLabel("Fecha y hora de última verificación (ISO 8601)").fill(new Date().toISOString());
  await page.getByLabel("Destacada").check();
  await page.getByLabel("Precio MXN").fill("1750000");
  await page.getByLabel("Ubicación").selectOption({ index: 1 });
  await page.getByLabel("Dirección").fill("Calle Integridad 42");
  await page.getByLabel("Código postal").fill("55740");
  await page.getByLabel("Latitud").fill("19.713456");
  await page.getByLabel("Longitud").fill("-98.968765");
  await page.getByLabel("Recámaras mínimas").fill("3");
  await page.getByRole("spinbutton", { name: "Baños", exact: true }).fill("2.5");
  await page.getByLabel("Estacionamientos mínimos").fill("2");
  await page.getByLabel("Niveles mínimos").fill("2");
  await page.getByLabel("Construcción mínima m²").fill("118.5");
  await page.getByLabel("Descripción corta").fill("Propiedad para comprobar el flujo integral real.");
  await page.getByLabel("Descripción completa").fill("Descripción original persistida desde el formulario administrativo.");
  await page.getByLabel("Referencia", { exact: true }).fill("E2E-PRIVATE-ROUNDTRIP");
  await page.getByLabel("Comisión %").fill("3.5");
  await page.getByLabel("Notas internas").fill("Dato confidencial de prueba.");
  await page.getByRole("button", { name: "Guardar propiedad" }).click();

  await expect(page).toHaveURL(/\/administracion\/propiedades$/);
  const row = page.getByRole("row").filter({ hasText: title });
  await expect(row).toBeVisible();
  await row.getByRole("link", { name: "Editar" }).click();
  await expect(page).toHaveURL(/\/administracion\/propiedades\/[0-9a-f-]+$/, { timeout: 30_000 });
  await expect(page.getByLabel("Dirección")).toHaveValue("Calle Integridad 42");
  await expect(page.getByLabel("Latitud")).toHaveValue("19.713456");
  await expect(page.getByLabel("Longitud")).toHaveValue("-98.968765");
  await expect(page.getByLabel("Niveles mínimos")).toHaveValue("2");
  await expect(page.getByLabel("Condición")).toHaveValue("used");
  await expect(page.getByLabel("Referencia", { exact: true })).toHaveValue("E2E-PRIVATE-ROUNDTRIP");

  const listingId = new URL(page.url()).pathname.split("/").at(-1)!;
  await page.getByLabel("Precio MXN").fill("1825000");
  await page.getByLabel("Condición").selectOption("new");
  await page.getByLabel("Descripción completa").fill("Descripción actualizada sin perder el resto de campos.");
  await page.getByRole("button", { name: "Guardar propiedad" }).click();
  await expect(page).toHaveURL(/\/administracion\/propiedades$/);

  const history = await page.request.get(`/api/v1/admin/listings/${listingId}/price_history/`);
  expect(history.status()).toBe(200);
  expect((await history.json()).length).toBe(2);
  const publicResponse = await page.request.get(`/api/v1/public/listings/${slug}/`);
  expect(publicResponse.status()).toBe(200);
  const publicData = await publicResponse.json();
  expect(publicData.condition).toBe("new");
  expect(Number(publicData.price)).toBe(1_825_000);
  expect(publicData).not.toHaveProperty("internal_notes");
  expect(publicData).not.toHaveProperty("default_commission_rate");

  await page.goto(`/propiedades/${slug}`);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await page.getByLabel("Nombre").fill("Cliente E2E");
  await page.getByLabel("Correo").fill("cliente.property@example.test");
  await page.getByLabel("Teléfono").fill("5512345678");
  await page.getByLabel("He leído el Aviso de Privacidad.", { exact: true }).check();
  await page.getByLabel(/Autorizo que CasaViva comparta mis datos/).check();
  await expect(page.getByTestId("turnstile-widget")).toBeVisible();
  await page.getByRole("button", { name: "Solicitar información" }).click();
  await expect(page.getByRole("heading", { name: "Gracias por escribirnos." })).toBeVisible();

  await page.goto("/administracion/consultas");
  await expect(page.getByText("Cliente E2E")).toBeVisible();
  await page.goto("/administracion/propiedades");
  const activeRow = page.getByRole("row").filter({ hasText: title });
  await activeRow.getByTitle("Archivar").click();
  const archiveDialog = page.getByRole("dialog").filter({ hasText: "¿Archivar esta propiedad?" });
  await archiveDialog.getByRole("button", { name: "Archivar", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: title })).toHaveCount(0);
  expect((await page.request.get(`/api/v1/public/listings/${slug}/`)).status()).toBe(404);

  await page.getByRole("button", { name: "Ver archivadas" }).click();
  const archivedRow = page.getByRole("row").filter({ hasText: title });
  await expect(archivedRow).toBeVisible();
  await archivedRow.getByRole("button", { name: "Restaurar" }).click();
  await expect(archivedRow).toHaveCount(0);
  await page.getByRole("button", { name: "Ver activas" }).click();
  await expect(page.getByRole("row").filter({ hasText: title })).toBeVisible();
  expect((await page.request.get(`/api/v1/public/listings/${slug}/`)).status()).toBe(404);
  assertNoErrors();
});
