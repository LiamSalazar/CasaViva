import { createHmac } from "node:crypto";
import { readFile } from "node:fs/promises";
import { expect, type Page } from "@playwright/test";

export function storageStatePath(email: string): string {
  return `playwright/.auth/${email.replace(/[^a-z0-9]+/gi, "-")}.json`;
}

export async function restoreAdminSession(page: Page, email = "liam@example.test") {
  const state = JSON.parse(await readFile(storageStatePath(email), "utf8"));
  await page.context().addCookies(state.cookies);
}

export function totp(secretHex: string, now = Date.now()): string {
  const counter = BigInt(Math.floor(now / 30_000));
  const buffer = Buffer.alloc(8);
  buffer.writeBigUInt64BE(counter);
  const digest = createHmac("sha1", Buffer.from(secretHex, "hex")).update(buffer).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const value = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return String(value).padStart(6, "0");
}

export function failOnPageErrors(page: Page, allowed: RegExp[] = []) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    const value = message.text();
    if (
      message.type() === "error" &&
      !value.includes("favicon") &&
      !allowed.some((pattern) => pattern.test(value))
    ) errors.push(value);
  });
  return () => expect(errors, errors.join("\n")).toEqual([]);
}

export async function loginAdmin(page: Page, email = "liam@example.test") {
  const password = process.env.E2E_ADMIN_PASSWORD;
  const secret = process.env.E2E_TOTP_SECRET;
  if (!password || !secret) throw new Error("Faltan credenciales temporales E2E.");
  await page.goto("/administracion/acceso");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByLabel("Código de seguridad").fill(totp(secret));
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page).toHaveURL(/\/administracion$/);
}
