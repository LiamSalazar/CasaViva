"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminLayout, AdminTable } from "@/components/admin";
import { apiFetch, fetchAllPages } from "@/services/api";
import { formatCurrency, formatDate, slugify } from "@/lib/utils";

type BiData = {
  current: Record<string, number>; previous: Record<string, number>;
  traffic: Array<{ date: string; sessions: number; visitors: number }>;
  funnel: Array<{ label: string; value: number }>;
  funnel_description?: string;
  lead_cohort?: { leads: number; with_visit: number; with_closed_sale: number };
  inventory: Record<string, number>;
};

const labels: Record<string, string> = { visitors: "Visitantes", sessions: "Sesiones", listing_views: "Propiedades vistas", inquiries: "Consultas", visits: "Visitas", sales: "Ventas" };

export function AdminBiPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<BiData>();
  const [searches, setSearches] = useState<any>(); const [marketing, setMarketing] = useState<any[]>([]); const [sales, setSales] = useState<any>(); const [decisions, setDecisions] = useState<any>();
  const [error, setError] = useState("");
  useEffect(() => { apiFetch<BiData>(`/api/v1/admin/bi/overview/?days=${days}`).then(setData).catch((e) => setError(e.message)); }, [days]);
  useEffect(() => { Promise.all([apiFetch<any>(`/api/v1/admin/bi/searches/?days=${days}`), apiFetch<any[]>(`/api/v1/admin/bi/marketing/?days=${days}`), apiFetch<any>(`/api/v1/admin/bi/sales/?days=${days}`), apiFetch<any>(`/api/v1/admin/bi/decisions/?days=${days}`)]).then(([a,b,c,d]) => { setSearches(a); setMarketing(b); setSales(c); setDecisions(d); }).catch((e) => setError(e.message)); }, [days]);
  const maxTraffic = Math.max(1, ...(data?.traffic.map((x) => x.sessions) || [1]));
  return <AdminLayout title="Business Intelligence">
    <div className="admin-title"><div><span className="eyebrow">Resultados</span><h2>Resumen ejecutivo</h2></div><label className="period-select">Periodo<select value={days} onChange={(e) => setDays(Number(e.target.value))}><option value="7">7 días</option><option value="30">30 días</option><option value="90">90 días</option></select></label></div>
    {error && <p className="form-error">{error}</p>}
    <div className="metric-grid">{data && Object.entries(labels).map(([key, label]) => <div className="metric-card" key={key}><span>{label}</span><strong>{data.current[key] || 0}</strong><small>Periodo anterior: {data.previous[key] || 0}</small></div>)}</div>
    <div className="admin-panels">
      <section className="admin-panel"><h3>Tráfico en el tiempo</h3><div className="bi-bars" aria-label="Sesiones por día">{data?.traffic.map((x) => <div key={x.date} title={`${x.date}: ${x.sessions} sesiones`}><span style={{ height: `${Math.max(3, x.sessions / maxTraffic * 100)}%` }} /><small>{new Date(x.date).getDate()}</small></div>)}</div></section>
      <section className="admin-panel"><h3>Actividad por etapa</h3><p className="muted">{data?.funnel_description}</p><div className="bi-funnel">{data?.funnel.map((x) => <div key={x.label}><span>{x.label}</span><strong>{x.value}</strong></div>)}</div>{data?.lead_cohort && <><h3>Cohorte de clientes del periodo</h3><div className="inventory-line"><span>Clientes creados <strong>{data.lead_cohort.leads}</strong></span><span>Con visita <strong>{data.lead_cohort.with_visit}</strong></span><span>Con venta cerrada <strong>{data.lead_cohort.with_closed_sale}</strong></span></div></>}</section>
    </div>
    <section className="admin-panel"><h3>Inventario</h3><div className="inventory-line"><span>Registradas <strong>{data?.inventory.registered || 0}</strong></span><span>Publicadas <strong>{data?.inventory.published || 0}</strong></span><span>No publicadas <strong>{data?.inventory.unpublished || 0}</strong></span><span>Archivadas <strong>{data?.inventory.archived || 0}</strong></span></div></section>
    <ListingPerformance days={days} />
    <div className="admin-panels"><section className="admin-panel"><h3>Búsquedas por ubicación</h3><p className="muted">Búsquedas sin resultados: {searches?.no_results || 0}</p><div className="bi-funnel">{searches?.municipalities?.map((x: any) => <div key={x.label}><span>{x.label}</span><strong>{x.count}</strong></div>)}</div></section><section className="admin-panel"><h3>Filtros más usados</h3><div className="bi-funnel">{searches?.filters?.map((x: any) => <div key={x.label}><span>{x.label}</span><strong>{x.count}</strong></div>)}</div></section></div>
    <section className="admin-panel bi-table"><h3>Fuentes de tráfico y campañas</h3><AdminTable heads={["Fuente", "Medio", "Campaña", "Sesiones", "Consultas", "Visitas", "Ventas", "Gasto", "Costo por consulta"]}>{marketing.map((x) => <tr key={[x.utm_source,x.utm_medium,x.utm_campaign,x.utm_content].join("|")}><td>{x.utm_source || "Directo"}</td><td>{x.utm_medium || "—"}</td><td>{x.utm_campaign || "—"}</td><td>{x.sessions}</td><td>{x.inquiries}</td><td>{x.visits}</td><td>{x.sales}</td><td>{x.spend == null ? "—" : formatCurrency(Number(x.spend))}</td><td>{x.cost_per_inquiry == null ? "—" : formatCurrency(Number(x.cost_per_inquiry))}</td></tr>)}</AdminTable></section>
    <section className="admin-panel"><h3>Ventas por periodo</h3><div className="inventory-line"><span>Ventas <strong>{sales?.totals?.sales || 0}</strong></span><span>Valor <strong>{sales?.totals?.value == null ? "—" : formatCurrency(Number(sales.totals.value))}</strong></span><span>Comisiones <strong>{sales?.totals?.commissions == null ? "—" : formatCurrency(Number(sales.totals.commissions))}</strong></span><span>Tiempo medio de cierre <strong>{sales?.totals?.average_close_days == null ? "—" : `${sales.totals.average_close_days} días`}</strong></span></div></section>
    <section className="admin-panel"><h3>Información para decisiones</h3><div className="inventory-line"><span>Leads pendientes de atención <strong>{decisions?.pending_leads || 0}</strong></span><span>Propiedades no publicadas modificadas <strong>{decisions?.recent_unpublished || 0}</strong></span></div><AdminTable heads={["Propiedad", "Visualizaciones", "Consultas"]}>{(decisions?.high_views_low_inquiries || []).map((x: any) => <tr key={x.id}><td>{x.title}</td><td>{x.views}</td><td>{x.inquiries_count}</td></tr>)}</AdminTable></section>
  </AdminLayout>;
}

