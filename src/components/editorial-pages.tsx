"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
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
import { api } from "@/services/api";
import type { Guide, Inquiry, Property } from "@/types";
import { ensureCurrentAnalyticsIdentity, trackEvent } from "@/components/analytics-provider";

export function DevelopmentsPage() {
  const { developments, properties } = useCasaViva();
  const list = developments.filter((d) => d.published);
  return (
    <>
      <PublicHeader />
      <div
        className="page-hero"
        style={{ backgroundImage: `url(${list[0]?.heroImage})` }}
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
  const { developments, properties } = useCasaViva();
  const d = developments.find((x) => x.slug === slug && x.published);
  const [models, setModels] = useState<Property[]>([]);
  const [inventoryLoaded, setInventoryLoaded] = useState(false);
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    if (!d) return () => { active = false; };
    api.publicListingsAll(`development=${encodeURIComponent(d.id)}`)
      .then((items) => { if (active) { setModels(items); setInventoryLoaded(true); } })
      .catch(() => { if (active) { setModels([]); setInventoryLoaded(true); } });
    return () => { active = false; };
  }, [d]);
  if (!d)
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
  const moveGallery = (delta: number) => setGalleryIndex((current) =>
    current === null ? 0 : (current + delta + d.gallery.length) % d.gallery.length,
  );
  return (
    <>
      <PublicHeader />
      <div
        className="page-hero development-hero"
        style={{ backgroundImage: `url(${d.heroImage})` }}
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
        <section className="section-tight">
          <div className="inline-heading">
            <h2>Galería</h2>
          </div>
          <div className="secondary-gallery">
            {d.gallery.slice(0, 5).map((src, i) => (
              <button key={src} type="button" onClick={() => setGalleryIndex(i)} aria-label={`Abrir foto ${i + 1} de ${d.name}`}>
                <Image
                  src={src}
                  alt={`${d.name}, foto ${i + 1}`}
                  fill
                  sizes="50vw"
                />
              </button>
            ))}
          </div>
          {galleryIndex !== null && d.gallery.length > 0 && (
            <div className="fullscreen-gallery" role="dialog" aria-modal="true" aria-label={`Galería de ${d.name}`}>
              <header>
                <span>Foto {galleryIndex + 1} / {d.gallery.length}</span>
                <button className="icon-button" type="button" onClick={() => setGalleryIndex(null)} aria-label="Cerrar"><X /></button>
              </header>
              <div className="fullscreen-image">
                <Image src={d.gallery[galleryIndex]} alt={`${d.name}, foto ${galleryIndex + 1}`} fill sizes="100vw" />
              </div>
              {d.gallery.length > 1 && <>
                <button className="gallery-nav prev" type="button" onClick={() => moveGallery(-1)} aria-label="Anterior"><ChevronLeft /></button>
                <button className="gallery-nav next" type="button" onClick={() => moveGallery(1)} aria-label="Siguiente"><ChevronRight /></button>
              </>}
            </div>
          )}
        </section>
        <section className="section">
          <div className="section-heading">
            <span className="eyebrow">Amenidades</span>
            <h2>Espacios que acompañan la vida</h2>
          </div>
          <div className="amenity-chips">
            {d.amenities.map((a) => (
              <span className="amenity-chip" key={a}>
                {a}
              </span>
            ))}
          </div>
        </section>
        <section className="section-tight">
          <div className="inline-heading">
            <h2>Ubicación</h2>
          </div>
          {inventoryLoaded ? (
            <DynamicMapView
              properties={
                models.length
                  ? models
                  : [
                      {
                        ...properties[0],
                        latitude: d.latitude,
                        longitude: d.longitude,
                      },
                    ]
              }
            />
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
        className="page-hero development-hero"
        style={{ backgroundImage: `url(${location.heroImage})` }}
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
  return (
    <>
      <PublicHeader />
      <main>
        <section className="container section">
          <span className="eyebrow">CasaViva</span>
          <h1>Una forma más clara de encontrar hogar.</h1>
        </section>
        <section
          className="brand-block"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=2000&q=85)",
          }}
        >
          <div className="brand-copy">
            <h2>Presentar bien también es informar mejor.</h2>
            <p>
              Cada vivienda merece contexto, imágenes cuidadas y datos precisos.
            </p>
          </div>
        </section>
        <section className="narrow section editorial-body">
          <div className="amenity-group">
            <h2>Qué hacemos</h2>
            <p>
              Reunimos propiedades y desarrollos para explorarlos de manera
              visual, ordenada y honesta. Hacemos que comparar sea más sencillo
              sin reducir una decisión importante a una lista de promesas.
            </p>
          </div>
          <div className="amenity-group">
            <h2>Cómo trabajamos</h2>
            <p>
              Priorizamos información clara, fotografía protagonista y
              herramientas prácticas. El mismo cuidado editorial acompaña a
              viviendas de distintos rangos de precio.
            </p>
          </div>
          <div className="amenity-group">
            <h2>Nuestra visión</h2>
            <p>
              Queremos que encontrar casa en México sea una experiencia más
              tranquila: con menos ruido, mejores preguntas y espacio para
              decidir.
            </p>
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
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ContactData>({ resolver: zodResolver(contactSchema), defaultValues: { subject: "", privacy: false } });
  const submit = async (d: ContactData) => {
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
      status: "new",
    };
    try {
      await inquiryService.create(item);
      void trackEvent("contact_form_submitted", { source: "contact" }).catch(() => undefined);
      setSent(true);
      toast("Consulta enviada");
    } catch {
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
                <span>He leído y acepto el Aviso de Privacidad.</span>
              </label>
              {errors.privacy && <small>{errors.privacy.message}</small>}
              <button className="button" type="submit" disabled={isSubmitting}>
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
  return (
    <>
      <PublicHeader />
      <main className="narrow section prose">
        <span className="eyebrow">Legal</span>
        <h1>
          {type === "privacy" ? "Aviso de privacidad" : "Términos de uso"}
        </h1>
        <p>
          CasaViva trata la información proporcionada para atender consultas,
          coordinar visitas y dar seguimiento a solicitudes inmobiliarias.
        </p>
        <h2>
          {type === "privacy"
            ? "Datos y consentimiento"
            : "Uso de la plataforma"}
        </h2>
        <p>
          {type === "privacy"
            ? "Los formularios solicitan únicamente los datos necesarios para responder. El consentimiento y la versión del aviso aplicable se conservan como parte del historial de atención."
            : "La disponibilidad y los precios pueden cambiar. Una publicación informa sobre el inventario registrado y no sustituye la confirmación comercial de CasaViva."}
        </p>
      </main>
      <Footer />
    </>
  );
}
