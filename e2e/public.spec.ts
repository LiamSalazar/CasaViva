import { expect, test } from "@playwright/test";
import { failOnPageErrors } from "./helpers";

test("home, catálogo dinámico, paginación, detalle y favorito usan el sistema real", async ({ page }) => {
  test.setTimeout(60_000);
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/");
  const heroTitle = page.locator("h1");
  await expect(heroTitle).toBeVisible();
  await expect(heroTitle).not.toHaveText("");
  await expect(page.getByRole("link", { name: "Casas nuevas" })).toHaveAttribute(
    "href",
    "/propiedades?propertyType=house&condition=new",
  );
  await page.goto("/propiedades");
  await expect(page.getByRole("button", { name: /^Dúplex/ })).toBeVisible();
  const listingsResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.status() === 200
      && url.pathname.replace(/\/$/, "") === "/api/v1/public/listings"
      && url.searchParams.get("property_type") === "duplex";
  });
  await page.getByRole("button", { name: /^Dúplex/ }).click();
  await expect(page).toHaveURL(/propertyType=duplex/);
  await listingsResponse;
  const resultSummary = page.getByText(/\d+ propiedades/).first();
  await expect(resultSummary).toBeVisible();
  await expect.poll(async () => Number((await resultSummary.textContent())?.match(/\d+/)?.[0] ?? 0)).toBeGreaterThan(24);
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeEnabled();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
  const favorite = page.getByRole("button", { name: /favorito/i }).first();
  await favorite.click();
  const favoritesNavigation = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.status() === 200
      && url.pathname === "/favoritos"
      && url.searchParams.has("_rsc");
  });
  await page.getByRole("link", { name: "Favoritos", exact: true }).click();
  await favoritesNavigation;
  await expect(page).toHaveURL(/\/favoritos$/);
  await expect(page.getByRole("heading", { name: "Favoritos", exact: true })).toBeVisible();
  await expect(page.locator('a[href="/propiedades/duplex-e2e-1"]')).toBeVisible();
  assertNoErrors();
});