function ListingPerformance({ days }: { days: number }) {
  const [rows, setRows] = useState<Array<any>>([]);
  useEffect(() => { apiFetch<Array<any>>(`/api/v1/admin/bi/listings/?days=${days}`).then(setRows).catch(() => setRows([])); }, [days]);
  return <section className="admin-panel bi-table"><h3>Resultados por propiedad</h3><AdminTable heads={["Propiedad", "Visualizaciones", "Favoritos", "Consultas", "Visitas", "Ventas", "Vista → consulta", "Consulta → visita", "Visita → venta"]}>{rows.map((x) => <tr key={x.id}><td>{x.title}</td><td>{x.views}</td><td>{x.favorites}</td><td>{x.inquiries_count}</td><td>{x.visits_count}</td><td>{x.sales_count}</td><td>{x.view_to_inquiry_rate == null ? "—" : `${Math.round(x.view_to_inquiry_rate)}%`}</td><td>{x.inquiry_to_visit_rate == null ? "—" : `${Math.round(x.inquiry_to_visit_rate)}%`}</td><td>{x.visit_to_sale_rate == null ? "—" : `${Math.round(x.visit_to_sale_rate)}%`}</td></tr>)}</AdminTable></section>;
}

const resources: Record<string, { title: string; endpoint: string; exportable?: boolean; heads: string[]; row: (x: any) => React.ReactNode[] }> = {
  clientes: { title: "Clientes", endpoint: "leads", exportable: true, heads: ["Nombre", "Correo", "Teléfono", "Etapa", "Actualizado"], row: (x) => [x.name, x.email || "—", x.phone_raw || "—", x.status_label, formatDate(x.updated_at)] },
  consultas: { title: "Consultas", endpoint: "inquiries", exportable: true, heads: ["Cliente", "Propiedad", "Canal", "Estado", "Recibida"], row: (x) => [x.lead_name, x.listing_title || "Consulta general", x.channel, x.status_label, formatDate(x.created_at)] },
  visitas: { title: "Visitas", endpoint: "visits", heads: ["Cliente", "Programada", "Estado", "Responsable"], row: (x) => [x.lead_name, formatDate(x.scheduled_at), x.status, x.assigned_to || "—"] },
  ventas: { title: "Ventas", endpoint: "sales", exportable: true, heads: ["Cliente", "Precio de venta", "Comisión", "Cierre"], row: (x) => [x.lead_name, formatCurrency(Number(x.sale_price)), x.commission_amount ? formatCurrency(Number(x.commission_amount)) : "—", formatDate(x.closed_at)] },
};

