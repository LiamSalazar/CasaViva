"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import {
  DevelopmentCard,
  DynamicMapView,
  PropertyGridCard,
} from "@/components/property";
import { EmptyState, Footer, PublicHeader, useToast } from "@/components/ui";
import { formatDate, formatLocation, uid } from "@/lib/utils";
import { inquiryService, useCasaViva } from "@/services";
import { api, apiFetch } from "@/services/api";
import type { Development, Guide, Inquiry, Property } from "@/types";
import { ensureCurrentAnalyticsIdentity, trackEvent } from "@/components/analytics-provider";
import { antibotIsEnabled, TurnstileWidget } from "@/components/turnstile-widget";

export function DevelopmentsPage() {
  const { developments, properties } = useCasaViva();
  const list = developments.filter((d) => d.published);
  const heroImage = list.find((development) => development.heroImage)?.heroImage;
  return (
    <>
      <PublicHeader />
      <div
        className={`page-hero ${heroImage ? "" : "no-media"}`}
        style={heroImage ? { backgroundImage: `url(${heroImage})` } : undefined}
      >
        <div>
          <span className="eyebrow">Comunidades para descubrir</span>
          <h1>Desarrollos</h1>
          <p>
            Proyectos residenciales presentados con claridad, desde sus espacios
            hasta sus modelos disponibles.
          </p>
        </div>
      </div>
      <main className="container section">
        <div className="development-grid">
          {list.map((d) => (
            <DevelopmentCard
              development={d}
              properties={properties}
              key={d.id}
            />
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
export function DevelopmentDetailPage({ slug }: { slug: string }) {
  const [developmentResult, setDevelopmentResult] = useState<{ slug: string; item: Development | null } | null>(null);
  const [inventoryResult, setInventoryResult] = useState<{ developmentId: string; items: Property[] } | null>(null);
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    api.developmentBySlug(slug)
      .then((item) => { if (active) setDevelopmentResult({ slug, item }); })
      .catch(() => { if (active) setDevelopmentResult({ slug, item: null }); });
    return () => { active = false; };
  }, [slug]);
  const development = developmentResult?.slug === slug ? developmentResult.item : null;
  const developmentLoaded = developmentResult?.slug === slug;
  useEffect(() => {
    let active = true;
    if (!development) return () => { active = false; };
    api.publicListingsAll(`development=${encodeURIComponent(development.id)}`)
      .then((items) => { if (active) setInventoryResult({ developmentId: development.id, items }); })
      .catch(() => { if (active) setInventoryResult({ developmentId: development.id, items: [] }); });
    return () => { active = false; };
  }, [development]);
  if (!developmentLoaded)
    return (
      <>
        <PublicHeader />
        <main className="narrow section"><div className="skeleton development-detail-loading" aria-label="Cargando desarrollo" /></main>
        <Footer />
      </>
    );
  if (!development)
    return (
      <>
        <PublicHeader />
        <EmptyState
          title="Desarrollo no disponible"
          body="La dirección puede haber cambiado."
          href="/desarrollos"
        />
        <Footer />
      </>
    );
  const d = development;
  const models = inventoryResult?.developmentId === d.id ? inventoryResult.items : [];
  const inventoryLoaded = inventoryResult?.developmentId === d.id;
  const gallery = d.gallery ?? [];
  const amenities = d.amenities ?? [];
  const mappableModels = models.filter((model) => Number.isFinite(model.latitude) && Number.isFinite(model.longitude));
  const moveGallery = (delta: number) => setGalleryIndex((current) =>
    current === null ? 0 : (current + delta + gallery.length) % gallery.length,
  );
  return (
    <>
      <PublicHeader />
      <div
        className={`page-hero development-hero ${d.heroImage ? "" : "no-media"}`}
        style={d.heroImage ? { backgroundImage: `url(${d.heroImage})` } : undefined}
      >
        <div>
          <span className="eyebrow">{d.developerName}</span>
          <h1>{d.name}</h1>
          <p>{formatLocation(d.municipality, d.state)}</p>
        </div>
      </div>
      <main className="container">
        <section className="section">
          <div className="section-heading">
            <span className="eyebrow">Sobre el desarrollo</span>
            <h2>Una comunidad para el ritmo de todos los días</h2>
            <p className="editorial-body">{d.description}</p>
          </div>
        </section>
        {gallery.length > 0 && <section className="section-tight">
          <div className="inline-heading">
            <h2>Galería</h2>
          </div>
          <div className="secondary-gallery">
            {gallery.slice(0, 5).map((src, i) => (
              <button key={src + i} type="button" onClick={() => setGalleryIndex(i)} aria-label={`Abrir foto ${i + 1} de ${d.name}`}>
                <Image
                  src={src}
                  alt={`${d.name}, foto ${i + 1}`}
                  fill
                  sizes="50vw"
                />
              </button>
            ))}
          </div>
          {galleryIndex !== null && (
            <div className="fullscreen-gallery" role="dialog" aria-modal="true" aria-label={`Galería de ${d.name}`}>
              <header>
                <span>Foto {galleryIndex + 1} / {gallery.length}</span>
                <button className="icon-button" type="button" onClick={() => setGalleryIndex(null)} aria-label="Cerrar"><X /></button>
              </header>
              <div className="fullscreen-image">
                <Image src={gallery[galleryIndex]} alt={`${d.name}, foto ${galleryIndex + 1}`} fill sizes="100vw" />
              </div>
              {gallery.length > 1 && <>
                <button className="gallery-nav prev" type="button" onClick={() => moveGallery(-1)} aria-label="Anterior"><ChevronLeft /></button>
                <button className="gallery-nav next" type="button" onClick={() => moveGallery(1)} aria-label="Siguiente"><ChevronRight /></button>
              </>}
            </div>
          )}
        </section>}
        {amenities.length > 0 && <section className="section">
          <div className="section-heading">
            <span className="eyebrow">Amenidades</span>
            <h2>Espacios que acompañan la vida</h2>
          </div>
          <div className="amenity-chips">
            {amenities.map((a) => (
              <span className="amenity-chip" key={a}>
                {a}
              </span>
            ))}
          </div>
        </section>}
        <section className="section-tight">
          <div className="inline-heading">
            <h2>Ubicación</h2>
          </div>
          {inventoryLoaded ? (
            mappableModels.length ? <DynamicMapView properties={mappableModels} /> : <div className="map-shell map-unavailable"><span>Ubicación sin coordenadas disponibles.</span></div>
          ) : <div className="map-shell skeleton" />}
        </section>
        <section className="section">
          <div className="inline-heading">
            <h2>Modelos disponibles</h2>
            <span>{models.length} opciones</span>
          </div>
          {models.length ? (
            <div className="property-grid">
              {models.map((p) => (
                <PropertyGridCard property={p} key={p.id} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="Próximamente nuevos modelos"
              body="Este desarrollo no tiene modelos publicados por el momento."
            />
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}

export function LocationPage({ slug }: { slug: string }) {
  const { locations, properties, developments, guides } = useCasaViva();
  const location = locations.find((l) => l.slug === slug);
  const [locationProperties, setLocationProperties] = useState<Property[]>([]);
  const [inventoryLoaded, setInventoryLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    if (!location) return () => { active = false; };
    api.publicListingsAll(`municipality=${encodeURIComponent(location.name)}`)
      .then((items) => { if (active) { setLocationProperties(items); setInventoryLoaded(true); } })
      .catch(() => { if (active) { setLocationProperties([]); setInventoryLoaded(true); } });
    return () => { active = false; };
  }, [location]);
  if (!location)
    return (
      <>
        <PublicHeader />
        <EmptyState
          title="Ubicación no encontrada"
          body="Explora otras zonas disponibles."
          href="/propiedades"
        />
        <Footer />
      </>
    );
  const props = locationProperties;
  const devs = developments.filter(
    (d) => d.municipality === location.name && d.published,
  );
  const related = guides
    .filter(
      (g) =>
        g.published &&
        (g.title.toLowerCase().includes(location.name.toLowerCase()) ||
          g.category === "zonas"),
    )
    .slice(0, 3);
  return (
    <>
      <PublicHeader />
      <div
        className={`page-hero development-hero ${location.heroImage ? "" : "no-media"}`}
        style={location.heroImage ? { backgroundImage: `url(${location.heroImage})` } : undefined}
      >
        <div>
          <span className="eyebrow">{location.state}</span>
          <h1>Vivir en {location.name}</h1>
        </div>
      </div>
      <main className="container">
        <section className="section">
          <div className="section-heading">
            <span className="eyebrow">La zona</span>
            <h2>Una mirada clara a {location.name}</h2>
            <p className="editorial-body">{location.description}</p>
          </div>
          {inventoryLoaded ? <DynamicMapView properties={props} /> : <div className="map-shell skeleton" />}
        </section>
        {devs.length > 0 && (
          <section className="section">
            <div className="inline-heading">
              <h2>Desarrollos</h2>
            </div>
            <div className="development-grid">
              {devs.map((d) => (
                <DevelopmentCard
                  development={d}
                  properties={properties}
                  key={d.id}
                />
              ))}
            </div>
          </section>
        )}
        <section className="section">
          <div className="inline-heading">
            <h2>Propiedades en {location.name}</h2>
            <Link
              className="text-link"
              href={`/propiedades?municipality=${location.slug}`}
            >
              Ver todas <ChevronRight />
            </Link>
          </div>
          <div className="property-grid">
            {props.map((p) => (
              <PropertyGridCard property={p} key={p.id} />
            ))}
          </div>
        </section>
        <section className="section">
          <div className="inline-heading">
            <h2>Guías relacionadas</h2>
          </div>
          <div className="guide-grid">
            {related.map((g) => (
              <GuideCard guide={g} key={g.id} />
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

const guideCategories: { value: Guide["category"]; label: string }[] = [
  { value: "zonas", label: "Zonas" },
  { value: "compra", label: "Comprar casa" },
  { value: "hogar", label: "Hogar" },
  { value: "mercado", label: "Mercado" },
];
export function GuidesPage() {
  const { guides } = useCasaViva();
  const list = guides.filter((g) => g.published);
  const [category, setCategory] = useState<Guide["category"] | "all">("all");
  const featured = list.find((g) => g.featured) || list[0];
  const filtered =
    category === "all" ? list : list.filter((g) => g.category === category);
  return (
    <>
      <PublicHeader />
      <main>
        <section className="container section">
          <span className="eyebrow">Ideas para decidir mejor</span>
          <h1>Guías CasaViva</h1>
          <div className="choice-grid">
            {" "}
            <button
              className={`choice ${category === "all" ? "active" : ""}`}
              onClick={() => setCategory("all")}
            >
              Todas
            </button>
            {guideCategories.map((c) => (
              <button
                className={`choice ${category === c.value ? "active" : ""}`}
                onClick={() => setCategory(c.value)}
                key={c.value}
              >
                {c.label}
              </button>
            ))}
          </div>
        </section>
        {featured && (
          <Link href={`/guias/${featured.slug}`} className="editorial-feature">
            <Image
              src={featured.heroImage}
              alt={featured.title}
              fill
              sizes="100vw"
            />
            <div className="editorial-feature-content">
              <span className="eyebrow">
                Artículo destacado ·{" "}
                {
                  guideCategories.find((c) => c.value === featured.category)
                    ?.label
                }
              </span>
              <h2>{featured.title}</h2>
              <p>{featured.excerpt}</p>
              <span className="button secondary">Leer guía</span>
            </div>
          </Link>
        )}
        <section className="container section">
          <div className="inline-heading">
            <h2>Últimos artículos</h2>
          </div>
          <div className="guide-grid">
            {filtered.map((g) => (
              <GuideCard guide={g} key={g.id} />
            ))}
          </div>
          <div className="inline-heading" style={{ marginTop: 100 }}>
            <h2>Más leídos</h2>
          </div>
          <div className="guide-grid">
            {[...list]
              .sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0))
              .slice(0, 3)
              .map((g) => (
                <GuideCard guide={g} key={g.id} />
              ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
export function GuideCard({ guide }: { guide: Guide }) {
  return (
    <Link href={`/guias/${guide.slug}`} className="guide-card">
      <Image src={guide.heroImage} alt={guide.title} width={800} height={590} />
      <span className="eyebrow">
        {guideCategories.find((c) => c.value === guide.category)?.label}
      </span>
      <h3>{guide.title}</h3>
      <p>{guide.excerpt}</p>
    </Link>
  );
}
export function GuideDetailPage({ slug }: { slug: string }) {
  const { guides, properties } = useCasaViva();
  const [guide, setGuide] = useState<Guide | null | undefined>(() => guides.find((g) => g.slug === slug && g.published));
  useEffect(() => {
    let active = true;
    api.guide(slug).then((value) => { if (active) setGuide(value); }).catch(() => { if (active) setGuide(null); });
    return () => { active = false; };
  }, [slug]);
  if (guide === undefined) return <><PublicHeader /><main className="container section"><p>Cargando guía…</p></main><Footer /></>;
  if (!guide)
    return (
      <>
        <PublicHeader />
        <EmptyState
          title="Guía no encontrada"
          body="Puedes explorar los artículos más recientes."
          href="/guias"
        />
        <Footer />
      </>
    );
  return (
    <>
      <PublicHeader />
      <article>
        <div className="narrow article-head">
          <span className="eyebrow">
            {guideCategories.find((c) => c.value === guide.category)?.label}
          </span>
          <h1>{guide.title}</h1>
          <p>{formatDate(guide.createdAt)} · CasaViva</p>
        </div>
        <div className="article-hero">
          <Image
            src={guide.heroImage}
            alt={guide.title}
            width={2000}
            height={1200}
          />
        </div>
        <div className="narrow section prose">
          <MarkdownLite content={guide.content} />
        </div>
      </article>
      <section className="container section">
        <div className="inline-heading">
          <h2>Explora propiedades relacionadas</h2>
          <Link className="text-link" href="/propiedades">
            Ver propiedades <ChevronRight />
          </Link>
        </div>
        <div className="property-grid">
          {properties
            .filter((p) => p.published)
            .slice(0, 3)
            .map((p) => (
              <PropertyGridCard property={p} key={p.id} />
            ))}
        </div>
      </section>
      <Footer />
    </>
  );
}
function MarkdownLite({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <>
      {lines.map((line, i) =>
        line.startsWith("## ") ? (
          <h2 key={i}>{line.slice(3)}</h2>
        ) : line.startsWith("### ") ? (
          <h3 key={i}>{line.slice(4)}</h3>
        ) : line.startsWith("> ") ? (
          <blockquote key={i}>{line.slice(2)}</blockquote>
        ) : line.startsWith("- ") ? (
          <li key={i}>{line.slice(2)}</li>
        ) : line.trim() ? (
          <p key={i}>{line}</p>
        ) : null,
      )}
    </>
  );
}

export function AboutPage() {
  const [content, setContent] = useState<Record<string, any> | null>(null);
  useEffect(() => { apiFetch<{ results?: Record<string, any>[] }>("/api/v1/public/about/").then((value) => setContent(value.results?.[0] || null)).catch(() => setContent(null)); }, []);
  const c = content || { eyebrow: "CasaViva", hero_title: "Una forma más clara de encontrar hogar.", main_title: "Promocionar bien también es informar mejor.", main_body: "CasaViva reúne y promociona propiedades de desarrolladoras y propietarios particulares para facilitar su exploración y acercar a las personas interesadas con el proveedor correspondiente.", what_we_do_title: "Qué hacemos", what_we_do_body: "Presentamos propiedades de forma visual y ordenada, ayudamos a comparar opciones y canalizamos las solicitudes de información hacia quien comercializa cada inmueble.", how_we_work_title: "Cómo trabajamos", how_we_work_body: "Trabajamos como promotores externos. La información publicada parte de los datos proporcionados o autorizados por desarrolladoras y propietarios, y buscamos mantener precios, disponibilidad y características actualizados.", vision_title: "Nuestra visión", vision_body: "Queremos que encontrar una vivienda sea un proceso más claro, con mejor información, herramientas útiles y seguimiento oportuno." };
  return (
    <>
      <PublicHeader />
      <main>
        <section className="container section">
          <span className="eyebrow">{c.eyebrow}</span>
          <h1>{c.hero_title}</h1>
        </section>
        <section
          className="brand-block"
          style={c.hero_media_url ? { backgroundImage: `url(${c.hero_media_url})` } : undefined}
        >
          <div className="brand-copy">
            <h2>{c.main_title}</h2>
            <p>{c.main_body}</p>
          </div>
        </section>
        <section className="narrow section editorial-body">
          <div className="amenity-group">
            <h2>{c.what_we_do_title}</h2><p>{c.what_we_do_body}</p>
          </div>
          <div className="amenity-group">
            <h2>{c.how_we_work_title}</h2><p>{c.how_we_work_body}</p>
          </div>
          <div className="amenity-group">
            <h2>{c.vision_title}</h2><p>{c.vision_body}</p>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

const contactSchema = z.object({
  name: z.string().min(2, "Escribe tu nombre"),
  email: z.email("Correo inválido"),
  phone: z.string().optional(),
  subject: z.string().min(1, "Selecciona un motivo"),
  message: z.string().min(10, "Cuéntanos un poco más"),
  privacy: z.boolean().refine(Boolean, "Debes aceptar el aviso"),
});
type ContactData = z.infer<typeof contactSchema>;
export function ContactPage() {
  const { siteSettings } = useCasaViva();
  const { toast } = useToast();
  const [sent, setSent] = useState(false);
  const [antibotToken, setAntibotToken] = useState("");
  const [antibotReset, setAntibotReset] = useState(0);
  const acceptAntibotToken = useCallback((token: string) => setAntibotToken(token), []);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ContactData>({ resolver: zodResolver(contactSchema), defaultValues: { subject: "", privacy: false } });
  const submit = async (d: ContactData) => {
    if (antibotIsEnabled() && !antibotToken) {
      toast("Completa la verificación de seguridad.");
      return;
    }
    const analyticsIdentity = await ensureCurrentAnalyticsIdentity();
    const item: Inquiry = {
      id: uid("inq"),
      createdAt: new Date().toISOString(),
      name: d.name,
      email: d.email,
      phone: d.phone,
      message: d.message,
      subject: d.subject,
      source: "contact",
      sessionId: analyticsIdentity.sessionId,
      visitorId: analyticsIdentity.visitorId,
      privacyConsent: d.privacy,
      antibotToken,
      status: "new",
    };
    try {
      await inquiryService.create(item);
      void trackEvent("contact_form_submitted", { source: "contact" }).catch(() => undefined);
      setSent(true);
      setAntibotReset((value) => value + 1);
      toast("Consulta enviada");
    } catch {
      setAntibotReset((value) => value + 1);
      toast("No pudimos enviar la consulta. Intenta nuevamente.");
    }
  };
  return (
    <>
      <PublicHeader />
      <main className="container section contact-layout">
        <div>
          <span className="eyebrow">Hablemos</span>
          <h1>¿Cómo podemos ayudarte?</h1>
          <p className="editorial-body">
            Escríbenos para resolver una duda, pedir apoyo con tu búsqueda o
            conocer más sobre una propiedad.
          </p>
          {siteSettings?.contact_email && <p><a className="text-link" href={`mailto:${siteSettings.contact_email}`}>{siteSettings.contact_email}</a></p>}
          <div className="table-actions">
            {siteSettings?.facebook_url && <a className="text-link" href={siteSettings.facebook_url} target="_blank" rel="noopener noreferrer" aria-label="Facebook de CasaViva">Facebook</a>}
            {siteSettings?.instagram_url && <a className="text-link" href={siteSettings.instagram_url} target="_blank" rel="noopener noreferrer" aria-label="Instagram de CasaViva">Instagram</a>}
            {siteSettings?.tiktok_url && <a className="text-link" href={siteSettings.tiktok_url} target="_blank" rel="noopener noreferrer" aria-label="TikTok de CasaViva">TikTok</a>}
          </div>
        </div>
        <div>
          {sent ? (
            <div className="empty-state">
              <h2>Gracias por escribirnos.</h2>
              <p>Recibimos tu consulta y podremos darle seguimiento.</p>
              <button className="button" onClick={() => setSent(false)}>
                Enviar otro mensaje
              </button>
            </div>
          ) : (
            <form className="filter-form" onSubmit={handleSubmit(submit)}>
              <Field label="Nombre" error={errors.name?.message}>
                <input {...register("name")} />
              </Field>
              <Field label="Correo" error={errors.email?.message}>
                <input type="email" {...register("email")} />
              </Field>
              <Field label="Teléfono">
                <input {...register("phone")} />
              </Field>
              <Field label="Motivo" error={errors.subject?.message}>
                <select {...register("subject")}>
                  <option value="">Selecciona</option>
                  <option value="PROPERTY_INFORMATION">Información de una propiedad</option>
                  <option value="SEARCH_ASSISTANCE">Ayuda con mi búsqueda</option>
                  <option value="GENERAL_COMMENT">Comentario general</option>
                </select>
              </Field>
              <Field label="Mensaje" error={errors.message?.message}>
                <textarea {...register("message")} />
              </Field>
              <label className="privacy-check">
                <input type="checkbox" {...register("privacy")} />
                <span>He leído el <Link href="/aviso-de-privacidad">Aviso de Privacidad</Link>.</span>
              </label>
              {errors.privacy && <small>{errors.privacy.message}</small>}
              <TurnstileWidget onToken={acceptAntibotToken} resetSignal={antibotReset} />
              {siteSettings?.responsible_name && siteSettings?.responsible_address && siteSettings?.privacy_email && <p className="form-privacy-notice">{siteSettings.responsible_name}, responsable del sitio {siteSettings.brand_name || "CasaViva"}, con domicilio en {siteSettings.responsible_address}, tratará los datos que proporciones para atender tu solicitud, dar seguimiento a tu interés inmobiliario, coordinar visitas cuando corresponda y medir internamente la atención brindada. Puedes limitar el uso de tus datos y ejercer tus derechos ARCO escribiendo a {siteSettings.privacy_email}. Consulta el <Link href="/aviso-de-privacidad">Aviso de Privacidad Integral</Link>.</p>}
              <button className="button" type="submit" disabled={isSubmitting || (antibotIsEnabled() && !antibotToken)}>
                Enviar mensaje
              </button>
            </form>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error && <small>{error}</small>}
    </label>
  );
}
export function LegalPage({ type }: { type: "privacy" | "terms" }) {
  const [document, setDocument] = useState<Record<string, any> | null>();
  useEffect(() => { apiFetch<Record<string, any>>(`/api/v1/public/${type === "privacy" ? "privacy-notice" : "terms-of-use"}/`).then(setDocument).catch(() => setDocument(null)); }, [type]);
  return (
    <>
      <PublicHeader />
      <main className="narrow section prose">
        <span className="eyebrow">Legal</span>
        <h1>{document?.title || (type === "privacy" ? "Aviso de privacidad" : "Términos de uso")}</h1>
        {document ? <><p>Versión {document.version}{document.effective_at ? ` · Vigente desde ${formatDate(document.effective_at)}` : ""}</p><MarkdownLite content={document.body} /></> : <p>Este documento no está disponible temporalmente. No enviaremos formularios sin una versión vigente del Aviso de Privacidad.</p>}
      </main>
      <Footer />
    </>
  );
}
