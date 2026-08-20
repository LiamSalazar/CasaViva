export type PropertyType = "house" | "apartment" | "land" | "townhouse";
export type PropertyStatus = "available" | "temporarily_unavailable" | "reserved" | "sold";

export interface Property {
  id: string;
  slug: string;
  title: string;
  shortTitle?: string;
  subtitle?: string;
  operation: "sale";
  propertyType: PropertyType;
  condition: "new" | "used";
  status: PropertyStatus;
  published: boolean;
  featured: boolean;
  price?: number;
  priceMax?: number;
  currency?: "MXN";
  priceLabel?: "fixed" | "from" | "range" | "on-request";
  state?: string;
  municipality?: string;
  neighborhood?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  bedrooms?: number;
  bathrooms?: number;
  halfBathrooms?: number;
  parkingSpaces?: number;
  constructionM2?: number;
  landM2?: number;
  levels?: number;
  description: string;
  shortDescription: string;
  amenities: string[];
  amenityIds?: string[];
  featureValues?: Array<{ definition: string; data_type?: string; value_boolean?: boolean; value_number?: number; value_text?: string; value_choice?: string }>;
  internalFeatures: string[];
  externalFeatures: string[];
  developerId?: string;
  developmentId?: string;
  heroImage: string;
  gallery: string[];
  floorplans?: string[];
  videoUrl?: string;
  tour360Url?: string;
  createdAt: string;
  updatedAt: string;
  internal?: { commissionPercent?: number; notes?: string; reference?: string };
  version?: number;
  offeringId?: string;
  offeringVersion?: number;
  propertyTypeId?: string;
  stateId?: string;
  municipalityId?: string;
  sourceType?: "DEVELOPER" | "PRIVATE";
  developerName?: string;
  developmentName?: string;
  developmentModelId?: string;
  modelName?: string;
  constructionAreaBasis?: "EXACT" | "UP_TO" | "FROM" | "RANGE" | "UNKNOWN";
  landAreaBasis?: "EXACT" | "UP_TO" | "FROM" | "RANGE" | "UNKNOWN";
  heroMediaId?: string;
  archivedAt?: string;
}

export interface Development {
  id: string;
  slug: string;
  name: string;
  developerName: string;
  description: string;
  shortDescription: string;
  state: string;
  municipality: string;
  neighborhood?: string;
  latitude?: number;
  longitude?: number;
  heroImage: string;
  gallery: string[];
  amenities: string[];
  propertyIds: string[];
  published: boolean;
  featured: boolean;
  createdAt: string;
  updatedAt: string;
  developerId?: string;
  stateId?: string;
  municipalityId?: string;
  version?: number;
}

export interface Location {
  id: string;
  slug: string;
  name: string;
  state: string;
  description: string;
  heroImage: string;
  featured: boolean;
  latitude?: number;
  longitude?: number;
  stateId?: string;
}

export interface Guide {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  category: "zonas" | "compra" | "hogar" | "mercado";
  heroImage: string;
  published: boolean;
  featured: boolean;
  createdAt: string;
  viewCount?: number;
}

export interface Inquiry {
  id: string;
  createdAt: string;
  name: string;
  email: string;
  phone?: string;
  message: string;
  source: "property" | "contact" | "visit";
  propertyId?: string;
  subject?: string;
  status: "new" | "viewed" | "attended";
}

export interface HeroSlide {
  id: string;
  propertyId: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  order: number;
  active: boolean;
}
export interface HomeContent {
  heroSlides: HeroSlide[];
  featuredPropertyIds: string[];
  featuredLocationIds: string[];
  featuredDevelopmentIds: string[];
  editorialTitle: string;
  editorialBody: string;
  editorialImage: string;
}

export interface PropertyFilters {
  state?: string;
  municipality?: string;
  propertyType?: PropertyType | "";
  condition?: "new" | "used" | "";
  minPrice?: number;
  maxPrice?: number;
  minBedrooms?: number;
  minBathrooms?: number;
  minParking?: number;
  minConstructionM2?: number;
  minLandM2?: number;
  amenities?: string[];
  developmentId?: string;
  query?: string;
}
export type PropertySort = "recent" | "price-asc" | "price-desc" | "area-desc";

export interface MatchCriteria {
  required: {
    municipality?: string;
    maxPrice?: number;
    propertyType?: PropertyType;
    minBedrooms?: number;
    minBathrooms?: number;
  };
  preferred: { amenities?: string[]; parkingSpaces?: number };
}

export interface SavedSearch {
  id: string;
  createdAt: string;
  filters: PropertyFilters;
  sort: PropertySort;
}