test("slug inexistente muestra la página 404 sin traceback", async ({ page }) => {
  await page.goto("/propiedades/no-existe-e2e");
  await expect(page.getByRole("heading", { name: "Esta propiedad no está disponible" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Traceback");
});

test("home muestra ubicaciones en una sola línea con media real, flechas, drag y enlaces", async ({ page }) => {
  await page.goto("/");
  const carousel = page.getByRole("region", { name: "Carrusel de Ubicaciones" });
  const viewport = carousel.locator(".horizontal-carousel-viewport");
  const track = carousel.locator(".horizontal-carousel-track");
  expect(await carousel.locator(".location-tile").count()).toBeGreaterThan(6);
  expect(await track.evaluate((element) => getComputedStyle(element).flexWrap)).toBe("nowrap");
  expect(await viewport.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);

  const locationsResponse = await page.request.get("/api/v1/public/locations/");
  const states = await locationsResponse.json() as Array<{ municipalities: Array<{ slug: string | null; heroImage: string | null; is_featured: boolean }> }>;
  const firstLocation = states.flatMap((state) => state.municipalities).find((location) => location.is_featured && location.slug && location.heroImage);
  expect(firstLocation).toBeTruthy();
  const href = `/ubicaciones/${firstLocation!.slug}`;
  const locationLink = carousel.locator(`a[href="${href}"]`);
  await expect(locationLink).toBeVisible();
  const renderedSource = await locationLink.locator("img").evaluate((image: HTMLImageElement) => new URL(image.currentSrc).searchParams.get("url") || image.currentSrc);
  expect(renderedSource).toBe(firstLocation!.heroImage);
  expect(renderedSource).not.toContain("casaviva-placeholder.svg");

  const initial = await viewport.evaluate((element) => element.scrollLeft);
  await page.getByRole("button", { name: "Siguientes ubicaciones" }).click();
  await expect.poll(() => viewport.evaluate((element) => element.scrollLeft)).toBeGreaterThan(initial);
  await viewport.evaluate((element) => { element.scrollLeft = 0; });
  const box = await viewport.boundingBox();
  expect(box).toBeTruthy();
  await page.mouse.move(box!.x + box!.width * 0.8, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width * 0.2, box!.y + box!.height / 2, { steps: 8 });
  await page.mouse.up();
  expect(await viewport.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);

  await expect(page.locator(`[data-carousel="ubicaciones"] a[href="${href}"]`)).toHaveAttribute("href", href);
  await page.goto(href);
  await expect(page).toHaveURL(new RegExp(`${href}$`));
});

test("detalle directo sin galería usa estado neutral y no crea placeholders", async ({ page }) => {
  await page.route("**/api/v1/public/developments/no-media-e2e/", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: "00000000-0000-0000-0000-000000000099", slug: "no-media-e2e", name: "Desarrollo sin media",
      developerName: "Constructora", description: "Sin multimedia cargada.", shortDescription: "", state: "Estado de México",
      municipality: "Tecámac", latitude: null, longitude: null, heroImage: null, gallery: [], amenities: null,
      published: true, featured: false, publishedListingCount: 0, availableListingCount: 0, currentMinPrice: null,
    }),
  }));
  await page.route("**/api/v1/public/listings/?development=00000000-0000-0000-0000-000000000099", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
  }));
  await page.goto("/desarrollos/no-media-e2e");
  await expect(page.getByRole("heading", { name: "Desarrollo sin media" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Galería" })).toHaveCount(0);
  await expect(page.locator('img[src*="casaviva-placeholder.svg"]')).toHaveCount(0);
});

test("detalle de guía fuera de la primera página usa su endpoint y las galerías abren fotos y planos", async ({ page }) => {
  const assertNoErrors = failOnPageErrors(page);
  await page.goto("/guias/guia-publica-e2e-00");
  await expect(page.getByRole("heading", { name: "Guía pública E2E 00" })).toBeVisible();

  await page.goto("/propiedades/duplex-e2e-1");
  await page.getByRole("button", { name: /2 Fotos/ }).click();
  await expect(page.getByRole("dialog", { name: "Galería de propiedad" })).toContainText("Foto 1 / 2");
  await page.getByRole("button", { name: "Cerrar" }).click();
  await page.getByRole("button", { name: /1 Planos/ }).click();
  await expect(page.getByRole("dialog", { name: "Galería de propiedad" })).toContainText("Plano 1 / 1");
  assertNoErrors();
});

test("desarrollo y ubicación cargan el inventario completo y la galería del desarrollo es interactiva", async ({ page }) => {
  test.setTimeout(60_000);
  const assertNoErrors = failOnPageErrors(page);
  const developmentsResponse = await page.request.get("/api/v1/public/developments/");
  const developments = (await developmentsResponse.json()).results as Array<{ slug: string; publishedListingCount: number }>;
  const development = developments.find((item) => item.publishedListingCount > 24);
  expect(development).toBeTruthy();

  await page.goto(`/desarrollos/${development!.slug}`);
  await expect(page.getByText("Inventario desarrollo E2E 1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Abrir foto 2 de/ }).click();
  await expect(page.getByRole("dialog", { name: /Galería de/ })).toContainText("Foto 2 / 2");
  await page.getByRole("button", { name: "Cerrar" }).click();

  const propertyResponse = await page.request.get("/api/v1/public/listings/duplex-e2e-1/");
  const municipality = (await propertyResponse.json()).municipality as string;
  const locationsResponse = await page.request.get("/api/v1/public/locations/");
  const states = await locationsResponse.json() as Array<{ municipalities: Array<{ name: string; slug: string | null }> }>;
  const location = states.flatMap((state) => state.municipalities).find((item) => item.name === municipality);
  expect(location).toBeTruthy();
  const locationSlug = location!.slug || location!.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-");
  await page.goto(`/ubicaciones/${locationSlug}`);
  await expect(page.getByText("Dúplex E2E 1", { exact: true })).toBeVisible();
  assertNoErrors();
});

test("@mobile mantiene accesibles home, resultados y detalle", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  const locationViewport = page.getByRole("region", { name: "Carrusel de Ubicaciones" }).locator(".horizontal-carousel-viewport");
  expect(await locationViewport.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  if ((page.viewportSize()?.width || 0) <= 767) {
    const viewportWidth = await locationViewport.evaluate((element) => element.clientWidth);
    const cardWidth = await page.getByRole("region", { name: "Carrusel de Ubicaciones" }).locator(".location-tile").first().evaluate((element) => element.getBoundingClientRect().width);
    expect(cardWidth).toBeLessThan(viewportWidth);
    expect(cardWidth).toBeGreaterThan(viewportWidth * 0.6);
  }
  await page.goto("/propiedades?propertyType=duplex");
  await expect(page.getByRole("button", { name: "Filtros" })).toBeVisible();
  await page.goto("/propiedades/duplex-e2e-1");
  await expect(page.getByRole("heading", { name: "Dúplex E2E 1" })).toBeVisible();
});
