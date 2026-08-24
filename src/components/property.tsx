"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Maximize2,
  Images,
  Play,
  ScanLine,
  ChevronLeft,
  ChevronRight,
  X,
  CalendarDays,
} from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Development, Inquiry, Property } from "@/types";
import {
  formatArea,
  formatCurrency,
  formatLocation,
  propertyTypeLabel,
  uid,
} from "@/lib/utils";
import { FavoriteButton, ShareButton, useToast } from "@/components/ui";
import { ensureCurrentAnalyticsIdentity, trackEvent } from "@/components/analytics-provider";
import { inquiryService, useCasaViva } from "@/services";

export const DynamicMapView = dynamic(
  () => import("./map-view").then((m) => m.MapView),
  { ssr: false, loading: () => <div className="map-shell skeleton" /> },
);

export function PropertyListCard({
  property,
  development,
  onHover,
}: {
  property: Property;
  development?: Development;
  onHover?: (id?: string) => void;
}) {
  return (
    <Link
      href={`/propiedades/${property.slug}`}
      className="property-list-card"
      onMouseEnter={() => onHover?.(property.id)}
      onMouseLeave={() => onHover?.()}
    >
      <div className="property-image">
        <Image
          src={property.heroImage}
          alt={property.title}
          fill
          sizes="(max-width: 767px) 100vw, 42vw"
        />
        <span className="photo-count">
          <Images size={13} /> {property.gallery.length}
        </span>
      </div>
      <div className="property-card-body">
        <div className="property-card-actions">
          <ShareButton />
          <FavoriteButton id={property.id} />
        </div>
        <span className="property-type">
          {property.propertyTypeName || propertyTypeLabel[property.propertyType] || property.propertyType} en venta ·{" "}
          {formatLocation(property.municipality, property.state)}
        </span>
        <h2>{property.title}</h2>
        <div className="property-price">
          {property.priceLabel === "from" && "Desde "}
          {formatCurrency(property.price)}
        </div>
        <div className="property-facts">
          {property.constructionM2 && (
            <span>{formatArea(property.constructionM2)}</span>
          )}
          {(property.bedrooms || 0) > 0 && <span>{property.bedrooms} rec.</span>}
          {(property.bathrooms || 0) > 0 && <span>{property.bathrooms} baños</span>}
        </div>
        <p className="property-description">{property.shortDescription}</p>
        {development && (
          <span className="property-development">En {development.name}</span>
        )}
      </div>
    </Link>
  );
}
export function PropertyGridCard({ property }: { property: Property }) {
  return (
    <Link href={`/propiedades/${property.slug}`} className="property-grid-card">
      <div className="property-image">
        <Image
          src={property.heroImage}
          alt={property.title}
          fill
          sizes="(max-width:767px) 100vw, 33vw"
        />
        <div className="property-card-actions">
          <FavoriteButton id={property.id} />
        </div>
      </div>
      <div className="property-card-body">
        <span className="property-type">
          {property.propertyTypeName || propertyTypeLabel[property.propertyType] || property.propertyType} · {property.municipality}
        </span>
        <h3>{property.title}</h3>
        <div className="property-price">
          {property.priceLabel === "from" && "Desde "}
          {formatCurrency(property.price)}
        </div>
        <div className="property-facts">
          <span>{formatArea(property.constructionM2 || property.landM2)}</span>
          {(property.bedrooms || 0) > 0 && <span>{property.bedrooms} rec.</span>}
          {(property.bathrooms || 0) > 0 && <span>{property.bathrooms} baños</span>}
        </div>
      </div>
    </Link>
  );
}
export const PropertyCard = PropertyGridCard;

export function DevelopmentCard({
  development,
  properties,
}: {
  development: Development;
  properties: Property[];
}) {
  const associated = properties.filter(
    (p) => p.developmentId === development.id && p.published,
  );
  const knownPrices = associated.map((p) => p.price).filter((x): x is number => x !== undefined);
  const count = development.publishedListingCount ?? associated.length;
  const min = development.currentMinPrice ?? (knownPrices.length ? Math.min(...knownPrices) : 0);
  return (
    <Link
      href={`/desarrollos/${development.slug}`}
      className="development-card"
    >
      <div className="image-wrap">
        <Image
          src={development.heroImage}
          alt={development.name}
          width={900}
          height={620}
        />
      </div>
      <h3>{development.name}</h3>
      <p>
        {development.municipality}, {development.state} · {count}{" "}
        {count === 1 ? "propiedad" : "propiedades"}
        {min ? ` · Desde ${formatCurrency(min)}` : ""}
      </p>
    </Link>
  );
}

