import { expect, test } from "@playwright/test";
import { failOnPageErrors, loginAdmin } from "./helpers";

test("UTM conserva atribución desde sesión hasta venta y BI", async ({ page }) => {
  test.setTimeout(90_000);
  const assertNoErrors = failOnPageErrors(page);
  const campaign = "tecamac_agosto_e2e";
  const email = "atribucion.e2e@example.test";

  await page.goto(`/?utm_source=instagram&utm_medium=paid_social&utm_campaign=${campaign}&utm_content=reel_04`);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("casaviva-session-id"))).toBeTruthy();
  const identity = await page.evaluate(() => ({
    sessionId: sessionStorage.getItem("casaviva-session-id"),
    visitorId: localStorage.getItem("casaviva-visitor-id"),
  }));
  expect(identity.sessionId).toBeTruthy();
  expect(identity.visitorId).toBeTruthy();

  await page.goto("/propiedades/duplex-e2e-1");
  await page.getByLabel("Nombre").fill("Cliente atribuido E2E");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Teléfono").fill("5511112233");
  await page.getByLabel(/He leído y acepto/).check();
  await page.getByRole("button", { name: "Solicitar información" }).click();
  await expect(page.getByRole("heading", { name: "Gracias por escribirnos." })).toBeVisible();

  await loginAdmin(page, "attribution@example.test");
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

  const propertyResponse = await page.request.get(`/api/v1/admin/properties/${inquiry.listing}/`);
  expect(propertyResponse.status()).toBe(200);
  const property = await propertyResponse.json();
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  const headers = { "X-CSRFToken": csrf! };
  const visitResponse = await page.request.post("/api/v1/admin/visits/", { headers, data: {
    lead: inquiry.lead,
    offering: property.offering,
    scheduled_at: new Date().toISOString(),
    status: "COMPLETED",
    completed_at: new Date().toISOString(),
  }});
  expect(visitResponse.status()).toBe(201);
  const visit = await visitResponse.json();
  expect(visit.lead).toBe(inquiry.lead);

  const saleResponse = await page.request.post("/api/v1/admin/sales/", { headers, data: {
    lead: inquiry.lead,
    offering: property.offering,
    listing: inquiry.listing,
    sale_price: "1500000.00",
    closed_at: new Date().toISOString(),
    status: "CLOSED",
  }});
  expect(saleResponse.status()).toBe(201);
  const sale = await saleResponse.json();
  expect(sale.lead).toBe(inquiry.lead);

  const marketingResponse = await page.request.get("/api/v1/admin/bi/marketing/?days=30");
  expect(marketingResponse.status()).toBe(200);
  const marketing = await marketingResponse.json();
  const row = marketing.find((item: { utm_campaign: string }) => item.utm_campaign === campaign);
  expect(row).toMatchObject({ sessions: 1, inquiries: 1, visits: 1, sales: 1 });
  assertNoErrors();
});