export function AdminResourcePage({ resource }: { resource: keyof typeof resources }) {
  const config = resources[resource]; const [rows, setRows] = useState<Array<any>>([]); const [query, setQuery] = useState(""); const [error, setError] = useState("");
  useEffect(() => { fetchAllPages<any>(`/api/v1/admin/${config.endpoint}/?page_size=100&search=${encodeURIComponent(query)}`).then(setRows).catch((e) => setError(e.message)); }, [config.endpoint, query]);
  return <AdminLayout title={config.title}><div className="admin-title"><div><span className="eyebrow">Operación</span><h2>{config.title}</h2></div></div><div className="admin-toolbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Buscar en ${config.title.toLowerCase()}`} /><span>{rows.length} registros</span>{config.exportable && <a className="button secondary" href={`/api/v1/admin/${config.endpoint}/export/`}>Exportar CSV</a>}</div>{error ? <p className="form-error">{error}</p> : rows.length ? <AdminTable heads={config.heads}>{rows.map((x) => <tr key={x.id}>{config.row(x).map((value, index) => <td key={index}>{value}</td>)}</tr>)}</AdminTable> : <div className="empty-state"><p>No hay {config.title.toLowerCase()} en este momento.</p></div>}</AdminLayout>;
}

export function AdminAuditPage() {
  const [rows, setRows] = useState<any[]>([]); const [action, setAction] = useState("");
  useEffect(() => { fetchAllPages<any>(`/api/v1/admin/audit/?page_size=100${action ? `&action=${action}` : ""}`).then(setRows); }, [action]);
  return <AdminLayout title="Historial"><div className="admin-title"><div><span className="eyebrow">Historial</span><h2>Actividad del negocio</h2></div></div><div className="admin-toolbar"><select value={action} onChange={(e) => setAction(e.target.value)}><option value="">Todas las acciones</option><option value="CREATE">Creación</option><option value="UPDATE">Cambio</option><option value="PUBLISH">Publicación</option><option value="ARCHIVE">Archivo</option><option value="PRICE_CHANGE">Cambio de precio</option></select></div><AdminTable heads={["Fecha", "Usuario", "Acción", "Registro", "Resultado"]}>{rows.map((x) => <tr key={x.id}><td>{formatDate(x.occurred_at)}</td><td>{x.actor_name || "Sistema"}</td><td>{x.action_label}</td><td>{x.entity_type}</td><td>{x.success ? "Realizada" : "Fallida"}</td></tr>)}</AdminTable></AdminLayout>;
}

