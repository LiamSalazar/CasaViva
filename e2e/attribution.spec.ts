import { expect, test } from "@playwright/test";
import { failOnPageErrors, restoreAdminSession } from "./helpers";

test("UTM conserva atribución desde sesión hasta venta y BI", async ({ page }) => {
  test.setTimeout(90_000);
  const assertNoErrors = failOnPageErrors(page);
  const campaign = "tecamac_agosto_e2e";
  const email = "atribucion.e2e@example.test";

  await page.goto(`/?utm_source=instagram&utm_medium=paid_social&utm_campaign=${campaign}&utm_content=reel_04`);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeNull();
  await page.getByRole("button", { name: "Entendido" }).click();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeTruthy();
  const identity = await page.evaluate(() => ({
    sessionId: sessionStorage.getItem("casaviva-session-id"),
    visitorId: sessionStorage.getItem("casaviva-session-visitor-id"),
  }));
  expect(identity.sessionId).toBeTruthy();
  expect(identity.visitorId).toBeTruthy();

  await page.goto("/propiedades/duplex-e2e-1");
  await page.getByLabel("Nombre").fill("Cliente atribuido E2E");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Teléfono").fill("5511112233");
  await page.getByLabel("He leído el Aviso de Privacidad.", { exact: true }).check();
  await page.getByLabel(/Autorizo que CasaViva comparta mis datos/).check();
  await expect(page.getByTestId("turnstile-widget")).toBeVisible();
  await page.getByRole("button", { name: "Solicitar información" }).click();
  await expect(page.getByRole("heading", { name: "Gracias por escribirnos." })).toBeVisible();

  await restoreAdminSession(page, "attribution@example.test");
  await page.goto("/administracion/consultas");
  await expect(page.getByText("Cliente atribuido E2E")).toBeVisible();

  const inquiryResponse = await page.request.get("/api/v1/admin/inquiries/?page_size=100");
  expect(inquiryResponse.status()).toBe(200);
  const inquiryBody = await inquiryResponse.json();
  const inquiry = inquiryBody.results.find((item: { lead_name: string }) => item.lead_name === "Cliente atribuido E2E");
  expect(inquiry).toBeTruthy();
  expect(inquiry.session_id).toBe(identity.sessionId);

  const attributionResponse = await page.request.get(`/api/v1/admin/bi/sessions/${identity.sessionId}/`);
  expect(attributionResponse.status()).toBe(200);
  const attribution = await attributionResponse.json();
  expect(attribution.visitor_id).toBe(identity.visitorId);
  expect(attribution.lead_id).toBe(inquiry.lead);
  expect(attribution.utm_source).toBe("instagram");
  expect(attribution.utm_campaign).toBe(campaign);

  await page.goto("/administracion/visitas");
  await page.getByRole("button", { name: "Nueva visita" }).click();
  await page.getByLabel("Cliente").selectOption({ label: "Cliente atribuido E2E" });
  await page.getByLabel("Propiedad").selectOption({ label: "Dúplex E2E 1" });
  await page.getByLabel("Fecha y hora").fill(new Date(Date.now() + 86_400_000).toISOString().slice(0, 16));
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  const visitRow = page.getByRole("row").filter({ hasText: "Cliente atribuido E2E" });
  await expect(visitRow).toBeVisible();
  await visitRow.getByRole("button", { name: "Abrir" }).click();
  await page.getByLabel("Estado").selectOption("COMPLETED");
  await page.getByRole("button", { name: "Guardar cambios" }).click();

  await page.goto("/administracion/ventas");
  await page.getByRole("button", { name: "Registrar venta" }).click();
  await page.getByLabel("Cliente").selectOption({ label: "Cliente atribuido E2E" });
  await page.getByLabel("Propiedad").selectOption({ label: "Dúplex E2E 1" });
  await page.getByLabel("Precio de venta").fill("1500000");
  await page.getByLabel("Fecha de cierre").fill(new Date().toISOString().slice(0, 16));
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Cliente atribuido E2E" })).toBeVisible();

  const visits = await (await page.request.get("/api/v1/admin/visits/?page_size=100")).json();
  const visit = visits.results.find((item: { lead: string }) => item.lead === inquiry.lead);
  const sales = await (await page.request.get("/api/v1/admin/sales/?page_size=100")).json();
  const sale = sales.results.find((item: { lead: string }) => item.lead === inquiry.lead);
  expect(visit.status).toBe("COMPLETED");
  expect(sale.status).toBe("CLOSED");

  const marketingResponse = await page.request.get("/api/v1/admin/bi/marketing/?days=30");
  expect(marketingResponse.status()).toBe(200);
  const marketing = await marketingResponse.json();
  const row = marketing.campaigns.find((item: { utm_campaign: string }) => item.utm_campaign === campaign);
  expect(row).toMatchObject({ sessions: 1, inquiries: 1, completed_visits: 1, closed_sales: 1 });

  await page.evaluate(() => {
    sessionStorage.removeItem("casaviva-session-id");
    sessionStorage.removeItem("casaviva-session-visitor-id");
  });
  await page.goto("/");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeTruthy();
  const newIdentity = await page.evaluate(() => ({
    sessionId: sessionStorage.getItem("casaviva-session-id"),
    visitorId: sessionStorage.getItem("casaviva-session-visitor-id"),
  }));
  expect(newIdentity.sessionId).not.toBe(identity.sessionId);
  expect(newIdentity.visitorId).not.toBe(identity.visitorId);
  assertNoErrors();
});
