"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronRight,
  SlidersHorizontal,
  List,
  Map as MapIcon,
  Check,
  Minus,
  Trash2,
} from "lucide-react";
import type {
  MatchCriteria,
  PropertyFilters,
  PropertySort,
  PropertyType,
  Property,
  SearchOptions,
} from "@/types";
import { api, apiFetch, mapProperty } from "@/services/api";
import { trackEvent } from "@/components/analytics-provider";
import {
  matchProperties,
  savedSearchService,
  useCasaViva,
} from "@/services";
import {
  formatArea,
  formatCurrency,
  propertyTypeLabel,
  slugify,
  uid,
} from "@/lib/utils";
import {
  Drawer,
  EmptyState,
  FavoriteButton,
  Footer,
  PublicHeader,
  SearchHeader,
  ShareButton,
  useToast,
} from "@/components/ui";
import {
  DynamicMapView,
  PropertyAmenities,
  PropertyContactCard,
  PropertyDetails,
  PropertyGallery,
  PropertyGridCard,
  PropertyListCard,
  PropertyNote,
  PropertyStickyBar,
  SecondaryGallery,
  DevelopmentCard,
} from "@/components/property";

const deslug = (value: string, options: string[]) =>
  options.find((x) => slugify(x) === value) || value;

export function PropertiesPage() {
  const search = useSearchParams();
  const router = useRouter();
  const { developments, locations } = useCasaViva();
  const { toast } = useToast();
  const [drawer, setDrawer] = useState(false);
  const [map, setMap] = useState(search.get("view") === "map");
  const [selected, setSelected] = useState<string>();
  const [remote, setRemote] = useState<Property[]>([]);
  const [remoteCount, setRemoteCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchOptions, setSearchOptions] = useState<SearchOptions>({ property_types: [], amenities: [], locations: [] });
  useEffect(() => { api.searchOptions().then(setSearchOptions).catch(() => setSearchOptions({ property_types: [], amenities: [], locations: [] })); }, []);
  const municipalities = useMemo(() => locations.map((l) => l.name), [locations]);
  const filters: PropertyFilters = {
    query: search.get("query") || undefined,
    state: search.get("state") || undefined,
    municipality: search.get("municipality")
      ? deslug(search.get("municipality")!, municipalities)
      : undefined,
    propertyType: (search.get("propertyType") as PropertyType) || undefined,
    condition: (search.get("condition") as "new" | "used") || undefined,
    minPrice: Number(search.get("minPrice")) || undefined,
    maxPrice: Number(search.get("maxPrice")) || undefined,
    minBedrooms: Number(search.get("minBedrooms")) || undefined,
    minBathrooms: Number(search.get("minBathrooms")) || undefined,
    minParking: Number(search.get("minParking")) || undefined,
    minConstructionM2: Number(search.get("minConstructionM2")) || undefined,
    minLandM2: Number(search.get("minLandM2")) || undefined,
    developmentId: search.get("developmentId") || undefined,
    amenities: search.get("amenities")?.split(",").filter(Boolean),
  };
  const sort = (search.get("sort") as PropertySort) || "recent";
  const queryString = search.toString();
  useEffect(() => {
    let cancelled = false;
    const source = new URLSearchParams(queryString);
    const params = new URLSearchParams();
    const mappings: Record<string, string> = { query: "query", state: "state", municipality: "municipality", propertyType: "property_type", condition: "condition", minPrice: "price_min", maxPrice: "price_max", minBedrooms: "bedrooms_min", minBathrooms: "bathrooms_min", minParking: "parking_min", minConstructionM2: "construction_area", minLandM2: "land_area", developmentId: "development", amenities: "amenities", page: "page" };
    Object.entries(mappings).forEach(([from, to]) => {
      const value = source.get(from);
      if (value) params.set(to, from === "municipality" ? deslug(value, municipalities) : from === "condition" ? value.toUpperCase() : value);
    });
    params.set("ordering", ({ recent: "newest", "price-asc": "price_asc", "price-desc": "price_desc", "area-desc": "area_desc" } as const)[sort]);
    queueMicrotask(() => { if (!cancelled) setLoading(true); });
    api.publicListingPage(params.toString()).then((page) => { if (!cancelled) { const municipalityName = source.get("municipality") ? deslug(source.get("municipality")!, municipalities) : undefined; const municipalityId = locations.find((item) => item.name === municipalityName)?.id; setRemote(page.results); setRemoteCount(page.count); void trackEvent("search_performed", { municipality_ids: municipalityId ? [municipalityId] : undefined, price_min: Number(source.get("minPrice")) || undefined, price_max: Number(source.get("maxPrice")) || undefined, bedrooms_min: Number(source.get("minBedrooms")) || undefined, property_type_ids: source.get("propertyType") ? [source.get("propertyType")] : undefined, result_count: page.count }); } }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [queryString, sort, municipalities, locations]);
  const results = remote;
  const setParam = (key: string, value?: string) => {
    const q = new URLSearchParams(search.toString());
    if (value) q.set(key, value);
    else q.delete(key);
    router.push(`/propiedades?${q.toString()}`);
  };
  const typeCounts = Object.fromEntries(searchOptions.property_types.map((type) => [type.code, results.filter((property) => property.propertyType === type.code).length]));
  const counts = { new: results.filter((p) => p.condition === "new").length, used: results.filter((p) => p.condition === "used").length };
  return (
    <>
      <SearchHeader />
      <div className="filter-bar">
        <button className="filter-pill active" onClick={() => setDrawer(true)}>
          <SlidersHorizontal size={14} /> Todos los filtros
        </button>
        <button className="filter-pill">En venta</button>
        <button
          className={`filter-pill ${filters.propertyType ? "active" : ""}`}
          onClick={() => setDrawer(true)}
        >
          Tipo
        </button>
        <button
          className={`filter-pill ${filters.minBedrooms || filters.minBathrooms ? "active" : ""}`}
          onClick={() => setDrawer(true)}
        >
          Características
        </button>
        <button
          className={`filter-pill ${filters.maxPrice || filters.minPrice ? "active" : ""}`}
          onClick={() => setDrawer(true)}
        >
          Precio
        </button>
        <button
          className={`filter-pill ${filters.minConstructionM2 || filters.minLandM2 ? "active" : ""}`}
          onClick={() => setDrawer(true)}
        >
          Superficie
        </button>
        <button className="button" onClick={() => setDrawer(true)}>
          Buscar
        </button>
      </div>
      <div className="mobile-search-actions">
        <button onClick={() => setDrawer(true)}>Filtros</button>
        <button onClick={() => setDrawer(true)}>Ordenar</button>
        <button onClick={() => setMap((x) => !x)}>
          {map ? "Lista" : "Mapa"}
        </button>
      </div>
      <main className="container">
        <div className="results-head">
          <div className="breadcrumb">
            <Link href="/">CasaViva</Link>
            <span>/</span>
            <span>{filters.state || "México"}</span>
            {filters.municipality && (
              <>
                <span>/</span>
                <span>{filters.municipality}</span>
              </>
            )}
          </div>
          <h1>
            {remoteCount}{" "}
            {remoteCount === 1 ? "propiedad" : "propiedades"}
            {filters.municipality
              ? ` en ${filters.municipality}`
              : " para descubrir"}
          </h1>
          <div className="category-counts">
            {searchOptions.property_types.map((type) => <button key={type.id} className="text-link" onClick={() => setParam("propertyType", type.code)}>{type.name} {typeCounts[type.code] || 0}</button>)}
            <button
              className="text-link"
              onClick={() => setParam("condition", "new")}
            >
              Casas nuevas {counts.new}
            </button>
            <button
              className="text-link"
              onClick={() => setParam("condition", "used")}
            >
              Casas usadas {counts.used}
            </button>
          </div>
        </div>
        <div className="results-toolbar">
          <span>{remoteCount} resultados</span>
          <button
            className="button secondary"
            onClick={() => {
              savedSearchService.save({
                id: uid("search"),
                createdAt: new Date().toISOString(),
                filters,
                sort,
              });
              toast("Búsqueda guardada");
            }}
          >
            Guardar búsqueda
          </button>
          <div className="segmented">
            <button
              className={!map ? "active" : ""}
              onClick={() => setMap(false)}
            >
              <List size={14} /> Lista
            </button>
            <button
              className={map ? "active" : ""}
              onClick={() => setMap(true)}
            >
              <MapIcon size={14} /> Mapa
            </button>
          </div>
          <select
            className="sort-select"
            value={sort}
            onChange={(e) => setParam("sort", e.target.value)}
            aria-label="Ordenar"
          >
            <option value="recent">Más recientes</option>
            <option value="price-asc">Precio: menor a mayor</option>
            <option value="price-desc">Precio: mayor a menor</option>
            <option value="area-desc">Mayor superficie</option>
          </select>
        </div>
        {loading ? <div className="empty-state"><p>Buscando propiedades…</p></div> : results.length ? (
          <div className={`results-layout ${map ? "map-open" : ""}`}>
            <div className="property-list">
              {results.map((p) => (
                <PropertyListCard
                  key={p.id}
                  property={p}
                  development={developments.find(
                    (d) => d.id === p.developmentId,
                  )}
                  onHover={setSelected}
                />
              ))}
            </div>
            {map && (
              <DynamicMapView
                properties={results}
                selectedId={selected}
                onSelect={setSelected}
              />
            )}
          </div>
        ) : (
          <EmptyState
            title="No encontramos propiedades con esos filtros"
            body="Prueba ampliar el precio o quitar alguna característica."
            href="/propiedades"
            action="Limpiar filtros"
          />
        )}
        {remoteCount > 24 && <div className="pagination"><button disabled={Number(search.get("page") || 1) <= 1} onClick={() => setParam("page", String(Math.max(1, Number(search.get("page") || 1) - 1)))}>Anterior</button><span>Página {Number(search.get("page") || 1)}</span><button disabled={Number(search.get("page") || 1) * 24 >= remoteCount} onClick={() => setParam("page", String(Number(search.get("page") || 1) + 1))}>Siguiente</button></div>}
      </main>
      <SearchFilters
        open={drawer}
        onClose={() => setDrawer(false)}
        initial={filters}
        sort={sort}
        locations={locations.map((l) => ({ name: l.name, state: l.state }))}
        developments={developments.map((d) => ({ id: d.id, name: d.name }))}
        typeOptions={searchOptions.property_types.map((type) => [type.name, type.code])}
        amenities={searchOptions.amenities.map((amenity) => amenity.name)}
      />
      <Footer />
    </>
  );
}

function SearchFilters({
  open,
  onClose,
  initial,
  sort,
  locations,
  developments,
  typeOptions,
  amenities,
}: {
  open: boolean;
  onClose: () => void;
  initial: PropertyFilters;
  sort: PropertySort;
  locations: { name: string; state: string }[];
  developments: { id: string; name: string }[];
  typeOptions: [string, PropertyType][];
  amenities: string[];
}) {
  const router = useRouter();
  const [draft, setDraft] = useState<PropertyFilters>(initial);
  const [sortDraft, setSort] = useState(sort);
  const update = (key: keyof PropertyFilters, value: unknown) =>
    setDraft((d) => ({ ...d, [key]: value || undefined }));
  const apply = () => {
    const q = new URLSearchParams();
    Object.entries(draft).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && (Array.isArray(v) ? v.length : true))
        q.set(
          k,
          k === "municipality"
            ? slugify(String(v))
            : Array.isArray(v)
              ? v.join(",")
              : String(v),
        );
    });
    q.set("sort", sortDraft);
    router.push(`/propiedades?${q}`);
    onClose();
  };
  return (
    <Drawer open={open} onClose={onClose} title="Filtros">
      <div className="filter-form">
        <div className="form-grid">
          <label className="field">
            <span>Estado</span>
            <select
              value={draft.state || ""}
              onChange={(e) => update("state", e.target.value)}
            >
              <option value="">Todos</option>
              {[...new Set(locations.map((l) => l.state))].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Municipio</span>
            <select
              value={draft.municipality || ""}
              onChange={(e) => update("municipality", e.target.value)}
            >
              <option value="">Todos</option>
              {locations
                .filter((l) => !draft.state || l.state === draft.state)
                .map((l) => (
                  <option key={l.name}>{l.name}</option>
                ))}
            </select>
          </label>
          <label className="field">
            <span>Tipo</span>
            <select
              value={draft.propertyType || ""}
              onChange={(e) => update("propertyType", e.target.value)}
            >
              <option value="">Todos</option>
              {typeOptions.map(([l, v]) => (
                <option value={v} key={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Condición</span>
            <select
              value={draft.condition || ""}
              onChange={(e) => update("condition", e.target.value)}
            >
              <option value="">Nueva o usada</option>
              <option value="new">Nueva</option>
              <option value="used">Usada</option>
            </select>
          </label>
          <Num
            label="Precio mínimo"
            value={draft.minPrice}
            onChange={(v) => update("minPrice", v)}
          />
          <Num
            label="Precio máximo"
            value={draft.maxPrice}
            onChange={(v) => update("maxPrice", v)}
          />
          <Num
            label="Recámaras mínimas"
            value={draft.minBedrooms}
            onChange={(v) => update("minBedrooms", v)}
          />
          <Num
            label="Baños mínimos"
            value={draft.minBathrooms}
            onChange={(v) => update("minBathrooms", v)}
          />
          <Num
            label="Estacionamientos"
            value={draft.minParking}
            onChange={(v) => update("minParking", v)}
          />
          <Num
            label="Construcción mínima m²"
            value={draft.minConstructionM2}
            onChange={(v) => update("minConstructionM2", v)}
          />
          <Num
            label="Terreno mínimo m²"
            value={draft.minLandM2}
            onChange={(v) => update("minLandM2", v)}
          />
          <label className="field">
            <span>Desarrollo</span>
            <select
              value={draft.developmentId || ""}
              onChange={(e) => update("developmentId", e.target.value)}
            >
              <option value="">Todos</option>
              {developments.map((d) => (
                <option value={d.id} key={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Ordenar</span>
            <select
              value={sortDraft}
              onChange={(e) => setSort(e.target.value as PropertySort)}
            >
              <option value="recent">Más recientes</option>
              <option value="price-asc">Precio: menor a mayor</option>
              <option value="price-desc">Precio: mayor a menor</option>
              <option value="area-desc">Mayor superficie</option>
            </select>
          </label>
        </div>
        <div>
          <strong>Amenidades</strong>
          <div className="filter-checks">
            {amenities.map((a) => (
              <label className="check-chip" key={a}>
                <input
                  type="checkbox"
                  checked={draft.amenities?.includes(a) || false}
                  onChange={(e) =>
                    update(
                      "amenities",
                      e.target.checked
                        ? [...(draft.amenities || []), a]
                        : (draft.amenities || []).filter((x) => x !== a),
                    )
                  }
                />
                <span>{a}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="form-actions">
          <button className="button ghost" onClick={() => setDraft({})}>
            Limpiar
          </button>
          <button className="button" onClick={apply}>
            Aplicar
          </button>
        </div>
      </div>
    </Drawer>
  );
}
function Num({
  label,
  value,
  onChange,
}: {
  label: string;
  value?: number;
  onChange: (v?: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min="0"
        value={value || ""}
        onChange={(e) => onChange(Number(e.target.value) || undefined)}
      />
    </label>
  );
}

export function PropertyDetailPage({
  slug,
  previewId,
}: {
  slug?: string;
  previewId?: string;
}) {
  const { properties, developments, adminAuthenticated } = useCasaViva();
  const [detail, setDetail] = useState<Property>();
  useEffect(() => {
    if (previewId && adminAuthenticated) apiFetch<Record<string, any>>(`/api/v1/admin/listings/${previewId}/`).then((x) => setDetail(mapProperty(x))).catch(() => setDetail(undefined));
    else if (slug) apiFetch<Record<string, any>>(`/api/v1/public/listings/${slug}/`).then((x) => { const mapped = mapProperty(x); setDetail(mapped); void trackEvent("listing_viewed", {}, { listing: mapped.id, offering: mapped.offeringId }); }).catch(() => setDetail(undefined));
  }, [slug, previewId, adminAuthenticated]);
  const property = previewId && !adminAuthenticated ? undefined : detail || (previewId ? properties.find((p) => p.id === previewId) : properties.find((p) => p.slug === slug && p.published));
  const [similar, setSimilar] = useState<Property[]>([]);
  useEffect(() => {
    if (!property?.slug || previewId) return;
    api.similarListings(property.slug).then(setSimilar).catch(() => setSimilar([]));
  }, [property?.slug, previewId]);
  const [expanded, setExpanded] = useState(false);
  const anchor = useRef<HTMLDivElement>(null);
  if (!property)
    return (
      <>
        <PublicHeader />
        <EmptyState
          title="Esta propiedad no está disponible"
          body="Puede haberse despublicado o la dirección no es correcta."
          href="/propiedades"
          action="Explorar propiedades"
        />
        <Footer />
      </>
    );
  const development = developments.find((d) => d.id === property.developmentId);
  return (
    <>
      <PublicHeader />
      <main className="property-page">
        {previewId && (
          <div
            style={{
              background: "#f6edd8",
              padding: "10px 20px",
              textAlign: "center",
            }}
          >
            Vista previa de administración — esta propiedad puede no estar
            publicada.
          </div>
        )}
        <div className="detail-top">
          <div className="breadcrumb">
            <Link href="/">CasaViva</Link>
            <span>/</span>
            <span>{property.state}</span>
            <span>/</span>
            <span>{property.municipality}</span>
            <span>/</span>
            <span>Propiedad</span>
          </div>
        </div>
        <PropertyGallery property={property} />
        <div className="container">
          <div className="detail-title-wrap" ref={anchor}>
            <div>
              <span className="eyebrow">
                {property.propertyTypeName || propertyTypeLabel[property.propertyType] || property.propertyType} en venta
              </span>
              <h1>
                {property.title} en {property.municipality}, {property.state}
              </h1>
              <div className="detail-price">
                {property.priceLabel === "from" && "Desde "}
                {formatCurrency(property.price)}
              </div>
              <div className="detail-facts">
                {property.constructionM2 && (
                  <span>
                    <MaxIcon />
                    {formatArea(property.constructionM2)}
                  </span>
                )}
                {(property.bedrooms || 0) > 0 && (
                  <span>{property.bedrooms} recámaras</span>
                )}
                {(property.bathrooms || 0) > 0 && (
                  <span>{property.bathrooms} baños</span>
                )}
                {property.parkingSpaces ? (
                  <span>
                    {property.parkingSpaces} estacionamiento
                    {property.parkingSpaces > 1 ? "s" : ""}
                  </span>
                ) : null}
              </div>
            </div>
            <div className="detail-actions">
              <ShareButton label />
              <FavoriteButton id={property.id} label />
            </div>
          </div>
          <PropertyStickyBar property={property} anchor={anchor} />
          <div className="detail-layout">
            <div className="detail-content">
              <section>
                <h2>Descripción</h2>
                <p
                  className={`editorial-body description-copy ${expanded ? "" : "collapsed"}`}
                >
                  {property.description}
                </p>
                <button
                  className="read-more"
                  onClick={() => setExpanded((x) => !x)}
                >
                  {expanded ? "Mostrar menos" : "Leer todo"}
                </button>
              </section>
              <section>
                <h2>Nota personal</h2>
                <PropertyNote id={property.id} />
              </section>
              <section>
                <h2>Detalles</h2>
                <PropertyDetails property={property} />
              </section>
              <section>
                <h2>Características</h2>
                <PropertyAmenities property={property} />
              </section>
              <section>
                <h2>Galería</h2>
                <SecondaryGallery property={property} />
              </section>
              {property.floorplans?.length ? (
                <section>
                  <h2>Planos</h2>
                  <button className="floorplan">
                    <Image
                      src={property.floorplans[0]}
                      alt={`Plano de ${property.title}`}
                      width={1400}
                      height={1000}
                    />
                  </button>
                </section>
              ) : null}
              <section>
                <h2>Ubicación</h2>
                <p>
                  {property.address ||
                    `${property.neighborhood || "Zona residencial"}, ${property.municipality}`}
                </p>
                <DynamicMapView properties={[property]} />
              </section>
              {development && (
                <section>
                  <h2>Conoce el desarrollo</h2>
                  <DevelopmentCard
                    development={development}
                    properties={properties}
                  />
                  <Link
                    className="button"
                    href={`/desarrollos/${development.slug}`}
                  >
                    Ver desarrollo
                  </Link>
                </section>
              )}
            </div>
            <div id="contacto">
              <PropertyContactCard property={property} />
            </div>
          </div>
          {similar.length > 0 && (
            <section className="section">
              <div className="inline-heading">
                <h2>También puedes explorar</h2>
                <Link className="text-link" href="/propiedades">
                  Ver todas <ChevronRight />
                </Link>
              </div>
              <div className="property-grid">
                {similar.map((p) => (
                  <PropertyGridCard property={p} key={p.id} />
                ))}
              </div>
            </section>
          )}
        </div>
      </main>
      <div className="mobile-contact-bar">
        <a className="button" href="#contacto">
          Solicitar información
        </a>
        <FavoriteButton id={property.id} />
      </div>
      <Footer />
    </>
  );
}
function MaxIcon() {
  return <span aria-hidden="true">↔</span>;
}

export function FavoritesPage() {
  const { favorites, clearFavorites } = useCasaViva();
  const [list, setList] = useState<Property[]>([]);
  useEffect(() => { api.favoriteListings(favorites).then(setList).catch(() => setList([])); }, [favorites]);
  const { toast } = useToast();
  return (
    <>
      <PublicHeader />
      <main className="container section">
        <div className="inline-heading">
          <div>
            <span className="eyebrow">Tu selección</span>
            <h1 style={{ fontSize: "clamp(3rem,6vw,6rem)" }}>Favoritos</h1>
          </div>
          {list.length > 0 && (
            <button
              className="button ghost"
              onClick={() => {
                clearFavorites();
                toast("Favoritos eliminados");
              }}
            >
              <Trash2 size={16} /> Limpiar favoritos
            </button>
          )}
        </div>
        {list.length ? (
          <div className="property-grid">
            {list.map((p) => (
              <PropertyGridCard key={p.id} property={p} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Todavía no has guardado propiedades."
            body="Usa el corazón de cualquier propiedad para conservarla aquí."
            href="/propiedades"
            action="Explorar propiedades"
          />
        )}
      </main>
      <Footer />
    </>
  );
}

export function FinderPage() {
  const { locations } = useCasaViva();
  const [step, setStep] = useState(0);
  const [inventory, setInventory] = useState<Property[]>([]);
  const [searchOptions, setSearchOptions] = useState<SearchOptions>({ property_types: [], amenities: [], locations: [] });
  const [criteria, setCriteria] = useState<MatchCriteria>({
    required: {},
    preferred: { amenities: [] },
  });
  useEffect(() => { api.searchOptions().then(setSearchOptions).catch(() => setSearchOptions({ property_types: [], amenities: [], locations: [] })); }, []);
  useEffect(() => {
    if (step < 4) return;
    const params = new URLSearchParams();
    if (criteria.required.municipality) params.set("municipality", criteria.required.municipality);
    if (criteria.required.maxPrice) params.set("price_max", String(criteria.required.maxPrice));
    if (criteria.required.propertyType) params.set("property_type", criteria.required.propertyType);
    if (criteria.required.minBedrooms) params.set("bedrooms_min", String(criteria.required.minBedrooms));
    if (criteria.required.minBathrooms) params.set("bathrooms_min", String(criteria.required.minBathrooms));
    api.publicListingsAll(params.toString()).then(setInventory).catch(() => setInventory([]));
  }, [step, criteria.required]);
  const results = step >= 4 ? matchProperties(inventory, criteria) : [];
  const typeOptions: [string, PropertyType][] = searchOptions.property_types.map((type) => [type.name, type.code]);
  const amenities = searchOptions.amenities.map((amenity) => amenity.name);
  const toggleAmenity = (a: string) =>
    setCriteria((c) => ({
      ...c,
      preferred: {
        ...c.preferred,
        amenities: c.preferred.amenities?.includes(a)
          ? c.preferred.amenities.filter((x) => x !== a)
          : [...(c.preferred.amenities || []), a],
      },
    }));
  return (
    <>
      <PublicHeader />
      <main className="narrow section">
        <span className="eyebrow">Recomendador por criterios</span>
        <h1 style={{ fontSize: "clamp(3rem,6vw,6rem)" }}>
          Encuentra propiedades según lo que buscas
        </h1>
        <p className="editorial-body">
          Primero filtramos lo que necesitas. Después ordenamos por la cantidad
          de preferencias explícitas cumplidas, sin porcentajes ni puntuaciones
          ocultas.
        </p>
        <div className="wizard-progress">
          {[0, 1, 2, 3, 4].map((i) => (
            <span className={i <= step ? "active" : ""} key={i} />
          ))}
        </div>
        {step === 0 && (
          <Wizard title="¿Dónde quieres vivir?">
            <div className="choice-grid">
              {locations.map((l) => (
                <button
                  className={`choice ${criteria.required.municipality === l.name ? "active" : ""}`}
                  onClick={() =>
                    setCriteria((c) => ({
                      ...c,
                      required: { ...c.required, municipality: l.name },
                    }))
                  }
                  key={l.id}
                >
                  {l.name}
                </button>
              ))}
            </div>
          </Wizard>
        )}
        {step === 1 && (
          <Wizard title="¿Cuál es tu presupuesto máximo?">
            <div className="choice-grid">
              {[1000000, 1300000, 1600000, 2200000, 3500000].map((v) => (
                <button
                  className={`choice ${criteria.required.maxPrice === v ? "active" : ""}`}
                  onClick={() =>
                    setCriteria((c) => ({
                      ...c,
                      required: { ...c.required, maxPrice: v },
                    }))
                  }
                  key={v}
                >
                  {formatCurrency(v)}
                </button>
              ))}
            </div>
          </Wizard>
        )}
        {step === 2 && (
          <Wizard title="¿Qué tipo y tamaño necesitas?">
            <div className="form-grid">
              <label className="field">
                <span>Tipo</span>
                <select
                  value={criteria.required.propertyType || ""}
                  onChange={(e) =>
                    setCriteria((c) => ({
                      ...c,
                      required: {
                        ...c.required,
                        propertyType: e.target.value as PropertyType,
                      },
                    }))
                  }
                >
                  <option value="">Cualquier tipo</option>
                  {typeOptions.map(([l, v]) => (
                    <option value={v} key={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <Num
                label="Recámaras mínimas"
                value={criteria.required.minBedrooms}
                onChange={(v) =>
                  setCriteria((c) => ({
                    ...c,
                    required: { ...c.required, minBedrooms: v },
                  }))
                }
              />
              <Num
                label="Baños mínimos"
                value={criteria.required.minBathrooms}
                onChange={(v) =>
                  setCriteria((c) => ({
                    ...c,
                    required: { ...c.required, minBathrooms: v },
                  }))
                }
              />
            </div>
          </Wizard>
        )}
        {step === 3 && (
          <Wizard title="¿Qué te gustaría encontrar?">
            <p>Estas son preferencias, no requisitos.</p>
            <div className="choice-grid">
              {amenities.map((a) => (
                <button
                  className={`choice ${criteria.preferred.amenities?.includes(a) ? "active" : ""}`}
                  onClick={() => toggleAmenity(a)}
                  key={a}
                >
                  {a}
                </button>
              ))}
            </div>
            <div style={{ marginTop: 20 }}>
              <Num
                label="Estacionamientos deseados"
                value={criteria.preferred.parkingSpaces}
                onChange={(v) =>
                  setCriteria((c) => ({
                    ...c,
                    preferred: { ...c.preferred, parkingSpaces: v },
                  }))
                }
              />
            </div>
          </Wizard>
        )}
        {step >= 4 && (
          <div>
            <h2>{results.length} propiedades cumplen todos tus requisitos</h2>
            {results.length ? (
              <div className="property-grid">
                {results.map(({ property, preferences }) => (
                  <div key={property.id}>
                    <PropertyGridCard property={property} />
                    <div className="match-preferences">
                      <strong>Preferencias:</strong>
                      {preferences.map((p) => (
                        <span key={p.label}>
                          {p.met ? <Check size={13} /> : <Minus size={13} />}{" "}
                          {p.label}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No hay coincidencias exactas"
                body="Vuelve un paso y amplía alguno de tus requisitos."
              />
            )}
          </div>
        )}
        <div className="form-actions" style={{ marginTop: 40 }}>
          {step > 0 && (
            <button
              className="button secondary"
              onClick={() => setStep((x) => x - 1)}
            >
              Anterior
            </button>
          )}
          {step < 4 && (
            <button className="button" onClick={() => setStep((x) => x + 1)}>
              {step === 3 ? "Ver propiedades" : "Continuar"}
            </button>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
function Wizard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="wizard-step">
      <span className="eyebrow">Necesito / Me gustaría</span>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