export function AdminCatalogsPage() {
  const [types, setTypes] = useState<any[]>([]); const [amenities, setAmenities] = useState<any[]>([]); const [features, setFeatures] = useState<any[]>([]);
  const load = useCallback(() => Promise.all(["property-types", "amenities", "features"].map((x) => fetchAllPages<any>(`/api/v1/admin/${x}/?page_size=100`))).then(([a,b,c]) => {setTypes(a); setAmenities(b); setFeatures(c);}), []);
  useEffect(() => { void load(); }, [load]);
  return <AdminLayout title="Catálogos"><div className="admin-title"><div><span className="eyebrow">Configuración de negocio</span><h2>Catálogos</h2></div></div><div className="admin-panels"><CatalogBlock title="Tipos de propiedad" endpoint="property-types" rows={types} onChanged={load} /><CatalogBlock title="Amenidades" endpoint="amenities" rows={amenities} onChanged={load} /><CatalogBlock title="Características" endpoint="features" rows={features} onChanged={load} /></div></AdminLayout>;
}
function CatalogBlock({ title, endpoint, rows, onChanged }: { title: string; endpoint: string; rows: any[]; onChanged: () => Promise<void> }) {
  const [name, setName] = useState(""); const [editing, setEditing] = useState<any>(); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const payload = (value: string, current?: any) => endpoint === "property-types"
    ? { code: current?.code || slugify(value), name: value, is_active: current?.is_active ?? true, sort_order: current?.sort_order || 0 }
    : endpoint === "amenities"
      ? { name: value, slug: current?.slug || slugify(value), category: current?.category || "DEVELOPMENT", is_active: current?.is_active ?? true, sort_order: current?.sort_order || 0 }
      : { code: current?.code || slugify(value), label: value, category: current?.category || "General", data_type: current?.data_type || "TEXT", is_public: current?.is_public ?? true, is_filterable: current?.is_filterable ?? false, is_active: current?.is_active ?? true, sort_order: current?.sort_order || 0 };
  const save = async () => { if (!name.trim()) return; setBusy(true); setError(""); try { await apiFetch(editing ? `/api/v1/admin/${endpoint}/${editing.id}/` : `/api/v1/admin/${endpoint}/`, { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload(name.trim(), editing)) }); setName(""); setEditing(undefined); await onChanged(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible guardar"); } finally { setBusy(false); } };
  const toggle = async (row: any) => { setBusy(true); try { await apiFetch(`/api/v1/admin/${endpoint}/${row.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !row.is_active }) }); await onChanged(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible actualizar"); } finally { setBusy(false); } };
  return <section className="admin-panel"><h3>{title}</h3><div className="admin-toolbar"><input value={name} onChange={(e) => setName(e.target.value)} placeholder={editing ? "Nuevo nombre" : "Nueva opción"} /><button className="button" disabled={busy || !name.trim()} onClick={() => void save()}>{busy ? "Guardando…" : editing ? "Guardar" : "Añadir"}</button>{editing && <button className="button secondary" onClick={() => { setEditing(undefined); setName(""); }}>Cancelar</button>}</div>{error && <p className="form-error">{error}</p>}{rows.length ? rows.map((x) => <div className="admin-list-row" key={x.id}><span>{x.name || x.label}</span><small>{x.is_active ? "Activa" : "Inactiva"}</small><div className="table-actions"><button onClick={() => { setEditing(x); setName(x.name || x.label); }}>Renombrar</button><button onClick={() => void toggle(x)}>{x.is_active ? "Desactivar" : "Reactivar"}</button></div></div>) : <p className="muted">No hay opciones.</p>}</section>;
}

const simpleResources: Record<string, { title: string; endpoint: string; heads: string[]; cells: (x: any) => React.ReactNode[] }> = {
  desarrolladoras: { title: "Desarrolladoras", endpoint: "developers", heads: ["Nombre", "Razón social", "Sitio", "Estado"], cells: (x) => [x.name, x.legal_name || "—", x.website || "—", x.is_active ? "Activa" : "Inactiva"] },
  modelos: { title: "Modelos", endpoint: "models", heads: ["Modelo", "Desarrolladora", "Presente en", "Estado"], cells: (x) => [x.name, x.developer_name, x.developments?.map((d: any) => d.name).join(", ") || "Sin desarrollo", x.is_active ? "Activo" : "Inactivo"] },
  publicaciones: { title: "Publicaciones", endpoint: "listings", heads: ["Propiedad", "Publicación", "Destacada", "Actualizada"], cells: (x) => [x.title, x.is_published ? "Publicada" : "Sin publicar", x.is_featured ? "Sí" : "No", formatDate(x.updated_at)] },
  marketing: { title: "Marketing", endpoint: "marketing-campaigns", heads: ["Campaña", "Canal", "Clave de campaña", "Estado"], cells: (x) => [x.name, x.channel, x.utm_campaign, x.is_active ? "Activa" : "Finalizada"] },
  usuarios: { title: "Usuarios", endpoint: "users", heads: ["Nombre", "Correo", "Rol", "Activo", "MFA"], cells: (x) => [x.name, x.email, x.role, x.is_active ? "Sí" : "No", x.mfa_enabled ? "Configurado" : "Pendiente"] },
};

export function AdminSimpleResourcePage({ resource }: { resource: keyof typeof simpleResources }) {
  if (resource === "desarrolladoras" || resource === "modelos") return <EditableCatalogEntityPage resource={resource} />;
  if (resource === "usuarios") return <UserManagementPage />;
  return <ReadonlySimpleResourcePage resource={resource} />;
}

function ReadonlySimpleResourcePage({ resource }: { resource: Exclude<keyof typeof simpleResources, "desarrolladoras" | "modelos" | "usuarios"> }) {
  const config = simpleResources[resource]; const [rows, setRows] = useState<any[]>([]); const [error, setError] = useState("");
  useEffect(() => { fetchAllPages<any>(`/api/v1/admin/${config.endpoint}/?page_size=100`).then(setRows).catch((e) => setError(e.message)); }, [config.endpoint]);
  return <AdminLayout title={config.title}><div className="admin-title"><div><span className="eyebrow">Administración</span><h2>{config.title}</h2></div></div>{error ? <p className="form-error">{error}</p> : rows.length ? <AdminTable heads={config.heads}>{rows.map((x) => <tr key={x.id}>{config.cells(x).map((cell, i) => <td key={i}>{cell}</td>)}</tr>)}</AdminTable> : <div className="empty-state"><p>No hay registros.</p></div>}</AdminLayout>;
}

function EditableCatalogEntityPage({ resource }: { resource: "desarrolladoras" | "modelos" }) {
  const config = simpleResources[resource];
  const [rows, setRows] = useState<any[]>([]); const [developers, setDevelopers] = useState<any[]>([]); const [developments, setDevelopments] = useState<any[]>([]);
  const [editing, setEditing] = useState<any>(); const [name, setName] = useState(""); const [developerId, setDeveloperId] = useState(""); const [description, setDescription] = useState("");
  const [relation, setRelation] = useState<Record<string, string>>({}); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [items, developerData, developmentData] = await Promise.all([
      fetchAllPages<any>(`/api/v1/admin/${config.endpoint}/?page_size=100&archived=all`),
      fetchAllPages<any>("/api/v1/admin/developers/?page_size=100"),
      fetchAllPages<any>("/api/v1/admin/developments/?page_size=100"),
    ]);
    setRows(items); setDevelopers(developerData); setDevelopments(developmentData);
  }, [config.endpoint]);
  useEffect(() => {
    let active = true;
    Promise.all([
      fetchAllPages<any>(`/api/v1/admin/${config.endpoint}/?page_size=100&archived=all`),
      fetchAllPages<any>("/api/v1/admin/developers/?page_size=100"),
      fetchAllPages<any>("/api/v1/admin/developments/?page_size=100"),
    ]).then(([items, developerData, developmentData]) => {
      if (!active) return;
      setRows(items); setDevelopers(developerData); setDevelopments(developmentData);
    }).catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [config.endpoint]);
  const begin = (row?: any) => { setEditing(row || {}); setName(row?.name || ""); setDeveloperId(row?.developer || ""); setDescription(row?.base_description || row?.legal_name || ""); setError(""); };
  const save = async () => {
    if (!name.trim() || (resource === "modelos" && !developerId)) return setError("Completa los campos obligatorios.");
    setBusy(true); setError("");
    try {
      const payload = resource === "modelos"
        ? { name: name.trim(), slug: editing?.slug || slugify(name), developer: developerId, base_description: description || null, is_active: true, ...(editing?.id ? { version: editing.version } : {}) }
        : { name: name.trim(), slug: editing?.slug || slugify(name), legal_name: description || null, is_active: true, ...(editing?.id ? { version: editing.version } : {}) };
      await apiFetch(editing?.id ? `/api/v1/admin/${config.endpoint}/${editing.id}/` : `/api/v1/admin/${config.endpoint}/`, { method: editing?.id ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setEditing(undefined); setName(""); setDescription(""); setDeveloperId(""); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "No fue posible guardar"); } finally { setBusy(false); }
  };
  const archiveOrRestore = async (row: any) => { setBusy(true); try { await apiFetch(row.archived_at ? `/api/v1/admin/${config.endpoint}/${row.id}/restore/` : `/api/v1/admin/${config.endpoint}/${row.id}/`, { method: row.archived_at ? "POST" : "DELETE", body: row.archived_at ? "{}" : undefined }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible actualizar"); } finally { setBusy(false); } };
  const addRelation = async (model: any) => { const development = relation[model.id]; if (!development) return; setBusy(true); try { await apiFetch("/api/v1/admin/development-models/", { method: "POST", body: JSON.stringify({ development, housing_model: model.id, is_active: true }) }); setRelation((current) => ({ ...current, [model.id]: "" })); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible relacionar el modelo"); } finally { setBusy(false); } };
  const removeRelation = async (linkId: string) => { setBusy(true); try { await apiFetch(`/api/v1/admin/development-models/${linkId}/`, { method: "DELETE" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible desvincular"); } finally { setBusy(false); } };
  return <AdminLayout title={config.title}><div className="admin-title"><div><span className="eyebrow">Administración</span><h2>{config.title}</h2></div><button className="button" onClick={() => begin()}>Nuevo registro</button></div>
    {editing && <section className="admin-panel"><h3>{editing.id ? "Editar" : "Nuevo registro"}</h3><div className="admin-form-grid"><label className="field"><span>Nombre</span><input value={name} onChange={(e) => setName(e.target.value)} /></label>{resource === "modelos" && <label className="field"><span>Desarrolladora</span><select value={developerId} onChange={(e) => setDeveloperId(e.target.value)}><option value="">Selecciona</option>{developers.map((x) => <option value={x.id} key={x.id}>{x.name}</option>)}</select></label>}<label className="field"><span>{resource === "modelos" ? "Descripción base" : "Razón social"}</span><input value={description} onChange={(e) => setDescription(e.target.value)} /></label></div><div className="admin-form-actions"><button className="button secondary" onClick={() => setEditing(undefined)}>Cancelar</button><button className="button" disabled={busy} onClick={() => void save()}>{busy ? "Guardando…" : "Guardar"}</button></div></section>}
    {error && <p className="form-error">{error}</p>}
    {rows.length ? <AdminTable heads={[...config.heads, "Acciones"]}>{rows.map((row) => <tr key={row.id}>{config.cells(row).map((cell, i) => <td key={i}>{cell}</td>)}<td><div className="table-actions"><button onClick={() => begin(row)}>Editar</button><button disabled={busy} onClick={() => void archiveOrRestore(row)}>{row.archived_at ? "Restaurar" : "Archivar"}</button></div>{resource === "modelos" && !row.archived_at && <div><div className="admin-toolbar"><select value={relation[row.id] || ""} onChange={(e) => setRelation((current) => ({ ...current, [row.id]: e.target.value }))}><option value="">Añadir a desarrollo</option>{developments.filter((d) => d.developer === row.developer && !row.developments?.some((linked: any) => linked.id === d.id)).map((d) => <option value={d.id} key={d.id}>{d.name}</option>)}</select><button disabled={busy || !relation[row.id]} onClick={() => void addRelation(row)}>Relacionar</button></div>{row.developments?.map((linked: any) => <div className="admin-list-row" key={linked.link_id}><span>{linked.name}</span><button onClick={() => void removeRelation(linked.link_id)}>Desvincular</button></div>)}</div>}</td></tr>)}</AdminTable> : <div className="empty-state"><p>No hay registros.</p></div>}
  </AdminLayout>;
}

function UserManagementPage() {
  const [rows, setRows] = useState<any[]>([]); const [creating, setCreating] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", role_name: "Founder Admin" });
  const load = useCallback(() => fetchAllPages<any>("/api/v1/admin/users/?page_size=100").then(setRows), []);
  useEffect(() => { fetchAllPages<any>("/api/v1/admin/users/?page_size=100").then(setRows).catch((e) => setError(e.message)); }, []);
  const create = async () => { setBusy(true); setError(""); try { await apiFetch("/api/v1/admin/users/", { method: "POST", body: JSON.stringify(form) }); setCreating(false); setForm({ first_name: "", last_name: "", email: "", password: "", role_name: "Founder Admin" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible crear el usuario"); } finally { setBusy(false); } };
  const changeActive = async (user: any) => { setBusy(true); setError(""); try { await apiFetch(`/api/v1/admin/users/${user.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !user.is_active, role_name: user.role }) }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible cambiar el acceso"); } finally { setBusy(false); } };
  const securityAction = async (user: any, action: "revoke-sessions" | "reset-mfa") => { setBusy(true); setError(""); try { await apiFetch(`/api/v1/admin/users/${user.id}/${action}/`, { method: "POST", body: "{}" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible completar la acción"); } finally { setBusy(false); } };
  return <AdminLayout title="Usuarios"><div className="admin-title"><div><span className="eyebrow">Accesos</span><h2>Usuarios</h2></div><button className="button" onClick={() => setCreating(true)}>Crear usuario</button></div>
    {creating && <section className="admin-panel"><h3>Nuevo usuario administrativo</h3><div className="admin-form-grid">{(["first_name", "last_name", "email", "password"] as const).map((key) => <label className="field" key={key}><span>{{ first_name: "Nombre", last_name: "Apellidos", email: "Correo", password: "Contraseña inicial" }[key]}</span><input type={key === "password" ? "password" : key === "email" ? "email" : "text"} value={form[key]} onChange={(e) => setForm((current) => ({ ...current, [key]: e.target.value }))} /></label>)}<label className="field"><span>Rol</span><select value={form.role_name} onChange={(e) => setForm((current) => ({ ...current, role_name: e.target.value }))}><option value="Founder Admin">Administrador de negocio</option></select></label></div><p className="muted">El usuario deberá configurar MFA en su primer acceso.</p><div className="admin-form-actions"><button className="button secondary" onClick={() => setCreating(false)}>Cancelar</button><button className="button" disabled={busy} onClick={() => void create()}>{busy ? "Guardando…" : "Crear usuario"}</button></div></section>}
    {error && <p className="form-error">{error}</p>}
    <AdminTable heads={["Nombre", "Correo", "Rol", "Activo", "Último acceso", "MFA", "Acciones"]}>{rows.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td>{user.role}</td><td>{user.is_active ? "Sí" : "No"}</td><td>{user.last_login ? formatDate(user.last_login) : "—"}</td><td>{user.mfa_enabled ? "Configurado" : "Pendiente"}</td><td><div className="table-actions"><button disabled={busy || user.role === "Owner"} onClick={() => void changeActive(user)}>{user.is_active ? "Desactivar" : "Reactivar"}</button><button disabled={busy} onClick={() => void securityAction(user, "revoke-sessions")}>Revocar sesiones</button><button disabled={busy} onClick={() => void securityAction(user, "reset-mfa")}>Restablecer MFA</button></div></td></tr>)}</AdminTable>
  </AdminLayout>;
}
