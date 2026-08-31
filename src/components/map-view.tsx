"use client";

import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import Image from "next/image";
import Link from "next/link";
import { useEffect } from "react";
import type { Property } from "@/types";
import { formatCurrency } from "@/lib/utils";

function Bounds({ properties }: { properties: Property[] }) {
  const map = useMap();
  useEffect(() => {
    const located = properties.filter((p) => Number.isFinite(p.latitude) && Number.isFinite(p.longitude));
    if (!located.length) return;
    const bounds = L.latLngBounds(
      located.map((p) => [p.latitude!, p.longitude!] as [number, number]),
    );
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  }, [map, properties]);
  return null;
}
export function MapView({
  properties,
  selectedId,
  onSelect,
}: {
  properties: Property[];
  selectedId?: string;
  onSelect?: (id: string) => void;
}) {
  const located = properties.filter((p) => Number.isFinite(p.latitude) && Number.isFinite(p.longitude));
  const center: [number, number] = located.length
    ? [located[0].latitude!, located[0].longitude!]
    : [19.65, -99.05];
  return (
    <div className="map-shell">
      <MapContainer center={center} zoom={10} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Bounds properties={located} />
        {located.map((p) => (
          <Marker
            key={p.id}
            position={[p.latitude!, p.longitude!]}
            eventHandlers={{ click: () => onSelect?.(p.id) }}
            icon={L.divIcon({
              className: "",
              html: `<span class="map-marker" style="${selectedId === p.id ? "background:#c51f3a" : ""}">${p.price === undefined ? "—" : new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 }).format(p.price)}</span>`,
              iconSize: [70, 30],
              iconAnchor: [35, 15],
            })}
          >
            <Popup>
              <Link href={`/propiedades/${p.slug}`} className="map-preview">
                <Image
                  src={p.heroImage}
                  alt={p.title}
                  width={210}
                  height={100}
                />
                <strong>{p.title}</strong>
                <span>{formatCurrency(p.price)}</span>
              </Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
