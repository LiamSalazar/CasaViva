import { expect, test } from "@playwright/test";
import { failOnPageErrors, loginAdmin } from "./helpers";

test("login rechaza password y MFA incorrectos", async ({ page }) => {
  // Las dos solicitudes 400 son el resultado esperado de este caso adverso.
  const assertNoErrors = failOnPageErrors(page, [/Failed to load resource:.*400/]);
  await page.goto("/administracion/acceso");
  await page.getByLabel("Correo").fill("liam@example.test");
  await page.getByLabel("Contraseña").fill("incorrecta");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByText(/credenciales|incorrect/i)).toBeVisible();

  await page.getByLabel("Contraseña").fill(process.env.E2E_ADMIN_PASSWORD!);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByLabel("Código de seguridad").fill("000000");
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page.getByText("Código incorrecto.")).toBeVisible();
  await expect(page).toHaveURL(/\/administracion\/acceso$/);
  assertNoErrors();
});

test("Founder Admin opera negocio pero la API de usuarios devuelve 403", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await loginAdmin(page, "ana@example.test");
  await page.goto("/administracion/propiedades");
  await expect(page.getByRole("link", { name: "Nueva propiedad" })).toBeVisible();
  const response = await page.request.get("http://127.0.0.1:3000/api/v1/admin/users/");
  expect(response.status()).toBe(403);
  assertNoErrors();
});

test("Owner puede consultar usuarios", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await loginAdmin(page);
  await page.goto("/administracion/usuarios");
  await expect(page.getByRole("heading", { name: "Usuarios", level: 1 })).toBeVisible();
  await expect(page.getByText("liam@example.test")).toBeVisible();
  assertNoErrors();
});
