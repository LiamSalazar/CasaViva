"use client";
import { useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/admin";
import { apiFetch, fetchAllPages } from "@/services/api";

type Kind = "privacy-notices" | "terms-of-use";
type Document = { id: string; version: string; title: string; body: string; status: string; content_hash: string; effective_at?: string };
export function LegalAdminPage() {
  const [kind, setKind] = useState<Kind>("privacy-notices"); const [items, setItems] = useState<Document[]>([]); const [draft, setDraft] = useState<Partial<Document>>({}); const [error, setError] = useState("");
  const load = useCallback(() => fetchAllPages<Document>(`/api/v1/admin/${kind}/?page_size=100`).then(setItems).catch((e) => setError(e.message)), [kind]);
  useEffect(() => { void load(); }, [load]);
  const save = async () => { setError(""); try { await apiFetch(draft.id ? `/api/v1/admin/${kind}/${draft.id}/` : `/api/v1/admin/${kind}/`, { method: draft.id ? "PATCH" : "POST", body: JSON.stringify({ version: draft.version, title: draft.title, body: draft.body, effective_at: draft.effective_at || null }) }); setDraft({}); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible guardar."); } };
  const publish = async (item: Document) => { try { await apiFetch(`/api/v1/admin/${kind}/${item.id}/publish/`, { method: "POST", body: "{}" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No fue posible publicar."); } };
  return <AdminLayout title="Contenido legal"><div className="admin-panel"><h1>Legal</h1><label className="field"><span>Documento</span><select value={kind} onChange={(e) => { setKind(e.target.value as Kind); setDraft({}); }}><option value="privacy-notices">Aviso de Privacidad</option><option value="terms-of-use">Términos de Uso</option></select></label>{error && <p className="form-error">{error}</p>}<h2>{draft.id ? "Editar borrador" : "Nuevo borrador"}</h2><label className="field"><span>Versión</span><input value={draft.version || ""} onChange={(e) => setDraft({ ...draft, version: e.target.value })} /></label><label className="field"><span>Título</span><input value={draft.title || ""} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label><label className="field"><span>Contenido Markdown</span><textarea rows={18} value={draft.body || ""} onChange={(e) => setDraft({ ...draft, body: e.target.value })} /></label><button className="button" onClick={() => void save()}>Guardar borrador</button><h2>Historial</h2>{items.map((item) => <article key={item.id} className="admin-list-row"><div><strong>{item.version} · {item.title}</strong><small>{item.status} · {item.content_hash || "sin hash"}</small></div><div className="table-actions"><button onClick={() => setDraft(item)}>Previsualizar / editar</button>{item.status === "DRAFT" && <button onClick={() => void publish(item)}>Publicar</button>}</div></article>)}</div></AdminLayout>;
}
