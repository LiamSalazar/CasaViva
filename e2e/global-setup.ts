import type { FullConfig } from "@playwright/test";

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use.baseURL || "http://127.0.0.1:3000";
  for (const route of [
    "/administracion/contenido/nosotros",
    "/administracion/contenido/identidad",
    "/nosotros",
    "/contacto",
    "/",
  ]) {
    const response = await fetch(`${baseURL}${route}`);
    if (!response.ok) throw new Error(`E2E readiness failed for ${route}: ${response.status}`);
  }
}
