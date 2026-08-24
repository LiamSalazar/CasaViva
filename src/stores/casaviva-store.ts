"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { api, apiFetch, buildPropertyPayload, fetchAllPages, mapProperty } from "@/services/api";
import type { Development, Guide, HomeContent, Inquiry, Location, Property, SavedSearch } from "@/types";

interface CasaVivaState {
  properties: Property[]; developments: Development[]; locations: Location[]; guides: Guide[]; inquiries: Inquiry[]; homeContent: HomeContent;
  favorites: string[]; notes: Record<string, string>; savedSearches: SavedSearch[];
  adminAuthenticated: boolean; adminInitialized: boolean; hydrated: boolean; loading: boolean; error?: string;
  initialize: () => Promise<void>; refreshAdmin: () => Promise<void>; setHydrated: (value: boolean) => void;
  saveProperty: (item: Property) => Promise<void>; deleteProperty: (id: string) => Promise<void>;
  saveDevelopment: (item: Development) => Promise<void>; deleteDevelopment: (id: string) => Promise<void>;
  saveLocation: (item: Location) => Promise<void>; deleteLocation: (id: string) => Promise<void>;
  saveGuide: (item: Guide) => Promise<void>; deleteGuide: (id: string) => Promise<void>;
  addInquiry: (item: Inquiry) => Promise<void>; setInquiryStatus: (id: string, status: Inquiry["status"]) => Promise<void>;
  setHomeContent: (item: HomeContent) => Promise<void>; toggleFavorite: (id: string) => void; clearFavorites: () => void;
  setNote: (id: string, note: string) => void; saveSearch: (item: SavedSearch) => void; login: () => void; logout: () => Promise<void>;
}

const emptyHome: HomeContent = { heroEyebrow: "Propiedades en México", heroTitle: "Encuentra el lugar que quieres llamar hogar", heroSlides: [], featuredPropertyIds: [], featuredLocationIds: [], featuredDevelopmentIds: [], editorialTitle: "", editorialBody: "", editorialImage: "/casaviva-placeholder.svg" };
const optionalNumber = (value: unknown) => value === null || value === undefined || value === "" ? undefined : Number(value);

async function persistLocationContent(item: Location) {
  let version = item.contentVersion;
  if (item.contentId && item.archivedAt) {
    const restored = await apiFetch<{ version: number }>(`/api/v1/admin/location-content/${item.contentId}/restore/`, { method: "POST", body: "{}" });
    version = restored.version;
  }
  const payload = { municipality: item.id, slug: item.slug, description: item.description, hero_media: item.heroMediaId || null, is_featured: item.featured, latitude: item.latitude ?? null, longitude: item.longitude ?? null, ...(item.contentId ? { version } : {}) };
  await apiFetch(item.contentId ? `/api/v1/admin/location-content/${item.contentId}/` : "/api/v1/admin/location-content/", { method: item.contentId ? "PATCH" : "POST", body: JSON.stringify(payload) });
}

