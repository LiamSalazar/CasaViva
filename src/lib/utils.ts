import type { PropertyType } from "@/types";

export const FEATURES = {
  sellProperty: false,
  propertyValuation: false,
  userAccounts: false,
  aiAssistant: false,
  adminBI: false,
} as const;
export const formatCurrency = (value?: number) =>
  value === undefined ? "—" : new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(value) + " MXN";
export const formatArea = (value?: number) =>
  value ? `${new Intl.NumberFormat("es-MX").format(value)} m²` : "—";
export const formatLocation = (municipality?: string, state?: string) =>
  [municipality, state].filter(Boolean).join(", ");
export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
export const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
export const propertyTypeLabel: Record<PropertyType, string> = {
  house: "Casa",
  apartment: "Departamento",
  land: "Terreno",
  townhouse: "Townhouse",
};
export const uid = (prefix = "cv") =>
  `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
export const copyText = async (text: string) => {
  await navigator.clipboard?.writeText(text);
};