export function PropertyGallery({ property }: { property: Property }) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [galleryKind, setGalleryKind] = useState<"photos" | "floorplans">("photos");
  const photos = [
    property.heroImage,
    ...property.gallery.filter((x) => x !== property.heroImage),
  ];
  const images = galleryKind === "floorplans" ? property.floorplans || [] : photos;
  const show = (i = 0, kind: "photos" | "floorplans" = "photos") => {
    setGalleryKind(kind);
    setIndex(i);
    setOpen(true);
  };
  const move = useCallback(
    (delta: number) =>
      setIndex((x) => (x + delta + images.length) % images.length),
    [images.length],
  );
  useEffect(() => {
    if (!open) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "ArrowRight") move(1);
      if (e.key === "ArrowLeft") move(-1);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [open, move]);
  return (
    <>
      <div className="property-gallery">
        {photos.slice(0, 5).map((src, i) => (
          <div
            className="gallery-cell"
            key={src + i}
            onClick={() => show(i)}
            aria-label={`Abrir foto ${i + 1}`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") show(i);
            }}
          >
            <Image
              src={src}
              alt={`${property.title}, foto ${i + 1}`}
              fill
              sizes={i === 0 ? "50vw" : "25vw"}
            />
            {i === 0 && (
              <span
                className="gallery-overlays"
                onClick={(e) => e.stopPropagation()}
              >
                <button onClick={() => show(0, "photos")}>
                  <Images size={14} /> {photos.length} Fotos
                </button>
                {property.floorplans?.length ? (
                  <button onClick={() => show(0, "floorplans")}>
                    <Maximize2 size={14} /> {property.floorplans.length} Planos
                  </button>
                ) : null}
                {property.videoUrl && (
                  <button
                    onClick={() => window.open(property.videoUrl, "_blank")}
                  >
                    <Play size={14} /> Video
                  </button>
                )}
                {property.tour360Url && (
                  <button
                    onClick={() => window.open(property.tour360Url, "_blank")}
                  >
                    <ScanLine size={14} /> Tour 360°
                  </button>
                )}
              </span>
            )}
          </div>
        ))}
      </div>
      {open && (
        <div
          className="fullscreen-gallery"
          role="dialog"
          aria-modal="true"
          aria-label="Galería de propiedad"
        >
          <header>
            <span>
              {galleryKind === "floorplans" ? "Plano" : "Foto"} {index + 1} / {images.length}
            </span>
            <button
              className="icon-button"
              onClick={() => setOpen(false)}
              aria-label="Cerrar"
            >
              <X />
            </button>
          </header>
          <div className="fullscreen-image">
            <Image
              src={images[index]}
              alt={`${property.title}, foto ${index + 1}`}
              width={1800}
              height={1200}
            />
            <button
              className="gallery-arrow prev"
              onClick={() => move(-1)}
              aria-label="Anterior"
            >
              <ChevronLeft />
            </button>
            <button
              className="gallery-arrow next"
              onClick={() => move(1)}
              aria-label="Siguiente"
            >
              <ChevronRight />
            </button>
          </div>
          <div className="gallery-thumbs">
            {images.map((src, i) => (
              <button
                className={i === index ? "active" : ""}
                onClick={() => setIndex(i)}
                key={src + i}
              >
                <Image
                  src={src}
                  alt={`Miniatura ${i + 1}`}
                  width={72}
                  height={50}
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export function PropertyStickyBar({
  property,
  anchor,
}: {
  property: Property;
  anchor: React.RefObject<HTMLDivElement | null>;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = anchor.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => setVisible(!entry.isIntersecting),
      { threshold: 0 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [anchor]);
  return (
    <div className={`sticky-property-bar ${visible ? "visible" : ""}`}>
      <div className="sticky-bar-facts">
        <strong>{formatCurrency(property.price)}</strong>
        {property.constructionM2 && (
          <span>{formatArea(property.constructionM2)}</span>
        )}
        {property.bedrooms != null && <span>{property.bedrooms} rec.</span>}
        {property.bathrooms != null && <span>{property.bathrooms} baños</span>}
      </div>
      <div>
        <ShareButton />
        <FavoriteButton id={property.id} />
      </div>
    </div>
  );
}
export function PropertyDetails({ property }: { property: Property }) {
  const rows = [
    ["Recámaras", property.bedrooms || undefined],
    ["Baños", property.bathrooms || undefined],
    ["Medios baños", property.halfBathrooms],
    [
      "Construcción",
      property.constructionM2 && formatArea(property.constructionM2),
    ],
    ["Terreno", property.landM2 && formatArea(property.landM2)],
    ["Estacionamientos", property.parkingSpaces],
    ["Niveles", property.levels],
    ["Condición", property.condition ? (property.condition === "new" ? "Nueva" : "Usada") : undefined],
  ];
  return (
    <div className="details-grid">
      {rows
        .filter(([, v]) => v !== undefined && v !== 0)
        .map(([k, v]) => (
          <div className="detail-row" key={String(k)}>
            <span className="muted">{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
    </div>
  );
}
export function PropertyAmenities({ property }: { property: Property }) {
  return (
    <>
      {[
        ["Características interiores", property.internalFeatures],
        ["Características exteriores", property.externalFeatures],
        ["Amenidades", property.amenities],
      ].map(([title, items]) => (
        <div className="amenity-group" key={String(title)}>
          <h3>{title}</h3>
          <div className="amenity-chips">
            {(items as string[]).map((x) => (
              <span className="amenity-chip" key={x}>
                {x}
              </span>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

const inquirySchema = z.object({
  name: z.string().min(2, "Escribe tu nombre"),
  email: z.email("Correo inválido"),
  phone: z.string().min(8, "Teléfono inválido"),
  message: z.string().min(10, "Cuéntanos un poco más"),
  privacy: z.boolean().refine(Boolean, "Debes aceptar el aviso"),
});
type InquiryForm = z.infer<typeof inquirySchema>;
export function PropertyContactCard({ property }: { property: Property }) {
  const { toast } = useToast();
  const [sent, setSent] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<InquiryForm>({
    resolver: zodResolver(inquirySchema),
    defaultValues: {
      message: `Me interesa ${property.title}. Quisiera recibir más información.`,
      privacy: false,
    },
  });
  const submit = async (
    data: InquiryForm,
    source: "property" | "visit" = "property",
  ) => {
    const analyticsIdentity = await ensureCurrentAnalyticsIdentity();
    const item: Inquiry = {
      id: uid("inq"),
      createdAt: new Date().toISOString(),
      name: data.name,
      email: data.email,
      phone: data.phone,
      message: data.message,
      source,
      propertyId: property.id,
      listingSlug: property.slug,
      sessionId: analyticsIdentity.sessionId,
      visitorId: analyticsIdentity.visitorId,
      privacyConsent: data.privacy,
      status: "new",
    };
    try {
      await inquiryService.create(item);
      void trackEvent("contact_form_submitted", { source }, { listing: property.id, offering: property.offeringId }).catch(() => undefined);
      setSent(true);
      reset();
      toast(source === "visit" ? "Solicitud de visita enviada" : "Consulta enviada");
    } catch {
      toast("No pudimos enviar la consulta. Intenta nuevamente.");
    }
  };
  if (sent)
    return (
      <aside className="contact-card" aria-live="polite">
        <CasaVivaMark />
        <h2>Gracias por escribirnos.</h2>
        <p>
          Recibimos tu consulta. El equipo de CasaViva podrá darle seguimiento.
        </p>
        <button className="button secondary" onClick={() => setSent(false)}>
          Enviar otra consulta
        </button>
      </aside>
    );
  return (
    <aside className="contact-card">
      <CasaVivaMark />
      <h2>Me interesa esta propiedad</h2>
      <form onSubmit={handleSubmit((d) => submit(d))}>
        <Input
          label="Nombre"
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label="Correo"
          type="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          label="Teléfono"
          error={errors.phone?.message}
          {...register("phone")}
        />
        <label className="field">
          <span>Mensaje</span>
          <textarea {...register("message")} />
          <small>{errors.message?.message}</small>
        </label>
        <label className="privacy-check">
          <input type="checkbox" {...register("privacy")} />
          <span>He leído y acepto el Aviso de Privacidad.</span>
        </label>
        {errors.privacy && <small>{errors.privacy.message}</small>}
        <button disabled={isSubmitting} className="button" type="submit">
          Solicitar información
        </button>
        <button
          className="button secondary"
          type="button"
          onClick={handleSubmit((d) => submit(d, "visit"))}
        >
          <CalendarDays size={17} /> Solicitar visita
        </button>
      </form>
    </aside>
  );
}
function CasaVivaMark() {
  return <strong className="eyebrow">CASAVIVA</strong>;
}
function Input({
  label,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
      {error && <small>{error}</small>}
    </label>
  );
}

export function PropertyNote({ id }: { id: string }) {
  const { notes, setNote } = useCasaViva();
  const [value, setValue] = useState(notes[id] || "");
  const { toast } = useToast();
  return (
    <div>
      <textarea
        className="property-note"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Añade una nota privada sobre esta propiedad"
        aria-label="Nota privada"
      />
      <button
        className="read-more"
        onClick={() => {
          setNote(id, value);
          toast("Nota privada guardada");
        }}
      >
        Guardar nota
      </button>
    </div>
  );
}
export function SecondaryGallery({ property }: { property: Property }) {
  return (
    <div className="secondary-gallery">
      {property.gallery.slice(0, 5).map((src, i) => (
        <button key={src + i}>
          <Image
            src={src}
            alt={`${property.title}, galería ${i + 1}`}
            fill
            sizes="35vw"
          />
          {i === 4 && (
            <span className="gallery-more">
              Ver las {property.gallery.length} fotos
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