export const useCasaVivaStore = create<CasaVivaState>()(
  persist(
    (set, get) => ({
      properties: [], developments: [], locations: [], guides: [], inquiries: [], homeContent: emptyHome,
      favorites: [], notes: {}, savedSearches: [], adminAuthenticated: false, adminInitialized: false, hydrated: false, loading: false,
      setHydrated: (hydrated) => set({ hydrated }),
      initialize: async () => {
        if (get().loading) return;
        set({ loading: true, error: undefined });
        try {
          const [properties, developments, locations, guides, home, session] = await Promise.all([api.publicListings(), api.developments(), api.locations(), api.guides(), api.home(), apiFetch<{ authenticated?: boolean }>("/api/v1/auth/me/").then((value) => value.authenticated !== false).catch(() => false)]);
          const featured: Property[] = (home.featured_listings || []).map(mapProperty);
          const heroRaw: Record<string, any>[] = home.hero || [];
          const hero: Property[] = heroRaw.map(mapProperty);
          const merged = [...properties];
          [...featured, ...hero].forEach((p) => { if (!merged.some((x) => x.id === p.id)) merged.push(p); });
          set({
            properties: merged, developments, locations, guides,
            homeContent: {
              id: home.content?.id, version: home.content?.version,
              heroEyebrow: home.content?.hero_eyebrow || "Propiedades en México", heroTitle: home.content?.hero_title || "Encuentra el lugar que quieres llamar hogar",
              heroSlides: hero.map((p, index) => ({ id: String(heroRaw[index]?.slideId || `hero-${p.id}`), propertyId: p.id, eyebrow: heroRaw[index]?.eyebrowOverride || p.developmentName || p.municipality || "Propiedad", title: heroRaw[index]?.titleOverride || p.title, subtitle: heroRaw[index]?.subtitleOverride || p.shortDescription, order: index, active: true })),
              featuredPropertyIds: featured.map((p) => p.id), featuredLocationIds: locations.filter((x) => x.featured).map((x) => x.id), featuredDevelopmentIds: developments.filter((x) => x.featured).map((x) => x.id),
              editorialTitle: home.content?.editorial_title || "", editorialBody: home.content?.editorial_body || "", editorialImage: home.content?.editorial_media_url || "/casaviva-placeholder.svg", editorialMediaId: home.content?.editorial_media || undefined,
            },
            loading: false, hydrated: true, adminAuthenticated: session,
          });
        } catch (error) {
          set({ loading: false, hydrated: true, error: error instanceof Error ? error.message : "No fue posible cargar CasaViva." });
        }
      },
      refreshAdmin: async () => {
        const [properties, developments, inquiries, publicLocations, locationContent, guides] = await Promise.all([api.adminListings(), api.adminDevelopments(), fetchAllPages<any>("/api/v1/admin/inquiries/?page_size=100"), api.locations(), api.adminLocationContents(), fetchAllPages<any>("/api/v1/admin/guides/?page_size=100")]);
        const locations = publicLocations.map((location) => {
          const content = locationContent.find((item) => item.municipality === location.id);
          return content ? { ...location, slug: content.slug, description: content.description || "", heroImage: content.heroImage || location.heroImage, featured: content.is_featured, latitude: optionalNumber(content.latitude), longitude: optionalNumber(content.longitude), contentId: content.id, contentVersion: content.version, heroMediaId: content.hero_media || undefined, hasContent: !content.archived_at, archivedAt: content.archived_at || undefined } : location;
        });
        set((state) => ({
          properties,
          developments,
          locations,
          guides: guides.map((g) => ({ ...g, heroImage: g.heroImage || "/casaviva-placeholder.svg", heroMediaId: g.hero_media || undefined })),
          inquiries: inquiries.map((x) => ({ id: x.id, createdAt: x.created_at, name: x.lead_name, email: "", message: x.message || "", source: x.intent === "VISIT_REQUEST" ? "visit" : x.intent === "GENERAL_CONTACT" ? "contact" : "property", propertyId: x.listing || undefined, subject: x.subject || undefined, privacyConsent: true, status: x.status.toLowerCase() })),
          homeContent: {
            ...state.homeContent,
            featuredPropertyIds: properties.filter((item) => item.featured).map((item) => item.id),
            featuredDevelopmentIds: developments.filter((item) => item.featured).map((item) => item.id),
            featuredLocationIds: locations.filter((item) => item.featured && item.hasContent).map((item) => item.id),
          },
          adminInitialized: true,
        }));
      },
      saveProperty: async (item) => {
        const current = get().properties.find((x) => x.id === item.id);
        const location = get().locations.find((x) => x.id === item.municipalityId || (x.name === item.municipality && x.state === item.state));
        const propertyTypeId = item.propertyTypeId || (await api.propertyTypes()).find((x) => x.code === item.propertyType)?.id;
        if (!propertyTypeId) throw new Error("El tipo de propiedad seleccionado ya no está disponible.");
        const payload = buildPropertyPayload(item, propertyTypeId, location);
        await apiFetch(current ? `/api/v1/admin/properties/${item.id}/` : "/api/v1/admin/properties/", {
          method: current ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        });
        await get().refreshAdmin();
      },
      deleteProperty: async (id) => { await apiFetch(`/api/v1/admin/properties/${id}/`, { method: "DELETE" }); await get().refreshAdmin(); },
      saveDevelopment: async (item) => {
        const current = get().developments.find((x) => x.id === item.id);
        const payload = { developer: item.developerId, name: item.name, slug: item.slug, state: item.stateId, municipality: item.municipalityId, locality: item.localityId || null, neighborhood: item.neighborhoodId || null, street_address: item.address || null, postal_code: item.postalCode || null, short_description: item.shortDescription || null, description: item.description || null, latitude: item.latitude ?? null, longitude: item.longitude ?? null, amenity_ids: item.amenityIds || [], media_input: item.mediaAssets?.length ? item.mediaAssets.map((media) => ({ media_id: media.mediaId, role: media.role, sort_order: media.sortOrder })) : item.heroMediaId ? [{ media_id: item.heroMediaId, role: "HERO", sort_order: 0 }] : [], is_published: item.published, is_featured: item.featured, ...(current ? { version: item.version } : {}) };
        await apiFetch(current ? `/api/v1/admin/developments/${item.id}/` : "/api/v1/admin/developments/", { method: current ? "PATCH" : "POST", body: JSON.stringify(payload) });
        set({ developments: await api.adminDevelopments() });
      },
      deleteDevelopment: async (id) => { await apiFetch(`/api/v1/admin/developments/${id}/`, { method: "DELETE" }); set((s) => ({ developments: s.developments.filter((x) => x.id !== id) })); },
      saveLocation: async (item) => {
        await persistLocationContent(item);
        await get().refreshAdmin();
      },
      deleteLocation: async (id) => {
        const location = get().locations.find((item) => item.id === id);
        if (!location?.contentId) return;
        await apiFetch(`/api/v1/admin/location-content/${location.contentId}/`, { method: "DELETE" });
        await get().refreshAdmin();
      },
      saveGuide: async (item) => {
        const current = get().guides.find((x) => x.id === item.id);
        const payload = { slug: item.slug, title: item.title, excerpt: item.excerpt, content: item.content, category: item.category, hero_media: item.heroMediaId || null, published: item.published, featured: item.featured, ...(current ? { version: current.version } : {}) };
        await apiFetch(current ? `/api/v1/admin/guides/${item.id}/` : "/api/v1/admin/guides/", { method: current ? "PATCH" : "POST", body: JSON.stringify(payload) });
        const guides = await fetchAllPages<any>("/api/v1/admin/guides/?page_size=100");
        set({ guides: guides.map((g) => ({ ...g, heroImage: g.heroImage || "/casaviva-placeholder.svg", heroMediaId: g.hero_media || undefined })) });
      },
      deleteGuide: async (id) => { await apiFetch(`/api/v1/admin/guides/${id}/`, { method: "DELETE" }); set((s) => ({ guides: s.guides.filter((x) => x.id !== id) })); },
      addInquiry: async (item) => { await apiFetch("/api/v1/public/inquiries/", { method: "POST", body: JSON.stringify({ first_name: item.name, email: item.email, phone: item.phone, message: item.message, listing_slug: item.listingSlug, session_id: item.sessionId, visitor_id: item.visitorId, privacy_consent: item.privacyConsent, intent: item.source === "visit" ? "VISIT_REQUEST" : item.source === "contact" ? "GENERAL_CONTACT" : "INFORMATION", subject: item.subject || null }) }); },
      setInquiryStatus: async (id, status) => { await apiFetch(`/api/v1/admin/inquiries/${id}/`, { method: "PATCH", body: JSON.stringify({ status: status.toUpperCase() }) }); await get().refreshAdmin(); },
      setHomeContent: async (item) => {
        const records = await apiFetch<{ results: Array<{ id: string; version: number }> }>("/api/v1/admin/content/?page_size=10");
        const currentContent = records.results[0];
        const payload = { key: "main", hero_eyebrow: item.heroEyebrow, hero_title: item.heroTitle, editorial_title: item.editorialTitle, editorial_body: item.editorialBody, editorial_media: item.editorialMediaId || null, hero_slides: item.heroSlides.map((slide) => ({ listing: slide.propertyId, eyebrow_override: slide.eyebrow || null, title_override: slide.title || null, subtitle_override: slide.subtitle || null, sort_order: slide.order, is_active: slide.active })), ...(currentContent ? { version: currentContent.version } : {}) };
        await apiFetch(currentContent ? `/api/v1/admin/content/${currentContent.id}/` : "/api/v1/admin/content/", { method: currentContent ? "PATCH" : "POST", body: JSON.stringify(payload) });
        const featuredListings = new Set([...item.featuredPropertyIds, ...item.heroSlides.filter((x) => x.active).map((x) => x.propertyId)]);
        const updates: Promise<unknown>[] = [];
        for (const listing of get().properties) {
          const featured = featuredListings.has(listing.id);
          if (listing.featured !== featured) updates.push(apiFetch(`/api/v1/admin/properties/${listing.id}/featured/`, { method: "POST", body: JSON.stringify({ is_featured: featured, listing_version: listing.version }) }));
        }
        for (const development of get().developments) {
          const featured = item.featuredDevelopmentIds.includes(development.id);
          if (development.featured !== featured) updates.push(apiFetch(`/api/v1/admin/developments/${development.id}/`, { method: "PATCH", body: JSON.stringify({ is_featured: featured, version: development.version }) }));
        }
        for (const location of get().locations) {
          const featured = item.featuredLocationIds.includes(location.id);
          if (location.featured !== featured) updates.push(persistLocationContent({ ...location, featured }));
        }
        await Promise.all(updates);
        set({ homeContent: item });
        await get().refreshAdmin();
      },
      toggleFavorite: (id) => set((s) => ({ favorites: s.favorites.includes(id) ? s.favorites.filter((x) => x !== id) : [...s.favorites, id] })),
      clearFavorites: () => set({ favorites: [] }), setNote: (id, note) => set((s) => ({ notes: { ...s.notes, [id]: note } })),
      saveSearch: (item) => set((s) => ({ savedSearches: [item, ...s.savedSearches] })), login: () => set({ adminAuthenticated: true, adminInitialized: false }),
      logout: async () => { await apiFetch("/api/v1/auth/logout/", { method: "POST", body: "{}" }).catch(() => undefined); set({ adminAuthenticated: false, adminInitialized: false, inquiries: [] }); },
    }),
    { name: "casaviva-browser-v2", storage: createJSONStorage(() => localStorage), partialize: (s) => ({ favorites: s.favorites, notes: s.notes, savedSearches: s.savedSearches }) },
  ),
);
