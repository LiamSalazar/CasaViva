import { expect, test } from "@playwright/test";
import { failOnPageErrors, restoreAdminSession } from "./helpers";

async function expectAdminReady(page: import("@playwright/test").Page) {
  await expect(page.locator('[data-admin-ready="true"]')).toBeVisible();
}

test("administración edita Nosotros y la página pública refleja el cambio", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page, [/net::ERR_NETWORK_IO_SUSPENDED/]);
  await restoreAdminSession(page, "content@example.test");
  await page.goto("/administracion/contenido/nosotros");
  await expectAdminReady(page);
  const title = page.getByLabel("Título principal");
  const original = await title.inputValue();
  const temporary = "Nosotros — comprobación E2E";
  await title.fill(temporary);
  await page.getByRole("button", { name: "Guardar Nosotros" }).click();
  await expect(page.getByText("Contenido de Nosotros guardado")).toBeVisible();
  await page.goto("/nosotros");
  await expect(page.getByRole("heading", { name: temporary })).toBeVisible();
  await page.goto("/administracion/contenido/nosotros");
  await expectAdminReady(page);
  await page.getByLabel("Título principal").fill(original);
  await page.getByRole("button", { name: "Guardar Nosotros" }).click();
  await expect(page.getByText("Contenido de Nosotros guardado")).toBeVisible();
  assertNoErrors();
});

test("identidad legal exige permiso sensible y audita edición autorizada", async ({ page }) => {
  await restoreAdminSession(page, "content-limited@example.test");
  await page.goto("/administracion/contenido/identidad");
  await expectAdminReady(page);
  await expect(page.getByText("Tu rol puede consultar estos datos")).toBeVisible();
  await expect(page.getByLabel("Responsable", { exact: true })).toBeDisabled();

  await page.context().clearCookies();
  await restoreAdminSession(page, "liam@example.test");
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/administracion/contenido/identidad");
  await expectAdminReady(page);
  const contact = page.getByLabel("Correo de contacto");
  const original = await contact.inputValue();
  await contact.fill("contact-e2e@example.test");
  await page.getByRole("button", { name: "Guardar identidad y contacto" }).click();
  await expect(page.getByText("Identidad y contacto guardados")).toBeVisible();
  const publicSettings = await page.request.get("/api/v1/public/site-settings/");
  expect((await publicSettings.json()).results[0].contact_email).toBe("contact-e2e@example.test");
  await page.goto("/contacto");
  await expect(page.getByRole("link", { name: "contact-e2e@example.test" }).first()).toHaveAttribute("href", "mailto:contact-e2e@example.test");
  await page.goto("/administracion/contenido/identidad");
  await expectAdminReady(page);
  await contact.fill(original);
  await page.getByRole("button", { name: "Guardar identidad y contacto" }).click();
  await expect(page.getByText("Identidad y contacto guardados")).toBeVisible();
  assertNoErrors();
});
