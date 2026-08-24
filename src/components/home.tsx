"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PublicHeaderOverlay, Footer } from "@/components/ui";
import { DevelopmentCard } from "@/components/property";
import { formatCurrency, slugify } from "@/lib/utils";
import { useCasaViva } from "@/services";

export function HomePage() {
  const { properties, locations, developments, homeContent } = useCasaViva();
  const slides = homeContent.heroSlides
    .filter((s) => s.active)
    .sort((a, b) => a.order - b.order);
  const [active, setActive] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(
      () => setActive((x) => (x + 1) % Math.max(slides.length, 1)),
      7000,
    );
    return () => clearInterval(timer);
  }, [slides.length]);
  const featuredProperty =
    properties.find((p) => p.id === homeContent.featuredPropertyIds[0]) ||
    properties[0];
  const grouped = useMemo(
    () =>
      locations.reduce<Record<string, typeof locations>>((acc, l) => {
        (acc[l.state] ??= []).push(l);
        return acc;
      }, {}),
    [locations],
  );
  return (
    <>
      <main>
        <section className="home-hero">
          <PublicHeaderOverlay />
          {slides.map((s, i) => {
            const p = properties.find((x) => x.id === s.propertyId);
            return p ? (
              <div
                className={`hero-slide ${i === active ? "active" : ""}`}
                key={s.id}
              >
                <Image
                  src={p.heroImage}
                  alt={p.title}
                  fill
                  priority={i === 0}
                  sizes="100vw"
                />
              </div>
            ) : null;
          })}
          <div className="hero-content">
            <span className="eyebrow">{homeContent.heroEyebrow}</span>
            <h1>{homeContent.heroTitle}</h1>
            <HeroSearch locations={locations.map((l) => l.name)} />
          </div>
          <div className="hero-meta">
            {slides[active] &&
              (() => {
                const p = properties.find(
                  (x) => x.id === slides[active].propertyId,
                );
                return p ? (
                  <Link
                    href={`/propiedades/${p.slug}`}
                    className="hero-property"
                  >
                    <span className="eyebrow">{slides[active].eyebrow}</span>
                    <h3>{slides[active].title}</h3>
                    <p>{formatCurrency(p.price)}</p>
                  </Link>
                ) : null;
              })()}
            {slides.length > 1 && <div className="hero-controls">
              <button
                className="icon-button"
                onClick={() =>
                  setActive((x) => (x - 1 + slides.length) % slides.length)
                }
                aria-label="Anterior"
              >
                <ChevronLeft />
              </button>
              <div className="hero-dots">
                {slides.map((s, i) => (
                  <button
                    key={s.id}
                    className={i === active ? "active" : ""}
                    onClick={() => setActive(i)}
                    aria-label={`Ir a slide ${i + 1}`}
                  />
                ))}
              </div>
              <button
                className="icon-button"
                onClick={() => setActive((x) => (x + 1) % slides.length)}
                aria-label="Siguiente"
              >
                <ChevronRight />
              </button>
            </div>}
          </div>
        </section>
        {homeContent.featuredLocationIds.length > 0 && <section className="section">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">Lugares para vivir</span>
              <h2>Encuentra hogar en lugares que se sienten tuyos</h2>
              <p>
                Explora comunidades con distintas maneras de habitar, conectarte
                y construir una vida cotidiana.
              </p>
            </div>
          </div>
          <div className="location-strip">
            {homeContent.featuredLocationIds
              .map((id) => locations.find((l) => l.id === id))
              .filter(Boolean)
              .map((l) => (
                <Link
                  href={`/ubicaciones/${l!.slug}`}
                  className="location-tile"
                  key={l!.id}
                >
                  <Image src={l!.heroImage} alt={l!.name} fill sizes="25vw" />
                  <span>{l!.name}</span>
                </Link>
              ))}
          </div>
        </section>}
        {featuredProperty && (
          <Link
            href={`/propiedades/${featuredProperty.slug}`}
            className="editorial-feature"
          >
            <Image
              src={featuredProperty.heroImage}
              alt={featuredProperty.title}
              fill
              sizes="100vw"
            />
            <div className="editorial-feature-content">
              <span className="eyebrow">
                {featuredProperty.propertyType === "apartment"
                  ? "Departamento"
                  : "Casa"}{" "}
                en venta · {featuredProperty.municipality}
              </span>
              <h2>{featuredProperty.title}</h2>
              <p>{featuredProperty.shortDescription}</p>
              <span className="button secondary">Conocer la propiedad</span>
            </div>
          </Link>
        )}
        {homeContent.editorialTitle && homeContent.editorialBody && <section
          className="brand-block"
          style={{ backgroundImage: `url(${homeContent.editorialImage})` }}
        >
          <div className="brand-copy">
            <h2>{homeContent.editorialTitle}</h2>
            <p>{homeContent.editorialBody}</p>
          </div>
        </section>}
        {homeContent.featuredDevelopmentIds.length > 0 && <section className="section">
          <div className="container">
            <div className="inline-heading">
              <div>
                <span className="eyebrow">Nuevas comunidades</span>
                <h2>Desarrollos para descubrir</h2>
              </div>
              <Link className="text-link" href="/desarrollos">
                Ver todos <ChevronRight size={16} />
              </Link>
            </div>
            <div className="development-grid">
              {homeContent.featuredDevelopmentIds
                .map((id) => developments.find((d) => d.id === id))
                .filter(Boolean)
                .map((d) => (
                  <DevelopmentCard
                    key={d!.id}
                    development={d!}
                    properties={properties}
                  />
                ))}
            </div>
          </div>
        </section>}
        <section
          className="section"
          style={{ background: "var(--cv-gray-100)" }}
        >
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">Explora a tu manera</span>
              <h2>Encuentra el hogar que estás buscando</h2>
            </div>
            <div className="directory">
              {[
                ["Casas", "propertyType=house"],
                ["Departamentos", "propertyType=apartment"],
                ["Casas nuevas", "propertyType=house&condition=new"],
                ["Casas usadas", "propertyType=house&condition=used"],
                ["Desarrollos", "development=true"],
                ["Terrenos", "propertyType=land"],
              ].map(([label, q]) => (
                <Link
                  href={
                    label === "Desarrollos"
                      ? "/desarrollos"
                      : `/propiedades?${q}`
                  }
                  key={label}
                >
                  {label}
                  <ChevronRight />
                </Link>
              ))}
            </div>
          </div>
        </section>
        <section className="section">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">Directorio</span>
              <h2>Propiedades en las principales zonas</h2>
            </div>
            <div className="seo-columns">
              {Object.entries(grouped).map(([state, items]) => (
                <div key={state}>
                  <h3>{state}</h3>
                  {items.map((l) => (
                    <Link
                      key={l.id}
                      href={`/propiedades?municipality=${slugify(l.name)}`}
                    >
                      {l.name}
                    </Link>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function HeroSearch({ locations }: { locations: string[] }) {
  const router = useRouter();
  const [location, setLocation] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  return (
    <form
      className="hero-search"
      onSubmit={(e) => {
        e.preventDefault();
        const q = new URLSearchParams();
        if (location) q.set("municipality", slugify(location));
        if (maxPrice) q.set("maxPrice", maxPrice);
        router.push(`/propiedades?${q}`);
      }}
    >
      <label>
        Operación
        <select aria-label="Operación" defaultValue="sale">
          <option value="sale">En venta</option>
        </select>
      </label>
      <label>
        Precio
        <select
          value={maxPrice}
          onChange={(e) => setMaxPrice(e.target.value)}
          aria-label="Precio máximo"
        >
          <option value="">Cualquier precio</option>
          <option value="1000000">Hasta $1,000,000</option>
          <option value="1300000">Hasta $1,300,000</option>
          <option value="1600000">Hasta $1,600,000</option>
          <option value="2500000">Hasta $2,500,000</option>
        </select>
      </label>
      <label>
        Localidad
        <select
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          aria-label="Localidad"
        >
          <option value="">Todas las localidades</option>
          {locations.map((l) => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </label>
      <button className="button" type="submit">
        <Search size={17} /> Buscar
      </button>
    </form>
  );
}
