"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  BarChart3,
  Building2,
  FileText,
  Home,
  Images,
  LogOut,
  MapPin,
  MessageSquare,
  Pencil,
  Plus,
  Trash2,
  Eye,
  ExternalLink,
  Users,
  CalendarDays,
  Handshake,
  ShieldCheck,
  Megaphone,
  Layers3,
  KeyRound,
} from "lucide-react";
import type {
  Development,
  Guide,
  HomeContent,
  Location,
  Property,
  PropertyType,
  PropertyTypeOption,
  SiteSettings,
} from "@/types";
import {
  developmentService,
  guideService,
  homeContentService,
  propertyService,
  useCasaViva,
} from "@/services";
import { formatCurrency, formatDate, slugify, uid } from "@/lib/utils";
import {
  CasaVivaLogo,
  ConfirmDialog,
  Modal,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { api, apiFetch, fetchAllPages, mapProperty } from "@/services/api";

const adminNav = [
  ["Inicio", "/administracion", Home, []],
  ["Propiedades", "/administracion/propiedades", Building2, ["catalog.manage_offerings"]],
  ["Desarrolladoras", "/administracion/desarrolladoras", Building2, ["catalog.manage_developers"]],
  ["Desarrollos", "/administracion/desarrollos", Images, ["catalog.manage_developments"]],
  ["Modelos", "/administracion/modelos", Layers3, ["catalog.manage_models"]],
  ["Catálogos", "/administracion/catalogos", MapPin, ["catalog.manage_catalogs"]],
  ["Contenido", "/administracion/contenido", FileText, ["content.manage_content"]],
  ["Legal", "/administracion/legal", FileText, ["crm.publish_privacy_notice", "crm.publish_terms_of_use"]],
  ["Consultas", "/administracion/consultas", MessageSquare, ["crm.manage_inquiries"]],
  ["Clientes", "/administracion/clientes", Users, ["crm.manage_leads"]],
  ["Visitas", "/administracion/visitas", CalendarDays, ["crm.manage_visits"]],
  ["Ventas", "/administracion/ventas", Handshake, ["crm.manage_sales"]],
  ["Marketing", "/administracion/marketing", Megaphone, ["marketing.view_campaigns", "marketing.manage_campaigns", "marketing.view_spend", "marketing.manage_spend"]],
  ["Resultados", "/administracion/bi", BarChart3, ["analytics.view_bi"]],
  ["Historial", "/administracion/auditoria", ShieldCheck, ["audit.view_audit"]],
] as const;
export function AdminHeader({ title }: { title: string }) {
  return (
    <header className="admin-header">
      <h1>{title}</h1>
    </header>
  );
}
export function AdminSidebar() {
  const path = usePathname();
  const router = useRouter();
  const { logout } = useCasaViva();
  const [session, setSession] = useState<{ can_manage_users?: boolean; effective_permissions?: string[]; role?: string; casaviva_mode?: string }>({});
  useEffect(() => { apiFetch<typeof session>("/api/v1/auth/me/").then(setSession).catch(() => setSession({})); }, []);
  const permissions = new Set(session.effective_permissions || []);
  const owner = session.role === "Owner";
  return (
    <aside className="admin-sidebar">
      <Link href="/administracion">
        <CasaVivaLogo variant="light" />
      </Link>
      <div className="admin-sidebar-scroll">
        <nav className="admin-nav">
          {adminNav.filter(([, , , required]) => owner || required.length === 0 || required.some((key) => permissions.has(key))).map(([label, href, Icon]) => (
            <Link
              key={href}
              href={href}
              className={
                path === href || (href !== "/administracion" && path.startsWith(href))
                  ? "active"
                  : ""
              }
              title={label}
            >
              <Icon size={16} /> {label}
            </Link>
          ))}
        </nav>
        {session.can_manage_users && <div className="admin-security"><span>Seguridad</span><nav className="admin-nav"><Link href="/administracion/usuarios" className={path.startsWith("/administracion/usuarios") ? "active" : ""}><Users size={16} /> Usuarios</Link><Link href="/administracion/roles" className={path.startsWith("/administracion/roles") ? "active" : ""}><KeyRound size={16} /> Roles</Link></nav></div>}
      </div>
      <div className="admin-nav-bottom">
        {session.casaviva_mode === "demo" && <div className="admin-demo">MODO DEMOSTRACIÓN · DATOS SIMULADOS</div>}
        <Link href="/" target="_blank">
          <ExternalLink size={16} /> Ver sitio
        </Link>
        <button
          className="button ghost"
          onClick={() => {
            void logout();
            router.push("/administracion/acceso");
          }}
        >
          <LogOut size={16} /> Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
export function AdminLayout({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { adminAuthenticated, adminInitialized, hydrated, refreshAdmin } = useCasaViva();
  const router = useRouter();
  useEffect(() => {
    if (hydrated && !adminAuthenticated) router.replace("/administracion/acceso");
    if (hydrated && adminAuthenticated && !adminInitialized) void refreshAdmin();
  }, [hydrated, adminAuthenticated, adminInitialized, router, refreshAdmin]);
  if (!hydrated || !adminAuthenticated || !adminInitialized)
    return (
      <div className="empty-state">
        <p>Cargando administración…</p>
      </div>
    );
  return (
    <div className="admin-layout" data-admin-ready="true">
      <AdminSidebar />
      <AdminHeader title={title} />
      <main className="admin-main">{children}</main>
    </div>
  );
}

type AdminMedia = { mediaId: string; role: "HERO" | "GALLERY" | "FLOORPLAN" | "DOCUMENT"; sortOrder: number; url?: string };
function MediaManager({ title, assets, onChange }: { title: string; assets: AdminMedia[]; onChange: (assets: AdminMedia[]) => void }) {
  const [role, setRole] = useState<AdminMedia["role"]>("GALLERY"); const [uploading, setUploading] = useState(false); const { toast } = useToast();
  const ordered = [...assets].sort((a,b) => a.sortOrder - b.sortOrder);
  const upload = async (file?: File) => { if (!file) return; setUploading(true); try { const form = new FormData(); form.append("file", file); form.append("media_type", role === "DOCUMENT" ? "DOCUMENT" : role === "FLOORPLAN" ? "FLOORPLAN" : "IMAGE"); form.append("alt_text", title); const asset = await apiFetch<{ id: string; url: string }>("/api/v1/admin/media/", { method: "POST", body: form }); const next = role === "HERO" ? assets.filter((x) => x.role !== "HERO") : assets; onChange([...next, { mediaId: asset.id, role, sortOrder: next.length, url: asset.url }]); } catch (error) { toast(error instanceof Error ? error.message : "No fue posible cargar el archivo"); } finally { setUploading(false); } };
  const mutate = (id: string, changes?: Partial<AdminMedia>, direction=0) => { let next = ordered.map((asset) => asset.mediaId === id ? { ...asset, ...changes } : asset); if (changes?.role === "HERO") next = next.filter((asset) => asset.mediaId === id || asset.role !== "HERO"); if (direction) { const index = next.findIndex((asset) => asset.mediaId === id); const target = index + direction; if (target >= 0 && target < next.length) [next[index], next[target]] = [next[target], next[index]]; } onChange(next.map((asset, index) => ({ ...asset, sortOrder: index }))); };
  return <div className="media-manager"><div className="admin-toolbar"><select value={role} onChange={(e) => setRole(e.target.value as AdminMedia["role"])}><option value="HERO">Principal</option><option value="GALLERY">Galería</option><option value="FLOORPLAN">Plano</option><option value="DOCUMENT">Documento</option></select><label className="button secondary media-upload">{uploading ? "Cargando…" : "Añadir archivo"}<input type="file" accept={role === "DOCUMENT" ? "application/pdf" : "image/jpeg,image/png,image/webp,application/pdf"} disabled={uploading} onChange={(e) => void upload(e.target.files?.[0])} /></label></div>{ordered.map((asset, index) => <div className="media-row" key={asset.mediaId}>{asset.url && asset.role !== "DOCUMENT" ? <Image src={asset.url} alt="" width={72} height={48} /> : <FileText size={24} />}<select value={asset.role} onChange={(e) => mutate(asset.mediaId, { role: e.target.value as AdminMedia["role"] })}><option value="HERO">Principal</option><option value="GALLERY">Galería</option><option value="FLOORPLAN">Plano</option><option value="DOCUMENT">Documento</option></select><button type="button" disabled={index === 0} onClick={() => mutate(asset.mediaId, undefined, -1)}>↑</button><button type="button" disabled={index === ordered.length - 1} onClick={() => mutate(asset.mediaId, undefined, 1)}>↓</button><button type="button" onClick={() => onChange(assets.filter((x) => x.mediaId !== asset.mediaId))}>Quitar vínculo</button></div>)}</div>;
}

const loginSchema = z.object({ email: z.email(), password: z.string().min(1) });
type LoginData = z.infer<typeof loginSchema>;
export function AdminLoginPage() {
  const { adminAuthenticated, hydrated, login } = useCasaViva();
  const router = useRouter();
  const [invalid, setInvalid] = useState("");
  const [stage, setStage] = useState<"credentials" | "mfa">("credentials");
  const [code, setCode] = useState("");
  const [qr, setQr] = useState<string>();
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const { register, handleSubmit } = useForm<LoginData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  useEffect(() => {
    if (hydrated && adminAuthenticated) router.replace("/administracion");
  }, [hydrated, adminAuthenticated, router]);
  const submit = async (d: LoginData) => {
    setInvalid("");
    try {
      const result = await apiFetch<{ enrollment_required: boolean }>("/api/v1/auth/login/", { method: "POST", body: JSON.stringify(d) });
      if (result.enrollment_required) {
        const enrollment = await apiFetch<{ qr_png: string }>("/api/v1/auth/mfa/enroll/", { method: "POST", body: "{}" });
        setQr(`data:image/png;base64,${enrollment.qr_png}`);
      }
      setStage("mfa");
    } catch (error) { setInvalid(error instanceof Error ? error.message : "No fue posible iniciar sesión."); }
  };
  const verify = async (event: React.FormEvent) => {
    event.preventDefault(); setInvalid("");
    try {
      const result = await apiFetch<{ recovery_codes?: string[] }>("/api/v1/auth/mfa/verify/", { method: "POST", body: JSON.stringify({ code }) });
      if (result.recovery_codes?.length) { setRecoveryCodes(result.recovery_codes); return; }
      login(); router.push("/administracion");
    } catch (error) { setInvalid(error instanceof Error ? error.message : "Código incorrecto."); }
  };
  return (
    <div className="admin-login">
      <div
        className="admin-login-art"
        style={{
          backgroundImage:
            "url(https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=86)",
        }}
      />
      <div className="admin-login-form">
        <div>
          <CasaVivaLogo />
          <h1>Administración</h1>
          <p className="muted">Gestiona propiedades, clientes, contenido y resultados.</p>
          {stage === "credentials" ? <form key="credentials" method="post" data-hydrated={hydrated ? "true" : "false"} onSubmit={handleSubmit(submit)}>
            <label className="field">
              <span>Correo</span>
              <input type="email" {...register("email")} />
            </label>
            <label className="field">
              <span>Contraseña</span>
              <input type="password" {...register("password")} />
            </label>
            {invalid && <small>{invalid}</small>}
            <button className="button" type="submit" disabled={!hydrated}>
              Entrar
            </button>
          </form> : recoveryCodes.length ? <div className="recovery-codes"><h2>Códigos de recuperación</h2><p>Guárdalos ahora en un lugar seguro. No volverán a mostrarse.</p>{recoveryCodes.map((x) => <code key={x}>{x}</code>)}<button className="button" onClick={() => { login(); router.push("/administracion"); }}>Continuar</button></div> : <form key="mfa" method="post" data-hydrated={hydrated ? "true" : "false"} onSubmit={verify}>{qr && <><p>Escanea este código con tu aplicación de autenticación.</p><Image src={qr} alt="Código de configuración MFA" width={220} height={220} unoptimized /></>}<label className="field"><span>Código de seguridad</span><input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} /></label>{invalid && <small>{invalid}</small>}<button className="button" type="submit" disabled={!hydrated}>Verificar</button></form>}
        </div>
      </div>
    </div>
  );
}

export function AdminDashboard() {
  const { properties, developments, inquiries } = useCasaViva();
  const published = properties.filter((p) => p.published).length;
  return (
    <AdminLayout title="Inicio">
      <div className="admin-title">
        <div>
          <span className="eyebrow">Operación</span>
          <h2>Resumen del sitio</h2>
        </div>
      </div>
      <div className="metric-grid">
        <Metric label="Propiedades publicadas" value={published} />
        <Metric
          label="Propiedades borrador"
          value={properties.length - published}
        />
        <Metric label="Desarrollos" value={developments.length} />
        <Metric label="Consultas recibidas" value={inquiries.length} />
      </div>
      <div className="admin-panels">
        <section className="admin-panel">
          <h3>Últimas propiedades</h3>
          {[...properties]
            .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
            .slice(0, 5)
            .map((p) => (
              <Link
                className="admin-list-row"
                href={`/administracion/propiedades/${p.id}`}
                key={p.id}
              >
                <Image src={p.heroImage} alt="" width={60} height={44} />
                <span style={{ flex: 1 }}>{p.title}</span>
                <span>{formatCurrency(p.price)}</span>
              </Link>
            ))}
        </section>
        <section className="admin-panel">
          <h3>Últimas consultas</h3>
          {inquiries.slice(0, 5).map((i) => (
            <Link className="admin-list-row" href="/administracion/consultas" key={i.id}>
              <span style={{ flex: 1 }}>
                <strong>{i.name}</strong>
                <br />
                <small>{i.message.slice(0, 45)}…</small>
              </span>
              <StatusBadge tone={i.status === "new" ? "danger" : "neutral"}>
                {statusLabel(i.status)}
              </StatusBadge>
            </Link>
          ))}
        </section>
      </div>
    </AdminLayout>
  );
}
function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function AdminPropertiesPage() {
  const { properties, deleteProperty, refreshAdmin } = useCasaViva();
  const [query, setQuery] = useState("");
  const [remove, setRemove] = useState<Property>();
  const [showArchived, setShowArchived] = useState(false);
  const [archived, setArchived] = useState<Property[]>([]);
  const [hardDelete, setHardDelete] = useState<Property>();
  const [confirmation, setConfirmation] = useState("");
  const [hardDeleteReason, setHardDeleteReason] = useState("");
  const [deletePreview, setDeletePreview] = useState<{ inquiries: number; visits: number; interests: number; analytics_events: number; sales: number; can_delete: boolean }>();
  const [actionError, setActionError] = useState("");
  const { toast } = useToast();
  useEffect(() => {
    if (!showArchived) return;
    fetchAllPages<Record<string, any>>("/api/v1/admin/properties/?page_size=100&archived=all")
      .then((result) => setArchived(result.map(mapProperty).filter((item) => Boolean(item.archivedAt))))
      .catch((error) => setActionError(error instanceof Error ? error.message : "No fue posible cargar los registros archivados"));
  }, [showArchived]);
  const source = showArchived ? archived : properties;
  const list = source.filter((p) =>
    [p.title, p.municipality, p.slug]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <AdminLayout title="Propiedades">
      <AdminTitle
        title="Propiedades"
        action="Nueva propiedad"
        href="/administracion/propiedades/nueva"
      />
      <div className="admin-toolbar">
        <input
          placeholder="Buscar propiedad o ubicación"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <span>{list.length} registros</span>
        <button className="button secondary" onClick={() => setShowArchived((value) => !value)}>{showArchived ? "Ver activas" : "Ver archivadas"}</button>
        <a className="button secondary" href="/api/v1/admin/offerings/export/">Exportar CSV</a>
      </div>
      {actionError && <p className="form-error">{actionError}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Imagen</th>
              <th>Propiedad</th>
              <th>Ubicación</th>
              <th>Precio</th>
              <th>Estado</th>
              <th>Publicada</th>
              <th>Actualizada</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {list.map((p) => (
              <tr key={p.id}>
                <td>
                  <Image src={p.heroImage} alt="" width={70} height={50} />
                </td>
                <td>
                  <strong>{p.title}</strong>
                  <br />
                  <small>{p.slug}</small>
                </td>
                <td>
                  {p.municipality}
                  <br />
                  <small>{p.state}</small>
                </td>
                <td>{formatCurrency(p.price)}</td>
                <td>
                  <StatusBadge
                    tone={
                      p.status === "available"
                        ? "success"
                        : p.status === "temporarily_unavailable"
                          ? "danger"
                          : "neutral"
                    }
                  >
                    {p.status}
                  </StatusBadge>
                </td>
                <td>{p.published ? "Sí" : "Borrador"}</td>
                <td>{formatDate(p.updatedAt)}</td>
                <td>
                  <div className="table-actions">
                    {!showArchived && <Link title="Editar" href={`/administracion/propiedades/${p.id}`}>
                      <Pencil size={16} />
                    </Link>}
                    {!showArchived && <Link
                      title="Vista previa"
                      href={`/preview/propiedades/${p.id}`}
                      target="_blank"
                    >
                      <Eye size={16} />
                    </Link>}
                    {!showArchived && <button title="Archivar" onClick={() => setRemove(p)}>
                      <Trash2 size={16} />
                    </button>}
                    {showArchived && <button onClick={async () => { try { await apiFetch(`/api/v1/admin/properties/${p.id}/restore/`, { method: "POST", body: "{}" }); setArchived((items) => items.filter((item) => item.id !== p.id)); await refreshAdmin(); toast("Registro restaurado"); } catch (error) { setActionError(error instanceof Error ? error.message : "No fue posible restaurar"); } }}>Restaurar</button>}
                    {showArchived && <button className="danger" onClick={() => { setHardDelete(p); setConfirmation(""); setHardDeleteReason(""); setDeletePreview(undefined); setActionError(""); void apiFetch<{ inquiries: number; visits: number; interests: number; analytics_events: number; sales: number; can_delete: boolean }>(`/api/v1/admin/properties/${p.id}/delete-preview/`).then(setDeletePreview).catch((error) => setActionError(error instanceof Error ? error.message : "No fue posible revisar las dependencias")); }}>Eliminar definitivamente</button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={!!remove}
        onClose={() => setRemove(undefined)}
        title="¿Archivar esta propiedad?"
        description="La propiedad saldrá del flujo operativo y podrá restaurarse posteriormente."
        confirmLabel="Archivar"
        onConfirm={async () => {
          if (remove) {
            try { await deleteProperty(remove.id); toast("Propiedad archivada"); }
            catch (error) { setActionError(error instanceof Error ? error.message : "No fue posible archivar"); }
          }
        }}
      />
      <Modal open={Boolean(hardDelete)} onClose={() => setHardDelete(undefined)} title="Eliminar definitivamente">
        <p className="muted">Esta acción no se puede deshacer. Si el registro forma parte de una venta, CasaViva impedirá eliminarlo.</p>
        {deletePreview && <div className="inventory-line"><span>Consultas <strong>{deletePreview.inquiries}</strong></span><span>Visitas <strong>{deletePreview.visits}</strong></span><span>Intereses <strong>{deletePreview.interests}</strong></span><span>Eventos históricos <strong>{deletePreview.analytics_events}</strong></span><span>Ventas <strong>{deletePreview.sales}</strong></span></div>}
        <label className="field"><span>Para confirmar, escribe “{hardDelete?.title}”</span><input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>
        <label className="field"><span>Motivo</span><textarea value={hardDeleteReason} onChange={(event) => setHardDeleteReason(event.target.value)} /></label>
        {actionError && <p className="form-error">{actionError}</p>}
        {deletePreview?.sales ? <p className="form-error">Este registro forma parte del historial de una venta y no puede eliminarse definitivamente. Puedes conservarlo archivado.</p> : null}
        <div className="modal-actions"><button className="button secondary" onClick={() => setHardDelete(undefined)}>Cancelar</button><button className="button danger" disabled={!hardDelete || confirmation !== hardDelete.title || !hardDeleteReason.trim() || !deletePreview?.can_delete} onClick={async () => { if (!hardDelete) return; try { await apiFetch(`/api/v1/admin/properties/${hardDelete.id}/hard-delete/`, { method: "POST", body: JSON.stringify({ confirmation, reason: hardDeleteReason.trim() }) }); setArchived((items) => items.filter((item) => item.id !== hardDelete.id)); setHardDelete(undefined); toast("Registro eliminado definitivamente"); } catch (error) { setActionError(error instanceof Error ? error.message : "No fue posible eliminar"); } }}>Eliminar definitivamente</button></div>
      </Modal>
    </AdminLayout>
  );
}
function AdminTitle({
  title,
  action,
  href,
}: {
  title: string;
  action?: string;
  href?: string;
}) {
  return (
    <div className="admin-title">
      <div>
        <span className="eyebrow">CasaViva</span>
        <h2>{title}</h2>
      </div>
      {action && href && (
        <Link className="button" href={href}>
          <Plus size={16} />
          {action}
        </Link>
      )}
    </div>
  );
}

const propertySchema = z.object({
  title: z.string().min(3),
  slug: z.string().min(3),
});
const blankProperty = (): Property => ({
  id: uid("prop"),
  slug: "",
  title: "",
  operation: "sale",
  propertyType: "",
  condition: undefined,
  status: "available",
  sourceType: "PRIVATE",
  promotionAuthorized: false,
  published: false,
  featured: false,
  currency: "MXN",
  priceLabel: "fixed",
  description: "",
  shortDescription: "",
  amenities: [],
  internalFeatures: [],
  externalFeatures: [],
  heroImage: "/casaviva-placeholder.svg",
  gallery: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  internal: {},
});
export function PropertyFormPage({ id }: { id?: string }) {
  const { properties, developments, locations } = useCasaViva();
  const router = useRouter();
  const existing = properties.find((p) => p.id === id);
  const [item, setItem] = useState<Property>(() =>
    existing ? structuredClone(existing) : blankProperty(),
  );
  const [errors, setErrors] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState<{ prices: any[]; availability: any[] }>({ prices: [], availability: [] });
  const [modelLinks, setModelLinks] = useState<Array<{ id: string; development: string; development_name: string; housing_model: string; model_name: string; developer_id: string; developer_name: string }>>([]);
  const [amenityOptions, setAmenityOptions] = useState<Array<{ id: string; name: string; category: string }>>([]);
  const [propertyTypeOptions, setPropertyTypeOptions] = useState<PropertyTypeOption[]>([]);
  const [featureOptions, setFeatureOptions] = useState<Array<{ id: string; label: string; data_type: string; unit?: string; choices?: Array<{ id: string; label: string }> }>>([]);
  const [localityOptions, setLocalityOptions] = useState<Array<{ id: string; name: string }>>([]);
  const [neighborhoodOptions, setNeighborhoodOptions] = useState<Array<{ id: string; name: string; postal_code?: string }>>([]);
  useEffect(() => { if (existing || item.sourceType === "DEVELOPER") fetchAllPages<(typeof modelLinks)[number]>("/api/v1/admin/development-models/?page_size=100").then(setModelLinks).catch(() => setModelLinks([])); }, [existing, item.sourceType]);
  useEffect(() => { fetchAllPages<{ id: string; name: string; category: string }>("/api/v1/admin/amenities/?page_size=100&is_active=true").then(setAmenityOptions).catch(() => setAmenityOptions([])); }, []);
  useEffect(() => { api.propertyTypes().then(setPropertyTypeOptions).catch(() => setPropertyTypeOptions([])); }, []);
  const effectiveMunicipalityId = item.municipalityId || developments.find((development) => development.id === item.developmentId)?.municipalityId;
  useEffect(() => {
    let cancelled = false;
    if (!effectiveMunicipalityId) {
      queueMicrotask(() => { if (!cancelled) { setLocalityOptions([]); setNeighborhoodOptions([]); } });
      return () => { cancelled = true; };
    }
    Promise.all([
      fetchAllPages<{ id: string; name: string }>(`/api/v1/admin/localities/?municipality=${effectiveMunicipalityId}&is_active=true&page_size=100`),
      fetchAllPages<{ id: string; name: string; postal_code?: string }>(`/api/v1/admin/neighborhoods/?municipality=${effectiveMunicipalityId}&is_active=true&page_size=100`),
    ]).then(([localities, neighborhoods]) => { if (!cancelled) { setLocalityOptions(localities); setNeighborhoodOptions(neighborhoods); } }).catch(() => { if (!cancelled) { setLocalityOptions([]); setNeighborhoodOptions([]); } });
    return () => { cancelled = true; };
  }, [effectiveMunicipalityId]);
  useEffect(() => { fetchAllPages<{ id: string; label: string; data_type: string; unit?: string; choices?: Array<{ id: string; label: string }> }>("/api/v1/admin/features/?page_size=100&is_active=true").then(setFeatureOptions).catch(() => setFeatureOptions([])); }, []);
  useEffect(() => { if (!id) return; Promise.all([apiFetch<any[]>(`/api/v1/admin/properties/${id}/price_history/`), apiFetch<any[]>(`/api/v1/admin/properties/${id}/availability_history/`)]).then(([prices, availability]) => setHistory({ prices, availability })).catch(() => undefined); }, [id]);
  const { toast } = useToast();
  const update = <K extends keyof Property>(key: K, value: Property[K]) =>
    setItem((p) => ({ ...p, [key]: value }));
  const save = async () => {
    const parsed = propertySchema.safeParse(item);
    const duplicate = properties.some(
      (p) => p.slug === item.slug && p.id !== item.id,
    );
    const issues = [
      ...(!parsed.success
        ? parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`)
        : []),
      ...(duplicate ? ["El slug ya existe."] : []),
    ];
    if (issues.length) {
      setErrors(issues);
      return;
    }
    setSaving(true);
    try {
      await propertyService.save({ ...item, updatedAt: new Date().toISOString() });
      toast(existing ? "Cambios guardados" : "Propiedad creada");
      router.push("/administracion/propiedades");
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Error al guardar"]);
    } finally { setSaving(false); }
  };
  return (
    <AdminLayout title={existing ? "Editar propiedad" : "Nueva propiedad"}>
      <AdminTitle
        title={existing ? item.title || "Editar propiedad" : "Nueva propiedad"}
      />
      {errors.length > 0 && (
        <div className="demo-reset">
          {errors.map((e) => (
            <div key={e}>{e}</div>
          ))}
        </div>
      )}
      <FormSection title="Información básica">
        <div className="admin-form-grid">
          <Text
            label="Título"
            value={item.title}
            onChange={(v) => {
              update("title", v);
              if (!existing) update("slug", slugify(v));
            }}
          />
          <Text
            label="Slug"
            value={item.slug}
            onChange={(v) => update("slug", slugify(v))}
          />
          <Select
            label="Tipo"
            value={item.propertyType}
            onChange={(v) => update("propertyType", v as PropertyType)}
            options={[["Selecciona", ""], ...propertyTypeOptions.map((option) => [option.name, option.code])]}
          />
          <Select
            label="Condición"
            value={item.condition || ""}
            onChange={(v) => update("condition", (v || undefined) as Property["condition"])}
            options={[
              ["Sin especificar", ""],
              ["Nueva", "new"],
              ["Usada", "used"],
            ]}
          />
          <Select
            label="Estado de inventario"
            value={item.status}
            onChange={(v) => update("status", v as Property["status"])}
            options={[
              ["Disponible", "available"],
              ["No disponible temporalmente", "temporarily_unavailable"],
              ["Reservada", "reserved"],
              ["Vendida", "sold"],
            ]}
          />
          <Toggle
            label="Publicada"
            checked={item.published}
            onChange={(v) => update("published", v)}
          />
          <Toggle
            label="Destacada"
            checked={item.featured}
            onChange={(v) => update("featured", v)}
          />
        </div>
      </FormSection>
      <FormSection title="Precio">
        <div className="admin-form-grid">
          <Select
            label="Tipo de precio"
            value={item.priceLabel || "fixed"}
            onChange={(value) => setItem((current) => ({
              ...current,
              priceLabel: value as Property["priceLabel"],
              price: value === "on-request" ? undefined : current.price,
              priceMax: value === "range" ? current.priceMax : undefined,
            }))}
            options={[
              ["Precio fijo", "fixed"],
              ["Desde", "from"],
              ["Rango", "range"],
              ["A consultar", "on-request"],
            ]}
          />
          {item.priceLabel !== "on-request" && <NumberField
            label={item.priceLabel === "range" ? "Precio mínimo MXN" : "Precio MXN"}
            value={item.price}
            onChange={(v) => update("price", v)}
          />}
          {item.priceLabel === "range" && <NumberField
            label="Precio máximo MXN"
            value={item.priceMax}
            onChange={(v) => update("priceMax", v)}
          />}
        </div>
      </FormSection>
      <FormSection title="Ubicación">
        <div className="admin-form-grid">
          <Select label="Localidad" value={item.localityId || ""} onChange={(value) => update("localityId", value || undefined)} options={[["Sin especificar", ""], ...localityOptions.map((option) => [option.name, option.id])]} />
          <Select label="Colonia" value={item.neighborhoodId || ""} onChange={(value) => { const option = neighborhoodOptions.find((candidate) => candidate.id === value); setItem((current) => ({ ...current, neighborhoodId: value || undefined, neighborhood: option?.name, postalCode: current.postalCode || option?.postal_code || undefined })); }} options={[["Sin especificar", ""], ...neighborhoodOptions.map((option) => [option.name, option.id])]} />
          <Text
            label="Dirección"
            value={item.address || ""}
            onChange={(v) => update("address", v)}
          />
          <Text label="Código postal" value={item.postalCode || ""} onChange={(value) => update("postalCode", value)} />
          <NumberField
            label="Latitud"
            value={item.latitude}
            onChange={(v) => update("latitude", v)}
            step="0.000001"
          />
          <NumberField
            label="Longitud"
            value={item.longitude}
            onChange={(v) => update("longitude", v)}
            step="0.000001"
          />
        </div>
      </FormSection>
      <FormSection title="Dimensiones">
        <div className="admin-form-grid">
          {[
            ["Recámaras mínimas", "bedrooms"],
            ["Recámaras máximas", "bedroomsMax"],
            ["Baños", "bathrooms"],
            ["Baños completos", "fullBathrooms"],
            ["Medios baños", "halfBathrooms"],
            ["Estacionamientos mínimos", "parkingSpaces"],
            ["Estacionamientos máximos", "parkingMax"],
            ["Construcción mínima m²", "constructionM2"],
            ["Construcción máxima m²", "constructionM2Max"],
            ["Terreno mínimo m²", "landM2"],
            ["Terreno máximo m²", "landM2Max"],
            ["Jardín mínimo m²", "gardenM2"],
            ["Jardín máximo m²", "gardenM2Max"],
            ["Niveles mínimos", "levels"],
            ["Niveles máximos", "levelsMax"],
          ].map(([l, k]) => (
            <NumberField
              key={k}
              label={l}
              value={item[k as keyof Property] as number | undefined}
              onChange={(v) => update(k as keyof Property, v as never)}
            />
          ))}
        </div>
      </FormSection>
      <FormSection title="Desarrollo">
        <div className="admin-form-grid">
          <Select label="Origen" value={item.sourceType || "PRIVATE"} onChange={(v) => setItem((p) => ({ ...p, sourceType: v as Property["sourceType"], developerId: undefined, developmentId: undefined, developmentModelId: undefined }))} options={[["Particular", "PRIVATE"], ["Desarrolladora", "DEVELOPER"]]} />
          {item.sourceType === "DEVELOPER" && <>
          <Select
            label="Desarrolladora"
            value={item.developerId || ""}
            onChange={(v) => setItem((p) => ({ ...p, developerId: v || undefined, developmentId: undefined, developmentModelId: undefined }))}
            options={[["Selecciona", ""], ...Array.from(new Map(modelLinks.map((x) => [x.developer_id, x.developer_name]))).map(([value, label]) => [label, value])]}
          />
          <Select label="Desarrollo" value={item.developmentId || ""} onChange={(v) => setItem((p) => ({ ...p, developmentId: v || undefined, developmentModelId: undefined }))} options={[["Selecciona", ""], ...developments.filter((d) => modelLinks.some((x) => x.developer_id === item.developerId && x.development === d.id)).map((d) => [d.name, d.id])]} />
          <Select label="Modelo" value={item.developmentModelId || ""} onChange={(v) => { const link = modelLinks.find((x) => x.id === v); setItem((p) => ({ ...p, developmentModelId: v || undefined, modelName: link?.model_name })); }} options={[["Selecciona", ""], ...modelLinks.filter((x) => x.development === item.developmentId).map((x) => [x.model_name, x.id])]} />
          </>}
          {item.sourceType !== "DEVELOPER" && <Select
            label="Ubicación"
            value={locations.find((x) => x.name === item.municipality && x.state === item.state)?.id || ""}
            onChange={(v) => { const location = locations.find((x) => x.id === v); setItem((p) => ({ ...p, municipality: location?.name, state: location?.state, municipalityId: location?.id, stateId: location?.stateId, localityId: undefined, neighborhoodId: undefined })); }}
            options={[["Selecciona estado y municipio", ""], ...locations.map((x) => [`${x.name}, ${x.state}`, x.id])]}
          />
          }
        </div>
      </FormSection>
      <FormSection title="Transparencia comercial">
        <div className="admin-form-grid">
          <Toggle label="Promoción autorizada por el proveedor" checked={Boolean(item.promotionAuthorized)} onChange={(v) => update("promotionAuthorized", v as never)} />
          <Text label="Fecha y hora de última verificación (ISO 8601)" value={item.informationVerifiedAt || ""} onChange={(v) => update("informationVerifiedAt", v)} />
          <Text label="Etiqueta pública opcional del proveedor" value={item.publicProviderLabel || ""} onChange={(v) => update("publicProviderLabel", v)} />
          <Area label="Referencia interna de la fuente (no pública)" value={item.internalSourceReference || ""} onChange={(v) => update("internalSourceReference", v)} />
        </div>
        {item.published && (!item.promotionAuthorized || !item.informationVerifiedAt || (item.sourceType === "DEVELOPER" && !item.developmentModelId)) && <p className="form-error">No se puede publicar: confirma autorización, proveedor y fecha de verificación comercial.</p>}
      </FormSection>
      <FormSection title="Contenido">
        <div className="admin-form-grid">
          <Area
            label="Descripción corta"
            value={item.shortDescription}
            onChange={(v) => update("shortDescription", v)}
          />
          <Area
            label="Descripción completa"
            value={item.description}
            onChange={(v) => update("description", v)}
          />
        </div>
      </FormSection>
      <FormSection title="Características">
        <div className="filter-checks">{amenityOptions.map((amenity) => <label className="check-chip" key={amenity.id}><input type="checkbox" checked={(item.amenityIds || []).includes(amenity.id)} onChange={(event) => setItem((current) => ({ ...current, amenityIds: event.target.checked ? [...(current.amenityIds || []), amenity.id] : (current.amenityIds || []).filter((id) => id !== amenity.id), amenities: event.target.checked ? [...current.amenities.filter((name) => name !== amenity.name), amenity.name] : current.amenities.filter((name) => name !== amenity.name) }))} /><span>{amenity.name}</span></label>)}</div>
        <div className="admin-form-grid">{featureOptions.map((feature) => { const current = item.featureValues?.find((value) => value.definition === feature.id); const setFeature = (changes: Record<string, unknown>) => setItem((property) => ({ ...property, featureValues: [...(property.featureValues || []).filter((value) => value.definition !== feature.id), { definition: feature.id, data_type: feature.data_type, ...changes }] })); return feature.data_type === "BOOLEAN" ? <Toggle key={feature.id} label={feature.label} checked={Boolean(current?.value_boolean)} onChange={(value) => setFeature({ value_boolean: value })} /> : feature.data_type === "NUMBER" ? <NumberField key={feature.id} label={`${feature.label}${feature.unit ? ` (${feature.unit})` : ""}`} value={current?.value_number} onChange={(value) => setFeature({ value_number: value })} /> : feature.data_type === "CHOICE" ? <Select key={feature.id} label={feature.label} value={current?.value_choice || ""} onChange={(value) => setFeature({ value_choice: value || undefined })} options={[["Selecciona", ""], ...(feature.choices || []).map((choice) => [choice.label, choice.id])]} /> : <Text key={feature.id} label={feature.label} value={current?.value_text || ""} onChange={(value) => setFeature({ value_text: value })} />; })}</div>
      </FormSection>
      <FormSection title="Multimedia">
        <MediaManager title={item.title} assets={(item.mediaAssets || []) as AdminMedia[]} onChange={(assets) => setItem((current) => ({ ...current, mediaAssets: assets, heroMediaId: assets.find((asset) => asset.role === "HERO")?.mediaId, heroImage: assets.find((asset) => asset.role === "HERO")?.url || "/casaviva-placeholder.svg" }))} />
      </FormSection>
      {existing && <FormSection title="Historial"><h3>Precio</h3><AdminTable heads={["Fecha", "Tipo", "Valor", "Usuario / origen"]}>{history.prices.map((row) => <tr key={row.id}><td>{formatDate(row.effective_from)}</td><td>{row.price_type}</td><td>{row.amount_min == null ? "A consultar" : formatCurrency(Number(row.amount_min))}</td><td>{row.created_by_name || row.source_name || "Sistema"}</td></tr>)}</AdminTable><h3>Disponibilidad</h3><AdminTable heads={["Fecha", "Estado", "Usuario"]}>{history.availability.map((row) => <tr key={row.id}><td>{formatDate(row.effective_from)}</td><td>{row.status_label}</td><td>{row.changed_by_name || "Sistema"}</td></tr>)}</AdminTable></FormSection>}
      <FormSection title="Datos internos">
        <p className="muted">Estos datos nunca se publican.</p>
        <div className="admin-form-grid">
          <Text
            label="Referencia"
            value={item.internal?.reference || ""}
            onChange={(v) =>
              update("internal", { ...item.internal, reference: v })
            }
          />
          <NumberField
            label="Comisión %"
            value={item.internal?.commissionPercent || 0}
            onChange={(v) =>
              update("internal", { ...item.internal, commissionPercent: v })
            }
          />
          <Area
            label="Notas internas"
            value={item.internal?.notes || ""}
            onChange={(v) => update("internal", { ...item.internal, notes: v })}
          />
        </div>
      </FormSection>
      <div className="admin-form-actions">
        <Link className="button secondary" href="/administracion/propiedades">
          Cancelar
        </Link>
        <button className="button" onClick={() => void save()} disabled={saving}>
          {saving ? "Guardando…" : "Guardar propiedad"}
        </button>
      </div>
    </AdminLayout>
  );
}

export function AdminDevelopmentsPage() {
  const { developments, deleteDevelopment, properties } = useCasaViva();
  const [remove, setRemove] = useState<Development>();
  const { toast } = useToast();
  return (
    <AdminLayout title="Desarrollos">
      <AdminTitle
        title="Desarrollos"
        action="Nuevo desarrollo"
        href="/administracion/desarrollos/nuevo"
      />
      <EntityTable
        heads={[
          "Imagen",
          "Desarrollo",
          "Ubicación",
          "Modelos",
          "Publicada",
          "Acciones",
        ]}
      >
        {developments.map((d) => (
          <tr key={d.id}>
            <td>
              <Image src={d.heroImage} alt="" width={70} height={50} />
            </td>
            <td>
              <strong>{d.name}</strong>
              <br />
              <small>{d.developerName}</small>
            </td>
            <td>
              {d.municipality}, {d.state}
            </td>
            <td>{properties.filter((p) => p.developmentId === d.id).length}</td>
            <td>{d.published ? "Sí" : "Borrador"}</td>
            <td>
              <div className="table-actions">
                <Link href={`/administracion/desarrollos/${d.id}`}>
                  <Pencil size={16} />
                </Link>
                <button onClick={() => setRemove(d)}>
                  <Trash2 size={16} />
                </button>
              </div>
            </td>
          </tr>
        ))}
      </EntityTable>
      <ConfirmDialog
        open={!!remove}
        onClose={() => setRemove(undefined)}
        title="¿Eliminar este desarrollo?"
        description="Las propiedades asociadas conservarán sus datos, pero perderán esta relación."
        onConfirm={() => {
          if (remove) {
            deleteDevelopment(remove.id);
            toast("Desarrollo eliminado");
          }
        }}
      />
    </AdminLayout>
  );
}

export function DevelopmentFormPage({ id }: { id?: string }) {
  const { developments, locations } = useCasaViva();
  const existing = developments.find((d) => d.id === id);
  const router = useRouter();
  const { toast } = useToast();
  const [developers, setDevelopers] = useState<Array<{ id: string; name: string }>>([]);
  const [saving, setSaving] = useState(false);
  const [amenityOptions, setAmenityOptions] = useState<Array<{ id: string; name: string }>>([]);
  const [localityOptions, setLocalityOptions] = useState<Array<{ id: string; name: string }>>([]);
  const [neighborhoodOptions, setNeighborhoodOptions] = useState<Array<{ id: string; name: string; postal_code?: string }>>([]);
  useEffect(() => {
    fetchAllPages<{ id: string; name: string }>("/api/v1/admin/developers/?page_size=100")
      .then(setDevelopers)
      .catch(() => setDevelopers([]));
  }, []);
  useEffect(() => { fetchAllPages<{ id: string; name: string }>("/api/v1/admin/amenities/?is_active=true&page_size=100").then(setAmenityOptions).catch(() => setAmenityOptions([])); }, []);
  const [item, setItem] = useState<Development>(() =>
    existing
      ? structuredClone(existing)
      : {
          id: uid("dev"),
          slug: "",
          name: "",
          developerName: "",
          description: "",
          shortDescription: "",
          state: "",
          municipality: "",
          heroImage: "/casaviva-placeholder.svg",
          gallery: [],
          amenities: [],
          propertyIds: [],
          published: false,
          featured: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
  );
  const u = <K extends keyof Development>(k: K, v: Development[K]) =>
    setItem((x) => ({ ...x, [k]: v }));
  useEffect(() => {
    let cancelled = false;
    if (!item.municipalityId) {
      queueMicrotask(() => { if (!cancelled) { setLocalityOptions([]); setNeighborhoodOptions([]); } });
      return () => { cancelled = true; };
    }
    Promise.all([
      fetchAllPages<{ id: string; name: string }>(`/api/v1/admin/localities/?municipality=${item.municipalityId}&is_active=true&page_size=100`),
      fetchAllPages<{ id: string; name: string; postal_code?: string }>(`/api/v1/admin/neighborhoods/?municipality=${item.municipalityId}&is_active=true&page_size=100`),
    ]).then(([localities, neighborhoods]) => { if (!cancelled) { setLocalityOptions(localities); setNeighborhoodOptions(neighborhoods); } }).catch(() => { if (!cancelled) { setLocalityOptions([]); setNeighborhoodOptions([]); } });
    return () => { cancelled = true; };
  }, [item.municipalityId]);
  const save = async () => {
    if (
      !item.name ||
      !item.slug ||
      !item.developerId ||
      !item.stateId ||
      !item.municipalityId ||
      developments.some((d) => d.slug === item.slug && d.id !== item.id)
    ) {
      toast("Revisa el nombre, slug, desarrolladora y ubicación");
      return;
    }
    setSaving(true);
    try {
      await developmentService.save({ ...item, updatedAt: new Date().toISOString() });
      toast(existing ? "Cambios guardados" : "Desarrollo creado");
      router.push("/administracion/desarrollos");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };
  return (
    <AdminLayout title={existing ? "Editar desarrollo" : "Nuevo desarrollo"}>
      <AdminTitle title={item.name || "Nuevo desarrollo"} />
      <FormSection title="Información">
        <div className="admin-form-grid">
          <Text
            label="Nombre"
            value={item.name}
            onChange={(v) => {
              u("name", v);
              if (!existing) u("slug", slugify(v));
            }}
          />
          <Text
            label="Slug"
            value={item.slug}
            onChange={(v) => u("slug", slugify(v))}
          />
          <Select
            label="Desarrolladora"
            value={item.developerId || ""}
            onChange={(v) => { const developer = developers.find((x) => x.id === v); setItem((current) => ({ ...current, developerId: v || undefined, developerName: developer?.name || "" })); }}
            options={[["Selecciona", ""], ...developers.map((developer) => [developer.name, developer.id])]}
          />
          <Select
            label="Estado y municipio"
            value={item.municipalityId || ""}
            onChange={(v) => { const location = locations.find((x) => x.id === v); setItem((current) => ({ ...current, municipalityId: location?.id, stateId: location?.stateId, municipality: location?.name || "", state: location?.state || "", localityId: undefined, neighborhoodId: undefined })); }}
            options={[["Selecciona", ""], ...locations.map((location) => [`${location.name}, ${location.state}`, location.id])]}
          />
          <Select label="Localidad" value={item.localityId || ""} onChange={(value) => u("localityId", value || undefined)} options={[["Sin especificar", ""], ...localityOptions.map((option) => [option.name, option.id])]} />
          <Select label="Colonia" value={item.neighborhoodId || ""} onChange={(value) => { const option = neighborhoodOptions.find((candidate) => candidate.id === value); setItem((current) => ({ ...current, neighborhoodId: value || undefined, neighborhood: option?.name, postalCode: current.postalCode || option?.postal_code || undefined })); }} options={[["Sin especificar", ""], ...neighborhoodOptions.map((option) => [option.name, option.id])]} />
          <Text label="Dirección" value={item.address || ""} onChange={(value) => u("address", value)} />
          <Text label="Código postal" value={item.postalCode || ""} onChange={(value) => u("postalCode", value)} />
          <NumberField
            label="Latitud"
            value={item.latitude}
            onChange={(v) => u("latitude", v)}
            step="0.000001"
          />
          <NumberField
            label="Longitud"
            value={item.longitude}
            onChange={(v) => u("longitude", v)}
            step="0.000001"
          />
          <Area
            label="Descripción corta"
            value={item.shortDescription}
            onChange={(v) => u("shortDescription", v)}
          />
          <Area
            label="Descripción"
            value={item.description}
            onChange={(v) => u("description", v)}
          />
          <Toggle
            label="Publicado"
            checked={item.published}
            onChange={(v) => u("published", v)}
          />
          <Toggle
            label="Destacado"
            checked={item.featured}
            onChange={(v) => u("featured", v)}
          />
        </div>
      </FormSection>
      <FormSection title="Amenidades y multimedia">
        <div className="filter-checks">{amenityOptions.map((amenity) => <label className="check-chip" key={amenity.id}><input type="checkbox" checked={(item.amenityIds || []).includes(amenity.id)} onChange={(event) => setItem((current) => ({ ...current, amenityIds: event.target.checked ? [...(current.amenityIds || []), amenity.id] : (current.amenityIds || []).filter((id) => id !== amenity.id), amenities: event.target.checked ? [...current.amenities.filter((name) => name !== amenity.name), amenity.name] : current.amenities.filter((name) => name !== amenity.name) }))} /><span>{amenity.name}</span></label>)}</div>
        <MediaManager title={item.name} assets={(item.mediaAssets || []) as AdminMedia[]} onChange={(assets) => setItem((current) => ({ ...current, mediaAssets: assets, heroMediaId: assets.find((asset) => asset.role === "HERO")?.mediaId, heroImage: assets.find((asset) => asset.role === "HERO")?.url || "/casaviva-placeholder.svg" }))} />
      </FormSection>
      <FormSection title="Modelos asociados">
        <p className="muted">Las relaciones con modelos se administran desde la sección Modelos para conservar sus ofertas y precios independientes.</p>
        <Link className="button secondary" href="/administracion/modelos">Administrar modelos</Link>
      </FormSection>
      <div className="admin-form-actions">
        <Link className="button secondary" href="/administracion/desarrollos">
          Cancelar
        </Link>
        <button className="button" onClick={() => void save()} disabled={saving}>
          {saving ? "Guardando…" : "Guardar desarrollo"}
        </button>
      </div>
    </AdminLayout>
  );
}

export function AdminLocationsPage() {
  const { locations, deleteLocation } = useCasaViva();
  const [edit, setEdit] = useState<Location>();
  const [remove, setRemove] = useState<Location>();
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();
  return (
    <AdminLayout title="Ubicaciones">
      <AdminTitle title="Ubicaciones" />
      <button
        className="button"
        style={{ marginBottom: 18 }}
        onClick={() => setCreating(true)}
      >
        <Plus size={16} /> Nueva ubicación
      </button>
      <EntityTable
        heads={["Imagen", "Ubicación", "Estado", "Destacada", "Acciones"]}
      >
        {locations.filter((location) => location.contentId).map((l) => (
          <tr key={l.id}>
            <td>
              <Image src={l.heroImage} alt="" width={70} height={50} />
            </td>
            <td>
              <strong>{l.name}</strong>
            </td>
            <td>{l.state}</td>
            <td>{l.archivedAt ? "Archivada" : l.featured ? "Sí" : "No"}</td>
            <td>
              <div className="table-actions">
                <button title={l.archivedAt ? "Restaurar y editar" : "Editar"} onClick={() => setEdit(l)}>
                  <Pencil size={16} />
                </button>
                {!l.archivedAt && <button onClick={() => setRemove(l)}>
                  <Trash2 size={16} />
                </button>}
              </div>
            </td>
          </tr>
        ))}
      </EntityTable>
      {(edit || creating) && (
        <LocationInline
          item={edit}
          onClose={() => {
            setEdit(undefined);
            setCreating(false);
          }}
        />
      )}
      <ConfirmDialog
        open={!!remove}
        onClose={() => setRemove(undefined)}
        title="¿Eliminar esta ubicación?"
        description="La página editorial de esta ubicación dejará de estar disponible."
        onConfirm={async () => {
          if (remove) {
            try { await deleteLocation(remove.id); toast("Contenido de ubicación archivado"); }
            catch (error) { toast(error instanceof Error ? error.message : "No fue posible archivar la ubicación"); }
          }
        }}
      />
    </AdminLayout>
  );
}
function LocationInline({
  item,
  onClose,
}: {
  item?: Location;
  onClose: () => void;
}) {
  const [x, setX] = useState<Location>(() =>
    item
      ? structuredClone(item)
      : {
          id: "",
          slug: "",
          name: "",
          state: "",
          description: "",
          heroImage: "/casaviva-placeholder.svg",
          featured: false,
        },
  );
  const { locations, saveLocation } = useCasaViva();
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const u = <K extends keyof Location>(k: K, v: Location[K]) =>
    setX((a) => ({ ...a, [k]: v }));
  return (
    <div className="form-section" style={{ marginTop: 18 }}>
      <h3>{item ? "Editar ubicación" : "Nueva ubicación"}</h3>
      <div className="admin-form-grid">
        {item ? <label className="field"><span>Municipio</span><input value={`${x.name}, ${x.state}`} readOnly /></label> : <Select label="Municipio" value={x.id} onChange={(value) => { const location = locations.find((candidate) => candidate.id === value); setX((current) => ({ ...current, id: value, name: location?.name || "", state: location?.state || "", stateId: location?.stateId, slug: location ? slugify(location.name) : "" })); }} options={[["Selecciona", ""], ...locations.filter((location) => !location.contentId).map((location) => [`${location.name}, ${location.state}`, location.id])]} />}
        <Text
          label="Slug"
          value={x.slug}
          onChange={(v) => u("slug", slugify(v))}
        />
        <label className="field"><span>Imagen editorial</span><input type="file" accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; setUploading(true); setError(""); try { const form = new FormData(); form.append("file", file); form.append("media_type", "IMAGE"); form.append("alt_text", x.name); const asset = await apiFetch<{ id: string; url: string }>("/api/v1/admin/media/", { method: "POST", body: form }); setX((current) => ({ ...current, heroImage: asset.url, heroMediaId: asset.id })); } catch (uploadError) { setError(uploadError instanceof Error ? uploadError.message : "No fue posible cargar la imagen"); } finally { setUploading(false); } }} /><small>{uploading ? "Cargando imagen…" : "JPG, PNG o WebP"}</small></label>
        <NumberField
          label="Latitud"
          value={x.latitude}
          onChange={(v) => { if (v !== undefined) u("latitude", v); }}
          step="0.000001"
        />
        <NumberField
          label="Longitud"
          value={x.longitude}
          onChange={(v) => { if (v !== undefined) u("longitude", v); }}
          step="0.000001"
        />
        <Area
          label="Descripción"
          value={x.description}
          onChange={(v) => u("description", v)}
        />
        <Toggle
          label="Destacada"
          checked={x.featured}
          onChange={(v) => u("featured", v)}
        />
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions">
        <button className="button secondary" onClick={onClose}>
          Cancelar
        </button>
        <button
          className="button"
          disabled={saving || !x.id || !x.slug}
          onClick={async () => {
            setSaving(true); setError("");
            try { await saveLocation(x); toast(item ? "Cambios guardados" : "Ubicación creada"); onClose(); }
            catch (saveError) { setError(saveError instanceof Error ? saveError.message : "No fue posible guardar la ubicación"); }
            finally { setSaving(false); }
          }}
        >
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </div>
  );
}

export function AdminGuidesPage() {
  const { guides, deleteGuide } = useCasaViva();
  const [remove, setRemove] = useState<Guide>();
  const { toast } = useToast();
  return (
    <AdminLayout title="Guías">
      <AdminTitle title="Guías" action="Nueva guía" href="/administracion/guias/nueva" />
      <EntityTable
        heads={[
          "Imagen",
          "Artículo",
          "Categoría",
          "Publicada",
          "Fecha",
          "Acciones",
        ]}
      >
        {guides.map((g) => (
          <tr key={g.id}>
            <td>
              <Image src={g.heroImage} alt="" width={70} height={50} />
            </td>
            <td>
              <strong>{g.title}</strong>
            </td>
            <td>{g.category}</td>
            <td>{g.published ? "Sí" : "Borrador"}</td>
            <td>{formatDate(g.createdAt)}</td>
            <td>
              <div className="table-actions">
                <Link href={`/administracion/guias/${g.id}`}>
                  <Pencil size={16} />
                </Link>
                <button onClick={() => setRemove(g)}>
                  <Trash2 size={16} />
                </button>
              </div>
            </td>
          </tr>
        ))}
      </EntityTable>
      <ConfirmDialog
        open={!!remove}
        onClose={() => setRemove(undefined)}
        title="¿Eliminar esta guía?"
        description="La guía se archivará y dejará de estar disponible públicamente."
        onConfirm={async () => {
          if (remove) {
            try { await deleteGuide(remove.id); toast("Guía archivada"); setRemove(undefined); }
            catch (error) { toast(error instanceof Error ? error.message : "No fue posible archivar la guía"); }
          }
        }}
      />
    </AdminLayout>
  );
}
export function GuideFormPage({ id }: { id?: string }) {
  const { guides } = useCasaViva();
  const existing = guides.find((g) => g.id === id);
  const router = useRouter();
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [x, setX] = useState<Guide>(() =>
    existing
      ? structuredClone(existing)
      : {
          id: uid("guide"),
          slug: "",
          title: "",
          excerpt: "",
          content: "",
          category: "zonas",
          heroImage: "/casaviva-placeholder.svg",
          published: false,
          featured: false,
          createdAt: new Date().toISOString(),
          viewCount: 0,
        },
  );
  const u = <K extends keyof Guide>(k: K, v: Guide[K]) =>
    setX((a) => ({ ...a, [k]: v }));
  return (
    <AdminLayout title={existing ? "Editar guía" : "Nueva guía"}>
      <AdminTitle title={x.title || "Nueva guía"} />
      <FormSection title="Artículo">
        <div className="admin-form-grid">
          <Text
            label="Título"
            value={x.title}
            onChange={(v) => {
              u("title", v);
              if (!existing) u("slug", slugify(v));
            }}
          />
          <Text
            label="Slug"
            value={x.slug}
            onChange={(v) => u("slug", slugify(v))}
          />
          <Select
            label="Categoría"
            value={x.category}
            onChange={(v) => u("category", v as Guide["category"])}
            options={[
              ["Zonas", "zonas"],
              ["Comprar casa", "compra"],
              ["Hogar", "hogar"],
              ["Mercado", "mercado"],
            ]}
          />
          <label className="field"><span>Imagen principal</span><input type="file" accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; setUploading(true); try { const form = new FormData(); form.append("file", file); form.append("media_type", "IMAGE"); form.append("alt_text", x.title); const asset = await apiFetch<{ id: string; url: string }>("/api/v1/admin/media/", { method: "POST", body: form }); setX((current) => ({ ...current, heroImage: asset.url, heroMediaId: asset.id })); toast("Imagen cargada"); } catch (error) { toast(error instanceof Error ? error.message : "No fue posible cargar la imagen"); } finally { setUploading(false); } }} /><small>{uploading ? "Cargando imagen…" : "JPG, PNG o WebP"}</small></label>
          <Area
            label="Extracto"
            value={x.excerpt}
            onChange={(v) => u("excerpt", v)}
          />
          <label className="field full">
            <span>Contenido (Markdown simple)</span>
            <textarea
              style={{ minHeight: 360 }}
              value={x.content}
              onChange={(e) => u("content", e.target.value)}
            />
          </label>
          <Toggle
            label="Publicada"
            checked={x.published}
            onChange={(v) => u("published", v)}
          />
          <Toggle
            label="Destacada"
            checked={x.featured}
            onChange={(v) => u("featured", v)}
          />
        </div>
      </FormSection>
      <div className="admin-form-actions">
        <Link className="button secondary" href="/administracion/guias">
          Cancelar
        </Link>
        <button
          className="button"
          disabled={saving}
          onClick={async () => {
            if (
              !x.title ||
              !x.slug ||
              guides.some((g) => g.slug === x.slug && g.id !== x.id)
            ) {
              toast("Revisa el título y slug");
              return;
            }
            setSaving(true);
            try {
              await guideService.save(x);
              toast(existing ? "Cambios guardados" : "Guía creada");
              router.push("/administracion/guias");
            } catch (error) {
              toast(error instanceof Error ? error.message : "No fue posible guardar la guía");
            } finally { setSaving(false); }
          }}
        >
          {saving ? "Guardando…" : "Guardar guía"}
        </button>
      </div>
    </AdminLayout>
  );
}

export function AdminContentPage() {
  const { homeContent } = useCasaViva();
  const contentKey = `${homeContent.id || "new"}:${homeContent.version || 0}:${homeContent.featuredPropertyIds.join(",")}:${homeContent.featuredLocationIds.join(",")}:${homeContent.featuredDevelopmentIds.join(",")}`;
  return <AdminContentEditor key={contentKey} initialContent={homeContent} />;
}

function AdminContentEditor({ initialContent }: { initialContent: HomeContent }) {
  const { properties, locations, developments, setSiteSettings: updatePublicSiteSettings } = useCasaViva();
  const [x, setX] = useState<HomeContent>(() => structuredClone(initialContent));
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [siteSettings, setSiteSettings] = useState<SiteSettings>({ contact_email: "", facebook_url: "", instagram_url: "", tiktok_url: "" });
  const [contactLoaded, setContactLoaded] = useState(false);
  const [savingContact, setSavingContact] = useState(false);
  const { toast } = useToast();
  useEffect(() => {
    apiFetch<{ results: SiteSettings[] }>("/api/v1/admin/site-settings/?page_size=1")
      .then((page) => { if (page.results[0]) setSiteSettings(page.results[0]); })
      .catch((error) => toast(error instanceof Error ? error.message : "No fue posible cargar la información de contacto"))
      .finally(() => setContactLoaded(true));
  }, [toast]);
  const toggle = (
    key:
      | "featuredPropertyIds"
      | "featuredLocationIds"
      | "featuredDevelopmentIds",
    id: string,
  ) =>
    setX((a) => ({
      ...a,
      [key]: a[key].includes(id)
        ? a[key].filter((v) => v !== id)
        : [...a[key], id],
    }));
  return (
    <AdminLayout title="Inicio / Hero">
      <AdminTitle title="Contenido de inicio" />
      <FormSection title="Encabezado">
        <div className="admin-form-grid"><Text label="Antetítulo" value={x.heroEyebrow} onChange={(value) => setX((current) => ({ ...current, heroEyebrow: value }))} /><Text label="Título" value={x.heroTitle} onChange={(value) => setX((current) => ({ ...current, heroTitle: value }))} /></div>
      </FormSection>
      <FormSection title="Hero slides">
        <p className="muted">
          Activa y ordena las propiedades que encabezarán el inicio.
        </p>
        <button className="button secondary" type="button" disabled={!properties.length} onClick={() => { const property = properties.find((candidate) => !x.heroSlides.some((slide) => slide.propertyId === candidate.id)) || properties[0]; if (!property) return; setX((current) => ({ ...current, heroSlides: [...current.heroSlides, { id: `new-${Date.now()}`, propertyId: property.id, eyebrow: property.developmentName || property.municipality || "Propiedad", title: property.title, subtitle: property.shortDescription, order: current.heroSlides.length, active: true }] })); }}>Añadir slide</button>
        {x.heroSlides.map((s, i) => (
          <div className="admin-list-row" key={s.id}>
            <select
              value={s.propertyId}
              onChange={(e) =>
                setX((a) => ({
                  ...a,
                  heroSlides: a.heroSlides.map((v, n) =>
                    n === i ? { ...v, propertyId: e.target.value } : v,
                  ),
                }))
              }
            >
              {properties.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            <input
              value={s.title}
              onChange={(e) =>
                setX((a) => ({
                  ...a,
                  heroSlides: a.heroSlides.map((v, n) =>
                    n === i ? { ...v, title: e.target.value } : v,
                  ),
                }))
              }
            />
            <input aria-label="Subtítulo del slide" value={s.subtitle} onChange={(e) => setX((a) => ({ ...a, heroSlides: a.heroSlides.map((v, n) => n === i ? { ...v, subtitle: e.target.value } : v) }))} />
            <input
              type="number"
              value={s.order}
              onChange={(e) =>
                setX((a) => ({
                  ...a,
                  heroSlides: a.heroSlides.map((v, n) =>
                    n === i ? { ...v, order: Number(e.target.value) } : v,
                  ),
                }))
              }
            />
            <label>
              <input
                type="checkbox"
                checked={s.active}
                onChange={(e) =>
                  setX((a) => ({
                    ...a,
                    heroSlides: a.heroSlides.map((v, n) =>
                      n === i ? { ...v, active: e.target.checked } : v,
                    ),
                  }))
                }
              />{" "}
              Activo
            </label>
            <button type="button" className="icon-button" aria-label="Quitar slide" onClick={() => setX((current) => ({ ...current, heroSlides: current.heroSlides.filter((_, index) => index !== i) }))}><Trash2 size={16} /></button>
          </div>
        ))}
      </FormSection>
      <FormSection title="Propiedades destacadas">
        <PickList
          items={properties.map((p) => [p.id, p.title])}
          selected={x.featuredPropertyIds}
          onToggle={(id) => toggle("featuredPropertyIds", id)}
        />
      </FormSection>
      <FormSection title="Ubicaciones destacadas">
        <PickList
          items={locations.map((l) => [l.id, l.name])}
          selected={x.featuredLocationIds}
          onToggle={(id) => toggle("featuredLocationIds", id)}
        />
      </FormSection>
      <FormSection title="Desarrollos destacados">
        <PickList
          items={developments.map((d) => [d.id, d.name])}
          selected={x.featuredDevelopmentIds}
          onToggle={(id) => toggle("featuredDevelopmentIds", id)}
        />
      </FormSection>
      <FormSection title="Bloque editorial">
        <div className="admin-form-grid">
          <Area
            label="Titular"
            value={x.editorialTitle}
            onChange={(v) => setX((a) => ({ ...a, editorialTitle: v }))}
          />
          <label className="field"><span>Imagen editorial</span><input type="file" accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; setUploading(true); try { const form = new FormData(); form.append("file", file); form.append("media_type", "IMAGE"); form.append("alt_text", x.editorialTitle); const asset = await apiFetch<{ id: string; url: string }>("/api/v1/admin/media/", { method: "POST", body: form }); setX((current) => ({ ...current, editorialImage: asset.url, editorialMediaId: asset.id })); toast("Imagen cargada"); } catch (error) { toast(error instanceof Error ? error.message : "No fue posible cargar la imagen"); } finally { setUploading(false); } }} /><small>{uploading ? "Cargando imagen…" : "JPG, PNG o WebP"}</small></label>
          <Area
            label="Descripción"
            value={x.editorialBody}
            onChange={(v) => setX((a) => ({ ...a, editorialBody: v }))}
          />
        </div>
      </FormSection>
      <div className="admin-form-actions">
        <button
          className="button"
          disabled={saving}
          onClick={async () => {
            setSaving(true);
            try { await homeContentService.save(x); toast("Cambios guardados"); }
            catch (error) { toast(error instanceof Error ? error.message : "Error al guardar"); }
            finally { setSaving(false); }
          }}
        >
          {saving ? "Guardando…" : "Guardar contenido"}
        </button>
      </div>
      <FormSection title="Información de contacto">
        <p className="muted">Estos datos se muestran en el pie del sitio y en Contacto.</p>
        {contactLoaded ? <div className="admin-form-grid">
          <Text label="Correo" value={siteSettings.contact_email} onChange={(value) => setSiteSettings((current) => ({ ...current, contact_email: value }))} />
          <Text label="Facebook" value={siteSettings.facebook_url || ""} onChange={(value) => setSiteSettings((current) => ({ ...current, facebook_url: value || null }))} />
          <Text label="Instagram" value={siteSettings.instagram_url || ""} onChange={(value) => setSiteSettings((current) => ({ ...current, instagram_url: value || null }))} />
          <Text label="TikTok" value={siteSettings.tiktok_url || ""} onChange={(value) => setSiteSettings((current) => ({ ...current, tiktok_url: value || null }))} />
        </div> : <p className="muted">Cargando información de contacto…</p>}
        <div className="admin-form-actions"><button className="button" disabled={savingContact || !siteSettings.contact_email} onClick={async () => {
          setSavingContact(true);
          try {
            const exists = Boolean(siteSettings.id);
            const saved = await apiFetch<SiteSettings>(exists ? `/api/v1/admin/site-settings/${siteSettings.id}/` : "/api/v1/admin/site-settings/", { method: exists ? "PATCH" : "POST", body: JSON.stringify({ key: "main", contact_email: siteSettings.contact_email, facebook_url: siteSettings.facebook_url || null, instagram_url: siteSettings.instagram_url || null, tiktok_url: siteSettings.tiktok_url || null, ...(exists ? { version: siteSettings.version } : {}) }) });
            setSiteSettings(saved); updatePublicSiteSettings(saved); toast("Información de contacto guardada");
          } catch (error) { toast(error instanceof Error ? error.message : "No fue posible guardar"); }
          finally { setSavingContact(false); }
        }}>{savingContact ? "Guardando…" : "Guardar información de contacto"}</button></div>
      </FormSection>
    </AdminLayout>
  );
}
function PickList({
  items,
  selected,
  onToggle,
}: {
  items: string[][];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="filter-checks">
      {items.map(([id, label]) => (
        <label className="check-chip" key={id}>
          <input
            type="checkbox"
            checked={selected.includes(id)}
            onChange={() => onToggle(id)}
          />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}

export function AdminInquiriesPage() {
  const { inquiries, properties, setInquiryStatus } = useCasaViva();
  return (
    <AdminLayout title="Consultas">
      <AdminTitle title="Consultas" />
      <EntityTable
        heads={[
          "Fecha",
          "Nombre",
          "Teléfono",
          "Correo",
          "Propiedad",
          "Mensaje",
          "Estado",
        ]}
      >
        {inquiries.map((i) => (
          <tr key={i.id}>
            <td>{formatDate(i.createdAt)}</td>
            <td>
              <strong>{i.name}</strong>
            </td>
            <td>{i.phone || "—"}</td>
            <td>{i.email}</td>
            <td>
              {properties.find((p) => p.id === i.propertyId)?.title ||
                i.subject ||
                "Contacto"}
            </td>
            <td style={{ maxWidth: 300 }}>{i.message}</td>
            <td>
              <select
                value={i.status}
                onChange={(e) =>
                  setInquiryStatus(i.id, e.target.value as typeof i.status)
                }
              >
                <option value="new">Nueva</option>
                <option value="viewed">Vista</option>
                <option value="attended">Atendida</option>
              </select>
            </td>
          </tr>
        ))}
      </EntityTable>
    </AdminLayout>
  );
}

function statusLabel(s: string) {
  return s === "new" ? "Nueva" : s === "viewed" ? "Vista" : "Atendida";
}
function EntityTable({
  heads,
  children,
}: {
  heads: string[];
  children: ReactNode;
}) {
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            {heads.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
export function AdminTable(props: { heads: string[]; children: ReactNode }) {
  return <EntityTable {...props} />;
}
export function AdminToolbar({ children }: { children: ReactNode }) {
  return <div className="admin-toolbar">{children}</div>;
}
export function AdminPagination() {
  return (
    <div className="admin-toolbar">
      <span>Página 1 de 1</span>
    </div>
  );
}
export function FormSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="form-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
function Text({
  label,
  value,
  onChange,
}: {
  label: string;
  value?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value || ""} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}
function NumberField({
  label,
  value,
  onChange,
  step = "1",
}: {
  label: string;
  value?: number;
  onChange: (v?: number) => void;
  step?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={value || ""}
        onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
      />
    </label>
  );
}
function Area({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}
function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[][];
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([l, v]) => (
          <option value={v} key={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
export function PublishToggle({
  label = "Publicado",
  checked,
  onChange,
}: {
  label?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return <Toggle label={label} checked={checked} onChange={onChange} />;
}
function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="publish-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}
export const PropertyForm = PropertyFormPage;
export const DevelopmentForm = DevelopmentFormPage;
export const LocationForm = LocationInline;
export const GuideForm = GuideFormPage;
