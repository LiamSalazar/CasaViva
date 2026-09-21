import { expect, test } from "@playwright/test";

async function fillContact(page: import("@playwright/test").Page, suffix: string) {
  await page.goto("/contacto");
  await expect(page.getByTestId("turnstile-widget")).toBeVisible();
  await page.getByLabel("Nombre").fill(`Turnstile ${suffix}`);
  await page.getByLabel("Correo").fill(`turnstile-${suffix}@example.test`);
  await page.getByLabel("Motivo").selectOption("GENERAL_COMMENT");
  await page.getByLabel("Mensaje").fill("Consulta E2E para comprobar la protección antibot.");
  await page.getByRole("checkbox", { name: "He leído el Aviso de Privacidad." }).check();
}

test("Turnstile mocked acepta token válido y lo reinicia", async ({ page }) => {
  const tokens: string[] = [];
  await page.route("**/api/v1/public/inquiries/", async (route) => {
    tokens.push(JSON.parse(route.request().postData() || "{}").antibot_token);
    await route.continue();
  });
  await fillContact(page, "valid");
  await page.getByRole("button", { name: "Enviar mensaje" }).click();
  await expect(page.getByRole("heading", { name: "Gracias por escribirnos." })).toBeVisible();
  await page.getByRole("button", { name: "Enviar otro mensaje" }).click();
  expect(tokens).toEqual(["e2e-valid-token"]);
  await expect(page.getByTestId("turnstile-widget")).toBeVisible();
});

for (const [label, replacement] of [["inválido", "invalid-token"], ["ausente", ""]] as const) {
  test(`Turnstile mocked rechaza token ${label}`, async ({ page }) => {
    await page.route("**/api/v1/public/inquiries/", async (route) => {
      const payload = JSON.parse(route.request().postData() || "{}");
      payload.antibot_token = replacement;
      await route.continue({ postData: JSON.stringify(payload), headers: { ...route.request().headers(), "content-type": "application/json" } });
    });
    await fillContact(page, label === "inválido" ? "invalid" : label);
    await page.getByRole("button", { name: "Enviar mensaje" }).click();
    await expect(page.getByText("No pudimos enviar la consulta. Intenta nuevamente.")).toBeVisible();
  });
}
