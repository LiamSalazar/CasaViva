import { expect, test } from "@playwright/test";
import { failOnPageErrors, loginAdmin } from "./helpers";

test("contacto exige consentimiento y conserva motivo, sesión y campaña", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/contacto?utm_source=google&utm_medium=cpc&utm_campaign=contacto_e2e");
  await page.getByLabel("Nombre").fill("Contacto General E2E");
  await page.getByLabel("Correo").fill("contacto.general@example.test");
  await page.getByLabel("Motivo").selectOption("SEARCH_ASSISTANCE");
  await page.getByLabel("Mensaje").fill("Necesito ayuda para encontrar una propiedad adecuada.");
  await page.getByRole("button", { name: "Enviar mensaje" }).click();
  await expect(page.getByText("Debes aceptar el aviso")).toBeVisible();
  await page.getByLabel(/He leído y acepto/).check();
  await page.getByRole("button", { name: "Enviar mensaje" }).click();
  await expect(page.getByRole("heading", { name: "Gracias por escribirnos." })).toBeVisible();

  await loginAdmin(page, "attribution@example.test");
  const response = await page.request.get("/api/v1/admin/inquiries/?page_size=100&search=Contacto%20General%20E2E");
  expect(response.status()).toBe(200);
  const inquiry = (await response.json()).results.find((item: { lead_name: string }) => item.lead_name === "Contacto General E2E");
  expect(inquiry).toMatchObject({ intent: "GENERAL_CONTACT", subject: "SEARCH_ASSISTANCE", campaign: "contacto_e2e", source: "google" });
  expect(inquiry.session_id).toBeTruthy();
  assertNoErrors();
});

test("la sesión rota por campaña o inactividad y conserva el visitante", async ({ page }) => {
  await page.goto("/?utm_source=google&utm_medium=cpc&utm_campaign=campaign_a");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeTruthy();
  const first = await page.evaluate(() => ({
    session: sessionStorage.getItem("casaviva-session-id"),
    visitor: localStorage.getItem("casaviva-visitor-id"),
  }));

  await page.goto("/?utm_source=instagram&utm_medium=paid_social&utm_campaign=campaign_b");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).not.toBe(first.session);
  const second = await page.evaluate(() => ({
    session: sessionStorage.getItem("casaviva-session-id"),
    visitor: localStorage.getItem("casaviva-visitor-id"),
  }));
  expect(second.visitor).toBe(first.visitor);

  await page.evaluate(() => {
    sessionStorage.setItem("casaviva-session-last-activity", String(Date.now() - 31 * 60 * 1000));
  });
  await page.goto("/nosotros");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).not.toBe(second.session);
  expect(await page.evaluate(() => localStorage.getItem("casaviva-visitor-id"))).toBe(first.visitor);
});
