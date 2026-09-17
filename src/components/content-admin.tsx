"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AdminLayout } from "@/components/admin";
import { useToast } from "@/components/ui";
import { apiFetch } from "@/services/api";
import type { AboutContent, SiteSettings } from "@/types";

type MediaAsset = { id: string; url: string; original_filename: string; alt_text?: string | null };
const emptyAbout: AboutContent = { key: "main", eyebrow: "", hero_title: "", main_title: "", main_body: "", what_we_do_title: "", what_we_do_body: "", how_we_work_title: "", how_we_work_body: "", vision_title: "", vision_body: "", cta_label: "", cta_url: "" };

function TextField({ label, value, onChange, area = false, disabled = false }: { label: string; value: string; onChange: (value: string) => void; area?: boolean; disabled?: boolean }) {
  return <label className="field"><span>{label}</span>{area ? <textarea rows={5} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} /> : <input disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} />}</label>;
}

export function ContentIndexPage() {
  return <AdminLayout title="Contenido"><div className="admin-title"><div><span className="eyebrow">Administración</span><h2>Contenido público</h2></div></div><div className="admin-card-grid"><Link className="admin-panel" href="/administracion/contenido/inicio"><h3>Inicio</h3><p>Hero, destacados y bloque editorial.</p></Link><Link className="admin-panel" href="/administracion/contenido/nosotros"><h3>Nosotros</h3><p>Historia, forma de trabajo, visión e imagen.</p></Link><Link className="admin-panel" href="/administracion/contenido/identidad"><h3>Identidad y contacto</h3><p>Responsable, rol comercial y canales públicos.</p></Link></div></AdminLayout>;
}

export function AdminAboutPage() {
  const [value, setValue] = useState<AboutContent>(emptyAbout);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  useEffect(() => { Promise.all([apiFetch<{ results: AboutContent[] }>("/api/v1/admin/about/?page_size=1"), apiFetch<{ results: MediaAsset[] }>("/api/v1/admin/media/")]).then(([about, assets]) => { if (about.results[0]) setValue(about.results[0]); setMedia(assets.results); }).catch((error) => toast(error instanceof Error ? error.message : "No fue posible cargar Nosotros")); }, [toast]);
  const set = (key: keyof AboutContent, next: string | null) => setValue((current) => ({ ...current, [key]: next }));
  const upload = async (file?: File) => { if (!file) return; setBusy(true); try { const body = new FormData(); body.append("file", file); body.append("media_type", "IMAGE"); body.append("alt_text", value.hero_title); const asset = await apiFetch<MediaAsset>("/api/v1/admin/media/", { method: "POST", body }); setMedia((items) => [asset, ...items]); setValue((current) => ({ ...current, hero_media: asset.id, hero_media_url: asset.url })); toast("Imagen cargada"); } catch (error) { toast(error instanceof Error ? error.message : "No fue posible cargar la imagen"); } finally { setBusy(false); } };
  const save = async () => { setBusy(true); try { const saved = await apiFetch<AboutContent>(value.id ? `/api/v1/admin/about/${value.id}/` : "/api/v1/admin/about/", { method: value.id ? "PATCH" : "POST", body: JSON.stringify(value) }); setValue(saved); toast("Contenido de Nosotros guardado"); } catch (error) { toast(error instanceof Error ? error.message : "No fue posible guardar"); } finally { setBusy(false); } };
  return <AdminLayout title="Contenido / Nosotros"><div className="admin-title"><div><span className="eyebrow">Contenido</span><h2>Nosotros</h2></div><Link className="button secondary" href="/nosotros" target="_blank">Previsualizar</Link></div><section className="admin-panel"><div className="admin-form-grid"><TextField label="Antetítulo" value={value.eyebrow} onChange={(v) => set("eyebrow", v)} /><TextField label="Título principal" value={value.hero_title} onChange={(v) => set("hero_title", v)} /><TextField label="Título del bloque principal" value={value.main_title} onChange={(v) => set("main_title", v)} /><TextField label="Texto principal" area value={value.main_body} onChange={(v) => set("main_body", v)} /><TextField label="Qué hacemos — título" value={value.what_we_do_title} onChange={(v) => set("what_we_do_title", v)} /><TextField label="Qué hacemos — texto" area value={value.what_we_do_body} onChange={(v) => set("what_we_do_body", v)} /><TextField label="Cómo trabajamos — título" value={value.how_we_work_title} onChange={(v) => set("how_we_work_title", v)} /><TextField label="Cómo trabajamos — texto" area value={value.how_we_work_body} onChange={(v) => set("how_we_work_body", v)} /><TextField label="Visión — título" value={value.vision_title} onChange={(v) => set("vision_title", v)} /><TextField label="Visión — texto" area value={value.vision_body} onChange={(v) => set("vision_body", v)} /><TextField label="CTA — etiqueta" value={value.cta_label} onChange={(v) => set("cta_label", v)} /><TextField label="CTA — URL" value={value.cta_url} onChange={(v) => set("cta_url", v)} /></div><label className="field"><span>Imagen principal existente</span><select value={value.hero_media || ""} onChange={(event) => { const asset = media.find((item) => item.id === event.target.value); setValue((current) => ({ ...current, hero_media: event.target.value || null, hero_media_url: asset?.url || null })); }}><option value="">Sin imagen</option>{media.map((asset) => <option value={asset.id} key={asset.id}>{asset.original_filename}</option>)}</select></label><label className="field"><span>Subir nueva imagen</span><input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(event) => void upload(event.target.files?.[0])} /></label>{value.hero_media_url && <Image src={value.hero_media_url} alt="Previsualización" width={480} height={280} style={{ width: "100%", height: "auto" }} />}<div className="admin-form-actions"><button className="button" disabled={busy} onClick={() => void save()}>{busy ? "Guardando…" : "Guardar Nosotros"}</button></div></section></AdminLayout>;
}

