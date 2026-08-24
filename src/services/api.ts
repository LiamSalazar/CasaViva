import type { ApiPage, Development, Guide, Location, Property, PropertyTypeOption, SearchOptions, SiteSettings } from "@/types";

const PLACEHOLDER = "/casaviva-placeholder.svg";

function csrfToken() {
  if (typeof document === "undefined") return "";
  return document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "";
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path.startsWith("/api/") ? path : `/api/v1/${path.replace(/^\//, "")}`, {
    ...init,
    cache: init.cache ?? "no-store",
    credentials: "include",
    headers: {
      ...(init.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken() ? { "X-CSRFToken": csrfToken() } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const firstFieldMessage = Object.values(payload || {}).flat().find((value) => typeof value === "string");
    const error = new Error(payload?.error?.message || payload?.detail || firstFieldMessage || "No fue posible completar la solicitud.") as Error & { status?: number; fields?: Record<string, string[]> };
    error.status = response.status;
    error.fields = payload?.error?.fields;
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function fetchAllPages<T>(path: string): Promise<T[]> {
  const results: T[] = [];
  let next: string | null = path;
  while (next) {
    const normalized: string = next.startsWith("http") ? `${new URL(next).pathname}${new URL(next).search}` : next;
    const page: ApiPage<T> = await apiFetch<ApiPage<T>>(normalized);
    results.push(...page.results);
    next = page.next;
  }
  return results;
}

function numberOrUndefined(value: unknown): number | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

export function mapProperty(raw: Record<string, any>): Property {
  const p = raw.public_data || raw;
  const offering = raw.offering_detail;
  return {
    id: String(p.id),
    slug: p.slug,
    title: p.title,
    operation: "sale",
    propertyType: p.propertyType,
    propertyTypeName: p.propertyTypeName,
    condition: p.condition || undefined,
    status: p.status || "available",
    published: Boolean(p.published),
    featured: Boolean(p.featured),
    price: numberOrUndefined(p.price),
    priceMax: numberOrUndefined(p.priceMax),
    currency: p.currency || "MXN",
    priceLabel: p.priceLabel,
    state: p.state || undefined,
    municipality: p.municipality || undefined,
    neighborhood: p.neighborhood || undefined,
    address: offering?.street_address || undefined,
    latitude: numberOrUndefined(p.latitude),
    longitude: numberOrUndefined(p.longitude),
    bedrooms: numberOrUndefined(p.bedrooms),
    bedroomsMax: numberOrUndefined(offering?.bedrooms_max),
    bathrooms: numberOrUndefined(p.bathrooms),
    fullBathrooms: numberOrUndefined(offering?.full_bathrooms ?? p.fullBathrooms),
    halfBathrooms: numberOrUndefined(p.halfBathrooms),
    parkingSpaces: numberOrUndefined(p.parkingSpaces),
    parkingMax: numberOrUndefined(offering?.parking_max),
    levels: numberOrUndefined(offering?.levels_min),
    levelsMax: numberOrUndefined(offering?.levels_max),
    constructionM2: numberOrUndefined(offering?.construction_area_min ?? p.constructionM2),
    landM2: numberOrUndefined(offering?.land_area_min ?? p.landM2),
    constructionM2Max: numberOrUndefined(offering?.construction_area_max),
    landM2Max: numberOrUndefined(offering?.land_area_max),
    gardenM2: numberOrUndefined(offering?.garden_area_min),
    gardenM2Max: numberOrUndefined(offering?.garden_area_max),
    constructionAreaBasis: p.constructionAreaBasis,
    landAreaBasis: p.landAreaBasis,
    gardenAreaBasis: offering?.garden_area_basis || undefined,
    description: p.description || "",
    shortDescription: p.shortDescription || "",
    amenities: p.amenities || [],
    amenitySlugs: p.amenitySlugs || [],
    amenityIds: offering?.amenity_ids || [],
    featureValues: offering?.feature_values || [],
    internalFeatures: [],
    externalFeatures: [],
    developerId: p.developerId || undefined,
    developerName: p.developerName || undefined,
    developmentId: p.developmentId || undefined,
    developmentName: p.developmentName || undefined,
    modelName: p.modelName || undefined,
    sourceType: p.sourceType,
    heroImage: p.heroImage || PLACEHOLDER,
    gallery: p.gallery?.length ? p.gallery : [PLACEHOLDER],
    floorplans: p.floorplans || [],
    createdAt: p.createdAt,
    updatedAt: p.updatedAt,
    version: raw.version,
    offeringId: raw.offering || offering?.id,
    offeringVersion: offering?.version,
    propertyTypeId: offering?.property_type,
    stateId: offering?.state,
    municipalityId: offering?.municipality,
    localityId: offering?.locality,
    neighborhoodId: offering?.neighborhood,
    postalCode: offering?.postal_code || undefined,
    developmentModelId: offering?.development_model,
    mediaAssets: (raw.media || []).map((media: Record<string, any>) => ({ mediaId: media.media_id, role: media.role, sortOrder: media.sort_order, url: media.url })),
    heroMediaId: raw.media?.find((media: Record<string, any>) => media.role === "HERO")?.media_id,
    archivedAt: raw.archived_at || undefined,
    internal: offering ? { commissionPercent: numberOrUndefined(offering.default_commission_rate), notes: offering.internal_notes || undefined, reference: offering.internal_reference || undefined } : undefined,
  };
}

export function buildPropertyPayload(item: Property, propertyTypeId: string, location?: Location) {
  const developerSource = item.sourceType === "DEVELOPER";
  return {
    offering_version: item.offeringVersion,
    listing_version: item.version,
    offering: {
      source_type: item.sourceType || "PRIVATE",
      condition: item.condition ? item.condition.toUpperCase() : null,
      development_model: developerSource ? item.developmentModelId || null : null,
      property_type: propertyTypeId,
      state: developerSource ? null : item.stateId || location?.stateId || null,
      municipality: developerSource ? null : item.municipalityId || location?.id || null,
      locality: developerSource ? item.localityId || null : item.localityId || null,
      neighborhood: item.neighborhoodId || null,
      street_address: item.address || null,
      postal_code: item.postalCode || null,
      latitude: item.latitude ?? null,
      longitude: item.longitude ?? null,
      bedrooms_min: item.bedrooms ?? null,
      bedrooms_max: item.bedroomsMax ?? null,
      bathrooms_total: item.bathrooms ?? null,
      full_bathrooms: item.fullBathrooms ?? null,
      half_bathrooms: item.halfBathrooms ?? null,
      parking_min: item.parkingSpaces ?? null,
      parking_max: item.parkingMax ?? null,
      levels_min: item.levels ?? null,
      levels_max: item.levelsMax ?? null,
      construction_area_min: item.constructionM2 ?? null,
      construction_area_max: item.constructionM2Max ?? null,
      construction_area_basis: item.constructionM2 !== undefined || item.constructionM2Max !== undefined ? item.constructionAreaBasis || (item.constructionM2Max !== undefined && item.constructionM2 === undefined ? "UP_TO" : "EXACT") : null,
      land_area_min: item.landM2 ?? null,
      land_area_max: item.landM2Max ?? null,
      land_area_basis: item.landM2 !== undefined || item.landM2Max !== undefined ? item.landAreaBasis || (item.landM2Max !== undefined && item.landM2 === undefined ? "UP_TO" : "EXACT") : null,
      garden_area_min: item.gardenM2 ?? null,
      garden_area_max: item.gardenM2Max ?? null,
      garden_area_basis: item.gardenM2 !== undefined || item.gardenM2Max !== undefined ? item.gardenAreaBasis || (item.gardenM2Max !== undefined ? "RANGE" : "EXACT") : null,
      internal_reference: item.internal?.reference || null,
      internal_notes: item.internal?.notes || null,
      default_commission_rate: item.internal?.commissionPercent ?? null,
      amenity_ids: item.amenityIds || [],
      feature_values_input: item.featureValues || [],
    },
    listing: {
      title: item.title,
      slug: item.slug,
      short_description: item.shortDescription,
      description: item.description,
      is_featured: item.featured,
    },
    price: {
      price_type: item.price === undefined ? "ON_REQUEST" : (item.priceLabel || "fixed").replace("on-request", "ON_REQUEST").toUpperCase(),
      amount_min: item.price ?? null,
      amount_max: item.priceMax ?? null,
      currency: item.currency || "MXN",
    },
    availability: { status: item.status.toUpperCase() },
    media: item.mediaAssets?.length
      ? item.mediaAssets.map((media) => ({ media_id: media.mediaId, role: media.role, sort_order: media.sortOrder }))
      : item.heroMediaId ? [{ media_id: item.heroMediaId, role: "HERO", sort_order: 0 }] : [],
    published: item.published,
  };
}

export const api = {
  publicListingPage: async (params = "") => {
    const data = await apiFetch<{ count: number; next: string | null; previous: string | null; results: Record<string, any>[]; facets?: import("@/types").SearchFacets }>(`/api/v1/public/listings/${params ? `?${params}` : ""}`);
    return { ...data, results: data.results.map(mapProperty) };
  },
  publicListings: async (params = "") => {
    return (await api.publicListingPage(params)).results;
  },
  publicListingsAll: async (params = "") => {
    const path = `/api/v1/public/listings/${params ? `?${params}` : ""}`;
    return (await fetchAllPages<Record<string, any>>(path)).map(mapProperty);
  },
  similarListings: async (slug: string) => (await apiFetch<Record<string, any>[]>(`/api/v1/public/listings/${slug}/similar/`)).map(mapProperty),
  favoriteListings: async (ids: string[]) => {
    const results: Property[] = [];
    for (let index = 0; index < ids.length; index += 100) {
      const batch = ids.slice(index, index + 100);
      results.push(...(await apiFetch<Record<string, any>[]>(`/api/v1/public/listings/favorites/?ids=${encodeURIComponent(batch.join(","))}`)).map(mapProperty));
    }
    return results;
  },
  home: () => apiFetch<Record<string, any>>("/api/v1/public/home/"),
  searchOptions: () => apiFetch<SearchOptions>("/api/v1/public/search-options/"),
  developments: async () => (await apiFetch<{ results: Development[] }>("/api/v1/public/developments/")).results.map((d) => ({ ...d, heroImage: d.heroImage || PLACEHOLDER, gallery: d.gallery?.length ? d.gallery : [PLACEHOLDER], createdAt: d.createdAt || "", updatedAt: d.updatedAt || "", propertyIds: [], currentMinPrice: numberOrUndefined(d.currentMinPrice) })),
  locations: async () => {
    const states = await apiFetch<Array<{ id: string; name: string; municipalities: Array<{ id: string; name: string; slug?: string; description: string; heroImage?: string; is_featured: boolean; latitude?: string; longitude?: string; content_id?: string }> }>>("/api/v1/public/locations/");
    return states.flatMap((s) => s.municipalities.map((m): Location => ({ id: m.id, stateId: s.id, slug: m.slug || m.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-"), name: m.name, state: s.name, description: m.description || "", heroImage: m.heroImage || PLACEHOLDER, featured: m.is_featured, latitude: numberOrUndefined(m.latitude), longitude: numberOrUndefined(m.longitude), contentId: m.content_id, hasContent: Boolean(m.content_id) })));
  },
  guides: async () => (await fetchAllPages<Guide>("/api/v1/public/guides/")).map((g) => ({ ...g, heroImage: g.heroImage || PLACEHOLDER })),
  guide: async (slug: string) => {
    const guide = await apiFetch<Guide>(`/api/v1/public/guides/${encodeURIComponent(slug)}/`);
    return { ...guide, heroImage: guide.heroImage || PLACEHOLDER };
  },
  siteSettings: async () => {
    const page = await apiFetch<ApiPage<SiteSettings>>("/api/v1/public/site-settings/");
    return page.results[0] || null;
  },
  adminListings: async () => {
    return (await fetchAllPages<Record<string, any>>("/api/v1/admin/properties/?page_size=100")).map(mapProperty);
  },
  adminDevelopments: async () => {
    const data = await fetchAllPages<Record<string, any>>("/api/v1/admin/developments/?page_size=100");
    return data.map((d): Development => ({
      id: d.id,
      slug: d.slug,
      name: d.name,
      developerName: d.developer_name,
      developerId: d.developer,
      description: d.description || "",
      shortDescription: d.short_description || "",
      state: d.state_name,
      stateId: d.state,
      municipality: d.municipality_name,
      municipalityId: d.municipality,
      localityId: d.locality || undefined,
      neighborhoodId: d.neighborhood || undefined,
      neighborhood: d.neighborhood_name || undefined,
      address: d.street_address || undefined,
      postalCode: d.postal_code || undefined,
      latitude: numberOrUndefined(d.latitude),
      longitude: numberOrUndefined(d.longitude),
      heroImage: d.media?.find((media: Record<string, any>) => media.role === "HERO")?.url || PLACEHOLDER,
      gallery: d.media?.map((media: Record<string, any>) => media.url) || [],
      amenities: d.amenities || [],
      amenityIds: d.amenity_ids || [],
      mediaAssets: (d.media || []).map((media: Record<string, any>) => ({ mediaId: media.media_id, role: media.role, sortOrder: media.sort_order, url: media.url })),
      heroMediaId: d.media?.find((media: Record<string, any>) => media.role === "HERO")?.media_id,
      propertyIds: [],
      published: d.is_published,
      featured: d.is_featured,
      createdAt: d.created_at,
      updatedAt: d.updated_at,
      version: d.version,
    }));
  },
  adminLocationContents: () => fetchAllPages<Record<string, any>>("/api/v1/admin/location-content/?page_size=100&archived=all"),
  propertyTypes: () => fetchAllPages<PropertyTypeOption>("/api/v1/admin/property-types/?page_size=100&is_active=true"),
};
