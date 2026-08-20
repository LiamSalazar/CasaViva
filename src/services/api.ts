import type { Development, Guide, Location, Property } from "@/types";

const PLACEHOLDER = "/casaviva-placeholder.svg";

function csrfToken() {
  if (typeof document === "undefined") return "";
  return document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "";
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path.startsWith("/api/") ? path : `/api/v1/${path.replace(/^\//, "")}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken() ? { "X-CSRFToken": csrfToken() } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload?.error?.message || payload?.detail || "No fue posible completar la solicitud.") as Error & { status?: number; fields?: Record<string, string[]> };
    error.status = response.status;
    error.fields = payload?.error?.fields;
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json();
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
    condition: p.sourceType === "PRIVATE" ? "used" : "new",
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
    latitude: numberOrUndefined(p.latitude),
    longitude: numberOrUndefined(p.longitude),
    bedrooms: numberOrUndefined(p.bedrooms),
    bathrooms: numberOrUndefined(p.bathrooms),
    halfBathrooms: numberOrUndefined(p.halfBathrooms),
    parkingSpaces: numberOrUndefined(p.parkingSpaces),
    constructionM2: numberOrUndefined(p.constructionM2),
    landM2: numberOrUndefined(p.landM2),
    constructionAreaBasis: p.constructionAreaBasis,
    landAreaBasis: p.landAreaBasis,
    description: p.description || "",
    shortDescription: p.shortDescription || "",
    amenities: p.amenities || [],
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
    createdAt: p.createdAt,
    updatedAt: p.updatedAt,
    version: raw.version,
    offeringId: raw.offering || offering?.id,
    offeringVersion: offering?.version,
    propertyTypeId: offering?.property_type,
    stateId: offering?.state,
    municipalityId: offering?.municipality,
    developmentModelId: offering?.development_model,
    archivedAt: raw.archived_at || undefined,
    internal: offering ? { commissionPercent: numberOrUndefined(offering.default_commission_rate), notes: offering.internal_notes || undefined, reference: offering.internal_reference || undefined } : undefined,
  };
}

export const api = {
  publicListingPage: async (params = "") => {
    const data = await apiFetch<{ count: number; next: string | null; previous: string | null; results: Record<string, any>[] }>(`/api/v1/public/listings/${params ? `?${params}` : ""}`);
    return { ...data, results: data.results.map(mapProperty) };
  },
  publicListings: async (params = "") => {
    return (await api.publicListingPage(params)).results;
  },
  home: () => apiFetch<Record<string, any>>("/api/v1/public/home/"),
  developments: async () => (await apiFetch<{ results: Development[] }>("/api/v1/public/developments/")).results.map((d) => ({ ...d, heroImage: d.heroImage || PLACEHOLDER, gallery: d.gallery?.length ? d.gallery : [PLACEHOLDER], createdAt: d.createdAt || "", updatedAt: d.updatedAt || "", propertyIds: [] })),
  locations: async () => {
    const states = await apiFetch<Array<{ id: string; name: string; municipalities: Array<{ id: string; name: string; is_featured: boolean }> }>>("/api/v1/public/locations/");
    return states.flatMap((s) => s.municipalities.map((m): Location => ({ id: m.id, stateId: s.id, slug: m.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-"), name: m.name, state: s.name, description: "", heroImage: PLACEHOLDER, featured: m.is_featured })));
  },
  guides: async () => {
    const data = await apiFetch<{ results: Guide[] }>("/api/v1/public/guides/");
    return data.results.map((g) => ({ ...g, heroImage: g.heroImage || PLACEHOLDER }));
  },
  adminListings: async () => {
    const data = await apiFetch<{ results: Record<string, any>[] }>("/api/v1/admin/listings/?page_size=100");
    return data.results.map(mapProperty);
  },
  adminDevelopments: async () => {
    const data = await apiFetch<{ results: Array<Record<string, any>> }>("/api/v1/admin/developments/?page_size=100");
    return data.results.map((d): Development => ({
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
      latitude: numberOrUndefined(d.latitude),
      longitude: numberOrUndefined(d.longitude),
      heroImage: PLACEHOLDER,
      gallery: [],
      amenities: [],
      propertyIds: [],
      published: d.is_published,
      featured: d.is_featured,
      createdAt: d.created_at,
      updatedAt: d.updated_at,
      version: d.version,
    }));
  },
};