export function AdminIdentityPage() {
  const [value, setValue] = useState<SiteSettings>({ contact_email: "" });
  const [canEditLegal, setCanEditLegal] = useState(false);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  useEffect(() => { Promise.all([apiFetch<{ results: SiteSettings[] }>("/api/v1/admin/site-settings/?page_size=1"), apiFetch<{ role?: string; effective_permissions?: string[] }>("/api/v1/auth/me/")]).then(([settings, session]) => { if (settings.results[0]) setValue(settings.results[0]); setCanEditLegal(session.role === "Owner" || Boolean(session.effective_permissions?.includes("content.manage_legal_identity"))); }).catch((error) => toast(error instanceof Error ? error.message : "No fue posible cargar identidad")); }, [toast]);
  const set = (key: keyof SiteSettings, next: string | number | null) => setValue((current) => ({ ...current, [key]: next }));
  const save = async () => {
    setBusy(true);
    try {
      const payload = canEditLegal
        ? { ...value, key: "main" }
        : { key: "main", version: value.version, contact_email: value.contact_email };
      const saved = await apiFetch<SiteSettings>(value.id ? `/api/v1/admin/site-settings/${value.id}/` : "/api/v1/admin/site-settings/", {
        method: value.id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setValue(saved);
      toast("Identidad y contacto guardados");
    } catch (error) {
      toast(error instanceof Error ? error.message : "No fue posible guardar");
    } finally {
      setBusy(false);
    }
  };
  return <AdminLayout title="Contenido / Identidad y contacto"><div className="admin-title"><div><span className="eyebrow">Contenido</span><h2>Identidad y contacto</h2></div></div><section className="admin-panel">{!canEditLegal && <p className="form-error">Tu rol puede consultar estos datos, pero no modificar la identidad legal.</p>}<div className="admin-form-grid"><TextField label="Marca" disabled={!canEditLegal} value={value.brand_name || ""} onChange={(v) => set("brand_name", v)} /><TextField label="Responsable" disabled={!canEditLegal} value={value.responsible_name || ""} onChange={(v) => set("responsible_name", v)} /><TextField label="Tipo de responsable" disabled={!canEditLegal} value={value.operator_type || "PERSONA_FISICA"} onChange={(v) => set("operator_type", v)} /><TextField label="Rol comercial" disabled={!canEditLegal} value={value.commercial_role || "EXTERNAL_PROMOTER"} onChange={(v) => set("commercial_role", v)} /><TextField label="Descripción del rol" disabled={!canEditLegal} value={value.commercial_role_display || ""} onChange={(v) => set("commercial_role_display", v)} /><TextField label="Domicilio del responsable" area disabled={!canEditLegal} value={value.responsible_address || ""} onChange={(v) => set("responsible_address", v)} /><TextField label="Correo de privacidad" disabled={!canEditLegal} value={value.privacy_email || ""} onChange={(v) => set("privacy_email", v)} /><TextField label="Correo de contacto" value={value.contact_email || ""} onChange={(v) => set("contact_email", v)} /><TextField label="Correo de quejas" disabled={!canEditLegal} value={value.complaints_email || ""} onChange={(v) => set("complaints_email", v)} /><TextField label="Teléfono" disabled={!canEditLegal} value={value.contact_phone || ""} onChange={(v) => set("contact_phone", v)} /><label className="field"><span>Días para advertir verificación vencida</span><input type="number" disabled={!canEditLegal} value={value.verification_warning_days ?? ""} onChange={(event) => set("verification_warning_days", event.target.value ? Number(event.target.value) : null)} /></label></div><div className="admin-form-actions"><button className="button" disabled={busy} onClick={() => void save()}>{busy ? "Guardando…" : "Guardar identidad y contacto"}</button></div></section></AdminLayout>;
}
