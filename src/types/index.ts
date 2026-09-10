export type PropertyTypeCode = string;
export type PropertyType = PropertyTypeCode;
export type PropertyStatus = "available" | "temporarily_unavailable" | "reserved" | "sold";

export interface Property {
  id: string;
  slug: string;
  title: string;
  shortTitle?: string;
  subtitle?: string;
  operation: "sale";
  propertyType: PropertyType;
  propertyTypeName?: string;
  condition?: "new" | "used";
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
  bedroomsMax?: number;
  bathrooms?: number;
  fullBathrooms?: number;
  halfBathrooms?: number;
  parkingSpaces?: number;
  parkingMax?: number;
  constructionM2?: number;
  landM2?: number;
  levels?: number;
  levelsMax?: number;
  constructionM2Max?: number;
  landM2Max?: number;
  gardenM2?: number;
  gardenM2Max?: number;
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
  localityId?: string;
  neighborhoodId?: string;
  postalCode?: string;
  sourceType?: "DEVELOPER" | "PRIVATE";
  promotionAuthorized?: boolean;
  informationVerifiedAt?: string;
  publicProviderLabel?: string;
  internalSourceReference?: string;
  developerName?: string;
  developmentName?: string;
  developmentModelId?: string;
  modelName?: string;
  providerLabel?: string;
  promotionRole?: string;
  promotion?: { text: string; validFrom?: string; validUntil?: string; conditions?: string };
  constructionAreaBasis?: "EXACT" | "UP_TO" | "FROM" | "RANGE" | "UNKNOWN";
  landAreaBasis?: "EXACT" | "UP_TO" | "FROM" | "RANGE" | "UNKNOWN";
  gardenAreaBasis?: "EXACT" | "UP_TO" | "FROM" | "RANGE" | "UNKNOWN";
  amenitySlugs?: string[];
  heroMediaId?: string;
  mediaAssets?: Array<{ mediaId: string; role: "HERO" | "GALLERY" | "FLOORPLAN" | "DOCUMENT"; sortOrder: number; url?: string }>;
  archivedAt?: string;
}

export interface PropertyTypeOption { id: string; code: string; name: string }
export interface SearchOptions {
  property_types: PropertyTypeOption[];
  amenities: Array<{ id: string; slug: string; name: string; category: string }>;
  locations: Array<{ id: string; name: string; state_id: string; state: string }>;
}

export interface ApiPage<T> { count: number; next: string | null; previous: string | null; results: T[] }
export interface SiteSettings {
  id?: string;
  key?: string;
  contact_email: string;
  brand_name?: string;
  responsible_name?: string;
  responsible_address?: string;
  privacy_email?: string;
  complaints_email?: string;
  contact_phone?: string;
  commercial_role_display?: string;
  facebook_url?: string | null;
  instagram_url?: string | null;
  tiktok_url?: string | null;
  version?: number;
}
export interface SearchFacets {
  property_types: Array<{ offering__property_type__code: string; offering__property_type__name: string; count: number }>;
  conditions: Array<{ offering__condition: "NEW" | "USED"; count: number }>;
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
  localityId?: string;
  neighborhoodId?: string;
  address?: string;
  postalCode?: string;
  amenityIds?: string[];
  mediaAssets?: Array<{ mediaId: string; role: "HERO" | "GALLERY" | "FLOORPLAN" | "DOCUMENT"; sortOrder: number; url?: string }>;
  heroMediaId?: string;
  version?: number;
  publishedListingCount?: number;
  availableListingCount?: number;
  currentMinPrice?: number;
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
  contentId?: string;
  contentVersion?: number;
  heroMediaId?: string;
  hasContent?: boolean;
  archivedAt?: string;
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
  heroMediaId?: string;
  version?: number;
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
  listingSlug?: string;
  sessionId?: string;
  visitorId?: string;
  subject?: string;
  privacyConsent: boolean;
  transferConsent?: boolean;
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
  id?: string;
  version?: number;
  heroEyebrow: string;
  heroTitle: string;
  heroSlides: HeroSlide[];
  featuredPropertyIds: string[];
  featuredLocationIds: string[];
  featuredDevelopmentIds: string[];
  editorialTitle: string;
  editorialBody: string;
  editorialImage: string;
  editorialMediaId?: string;
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
