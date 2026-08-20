"use client";

import { useCasaVivaStore } from "@/stores/casaviva-store";
import type {
  Development,
  Guide,
  HomeContent,
  Inquiry,
  Location,
  MatchCriteria,
  Property,
  PropertyFilters,
  PropertySort,
  SavedSearch,
} from "@/types";

export type PublicProperty = Omit<Property, "internal">;
export const toPublicProperty = (property: Property): PublicProperty => {
  const copy = { ...property };
  delete copy.internal;
  return copy;
};

export function filterProperties(
  properties: Property[],
  filters: PropertyFilters = {},
  includeDrafts = false,
) {
  const text = filters.query?.trim().toLowerCase();
  return properties.filter((p) => {
    if (!includeDrafts && !p.published)
      return false;
    if (filters.state && p.state !== filters.state) return false;
    if (
      filters.municipality &&
      p.municipality?.toLowerCase() !== filters.municipality.toLowerCase()
    )
      return false;
    if (filters.propertyType && p.propertyType !== filters.propertyType)
      return false;
    if (filters.condition && p.condition !== filters.condition) return false;
    if (filters.minPrice && (p.price === undefined || p.price < filters.minPrice)) return false;
    if (filters.maxPrice && (p.price === undefined || p.price > filters.maxPrice)) return false;
    if (filters.minBedrooms && (p.bedrooms === undefined || p.bedrooms < filters.minBedrooms)) return false;
    if (filters.minBathrooms && (p.bathrooms === undefined || p.bathrooms < filters.minBathrooms))
      return false;
    if (filters.minParking && (p.parkingSpaces || 0) < filters.minParking)
      return false;
    if (
      filters.minConstructionM2 &&
      (p.constructionM2 || 0) < filters.minConstructionM2
    )
      return false;
    if (filters.minLandM2 && (p.landM2 || 0) < filters.minLandM2) return false;
    if (filters.developmentId && p.developmentId !== filters.developmentId)
      return false;
    if (
      filters.amenities?.length &&
      !filters.amenities.every((a) =>
        [...p.amenities, ...p.internalFeatures, ...p.externalFeatures].some(
          (x) => x.toLowerCase().includes(a.toLowerCase()),
        ),
      )
    )
      return false;
    if (
      text &&
      ![p.title, p.municipality, p.state, p.neighborhood]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    )
      return false;
    return true;
  });
}

export function sortProperties(
  properties: Property[],
  sort: PropertySort = "recent",
) {
  return [...properties].sort((a, b) =>
    sort === "price-asc"
      ? (a.price ?? Number.POSITIVE_INFINITY) - (b.price ?? Number.POSITIVE_INFINITY)
      : sort === "price-desc"
        ? (b.price ?? Number.NEGATIVE_INFINITY) - (a.price ?? Number.NEGATIVE_INFINITY)
        : sort === "area-desc"
          ? (b.constructionM2 || b.landM2 || 0) -
            (a.constructionM2 || a.landM2 || 0)
          : Date.parse(b.createdAt) - Date.parse(a.createdAt),
  );
}

export function getSimilarProperties(
  property: Property,
  properties: Property[],
) {
  return properties
    .filter(
      (p) => p.id !== property.id && p.published,
    )
    .sort((a, b) => {
      const aLocation = a.municipality === property.municipality ? 0 : 1;
      const bLocation = b.municipality === property.municipality ? 0 : 1;
      if (aLocation !== bLocation) return aLocation - bLocation;
      const aType = a.propertyType === property.propertyType ? 0 : 1;
      const bType = b.propertyType === property.propertyType ? 0 : 1;
      if (aType !== bType) return aType - bType;
      return (
        Math.abs((a.price ?? Number.POSITIVE_INFINITY) - (property.price ?? 0)) - Math.abs((b.price ?? Number.POSITIVE_INFINITY) - (property.price ?? 0))
      );
    })
    .slice(0, 3);
}

export function matchProperties(
  properties: Property[],
  criteria: MatchCriteria,
) {
  const { required, preferred } = criteria;
  return properties
    .filter(
      (p) =>
        p.published &&
        (!required.municipality || p.municipality === required.municipality) &&
        (!required.maxPrice || (p.price !== undefined && p.price <= required.maxPrice)) &&
        (!required.propertyType || p.propertyType === required.propertyType) &&
        (!required.minBedrooms || (p.bedrooms !== undefined && p.bedrooms >= required.minBedrooms)) &&
        (!required.minBathrooms || (p.bathrooms !== undefined && p.bathrooms >= required.minBathrooms)),
    )
    .map((property) => {
      const all = [
        ...property.amenities,
        ...property.internalFeatures,
        ...property.externalFeatures,
      ]
        .join(" ")
        .toLowerCase();
      const preferences = [
        ...(preferred.amenities || []).map((label) => ({
          label,
          met: all.includes(label.toLowerCase()),
        })),
        ...(preferred.parkingSpaces
          ? [
              {
                label: `${preferred.parkingSpaces} estacionamientos`,
                met: (property.parkingSpaces || 0) >= preferred.parkingSpaces,
              },
            ]
          : []),
      ];
      return {
        property,
        preferences,
        metCount: preferences.filter((x) => x.met).length,
      };
    })
    .sort((a, b) => b.metCount - a.metCount);
}

export const propertyService = {
  list: () => useCasaVivaStore.getState().properties.map(toPublicProperty),
  getBySlug: (slug: string) => {
    const p = useCasaVivaStore
      .getState()
      .properties.find((x) => x.slug === slug);
    return p ? toPublicProperty(p) : undefined;
  },
  save: (item: Property) => useCasaVivaStore.getState().saveProperty(item),
  remove: (id: string) => useCasaVivaStore.getState().deleteProperty(id),
};
export const developmentService = {
  save: (item: Development) =>
    useCasaVivaStore.getState().saveDevelopment(item),
  remove: (id: string) => useCasaVivaStore.getState().deleteDevelopment(id),
};
export const locationService = {
  save: (item: Location) => useCasaVivaStore.getState().saveLocation(item),
  remove: (id: string) => useCasaVivaStore.getState().deleteLocation(id),
};
export const guideService = {
  save: (item: Guide) => useCasaVivaStore.getState().saveGuide(item),
  remove: (id: string) => useCasaVivaStore.getState().deleteGuide(id),
};
export const inquiryService = {
  create: (item: Inquiry) => useCasaVivaStore.getState().addInquiry(item),
  setStatus: (id: string, status: Inquiry["status"]) =>
    useCasaVivaStore.getState().setInquiryStatus(id, status),
};
export const homeContentService = {
  save: (item: HomeContent) => useCasaVivaStore.getState().setHomeContent(item),
};
export const savedSearchService = {
  save: (item: SavedSearch) => useCasaVivaStore.getState().saveSearch(item),
};

export function useCasaViva() {
  return useCasaVivaStore();
}
