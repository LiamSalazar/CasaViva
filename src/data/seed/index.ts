import type {
  Development,
  Guide,
  HomeContent,
  Inquiry,
  Location,
  Property,
} from "@/types";

const img = (id: string, w = 1800, h = 1200) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${w}&h=${h}&q=86`;
const photos = [
  "photo-1600585154340-be6161a56a0c",
  "photo-1600566753086-00f18fb6b3ea",
  "photo-1600607687920-4e2a09cf159d",
  "photo-1600573472591-ee6b68d14c68",
  "photo-1600607687939-ce8a6c25118c",
  "photo-1600047509807-ba8f99d2cdde",
  "photo-1600210492486-724fe5c67fb0",
  "photo-1600566753190-17f0baa2a6c3",
  "photo-1600585152915-d208bec867a1",
  "photo-1600607688969-a5bfcd646154",
  "photo-1600607688960-e095ff83135c",
  "photo-1600585154526-990dced4db0d",
  "photo-1600566752355-35792bedcfea",
  "photo-1600585154363-67eb9e2e2099",
  "photo-1600566752734-2a0cd4e6a951",
  "photo-1600607688066-890987f18a86",
  "photo-1600607687644-c7171b42498f",
  "photo-1600607687929-52f95fdf0f7b",
  "photo-1600566753051-f0b89df2dd90",
  "photo-1600585152220-90363fe7e115",
  "photo-1600566753198-17f0baa2a6c3",
];
const gallery = (offset: number) =>
  Array.from({ length: 6 }, (_, i) =>
    img(photos[(offset + i) % photos.length]),
  );
const now = "2026-08-10T12:00:00.000Z";

export const seedLocations: Location[] = [
  ["loc-tecamac", "tecamac", "Tecámac", "Estado de México", 19.713, -98.968, 0],
  [
    "loc-zumpango",
    "zumpango",
    "Zumpango",
    "Estado de México",
    19.797,
    -99.099,
    3,
  ],
  [
    "loc-huehuetoca",
    "huehuetoca",
    "Huehuetoca",
    "Estado de México",
    19.835,
    -99.204,
    6,
  ],
  ["loc-chalco", "chalco", "Chalco", "Estado de México", 19.264, -98.897, 9],
  ["loc-tizayuca", "tizayuca", "Tizayuca", "Hidalgo", 19.84, -98.982, 12],
  [
    "loc-cuautitlan",
    "cuautitlan-izcalli",
    "Cuautitlán Izcalli",
    "Estado de México",
    19.646,
    -99.211,
    15,
  ],
].map(([id, slug, name, state, latitude, longitude, p]) => ({
  id: String(id),
  slug: String(slug),
  name: String(name),
  state: String(state),
  latitude: Number(latitude),
  longitude: Number(longitude),
  heroImage: img(photos[Number(p)]),
  featured: true,
  description: `${name} combina vida cotidiana, conexiones metropolitanas y comunidades en crecimiento. Explora viviendas presentadas con información clara y una mirada honesta a cada espacio.`,
}));

const developmentRaw = [
  [
    "dev-1",
    "senderos-de-tecamac",
    "Senderos de Tecámac",
    "Habita Desarrollos",
    "Tecámac",
    0,
  ],
  [
    "dev-2",
    "parque-del-lago",
    "Parque del Lago",
    "Norte Urbano",
    "Zumpango",
    4,
  ],
  [
    "dev-3",
    "arboledas-del-valle",
    "Arboledas del Valle",
    "Vértice Hogar",
    "Huehuetoca",
    8,
  ],
  [
    "dev-4",
    "patios-de-chalco",
    "Patios de Chalco",
    "Tierra Clara",
    "Chalco",
    12,
  ],
  [
    "dev-5",
    "hacienda-tizayuca",
    "Hacienda Tizayuca",
    "Casa Norte",
    "Tizayuca",
    16,
  ],
];
export const seedDevelopments: Development[] = developmentRaw.map(
  ([id, slug, name, developerName, municipality, p], index) => ({
    id: String(id),
    slug: String(slug),
    name: String(name),
    developerName: String(developerName),
    municipality: String(municipality),
    state: municipality === "Tizayuca" ? "Hidalgo" : "Estado de México",
    neighborhood: "Zona Centro",
    latitude: 19.72 + index * 0.025,
    longitude: -99.02 - index * 0.018,
    heroImage: img(photos[Number(p)]),
    gallery: gallery(Number(p)),
    amenities: [
      "Áreas verdes",
      "Juegos infantiles",
      "Acceso controlado",
      "Andadores",
    ],
    propertyIds: [],
    published: true,
    featured: index < 4,
    createdAt: now,
    updatedAt: now,
    shortDescription:
      "Una comunidad pensada para vivir con calma, servicios cercanos y espacios bien aprovechados.",
    description:
      "Un desarrollo residencial de escala amable, con arquitectura contemporánea y áreas comunes que acompañan la vida diaria. Sus modelos ofrecen distribuciones claras, iluminación natural y opciones para diferentes etapas de vida.",
  }),
);

const propertyRaw = [
  ["Casa Lirio", "Tecámac", 1190000, "house", "new", 3, 2, 68, 72, "dev-1"],
  ["Casa Nube", "Tecámac", 1050000, "townhouse", "new", 2, 1, 58, 64, "dev-1"],
  ["Casa Patio Norte", "Tecámac", 1350000, "house", "used", 3, 2, 82, 96, ""],
  [
    "Departamento Arista",
    "Tecámac",
    890000,
    "apartment",
    "new",
    2,
    1,
    54,
    0,
    "",
  ],
  ["Casa Lago", "Zumpango", 780000, "house", "new", 2, 1, 52, 60, "dev-2"],
  ["Casa Fresno", "Zumpango", 1190000, "house", "new", 3, 2, 72, 78, "dev-2"],
  [
    "Townhouse Bruma",
    "Zumpango",
    1650000,
    "townhouse",
    "used",
    3,
    2,
    98,
    110,
    "",
  ],
  [
    "Casa del Valle",
    "Huehuetoca",
    1050000,
    "house",
    "new",
    3,
    2,
    70,
    74,
    "dev-3",
  ],
  ["Casa Encino", "Huehuetoca", 890000, "house", "used", 2, 1, 61, 76, "dev-3"],
  ["Terreno Horizonte", "Huehuetoca", 780000, "land", "used", 0, 0, 0, 180, ""],
  ["Casa Bugambilia", "Chalco", 1350000, "house", "new", 3, 2, 76, 88, "dev-4"],
  ["Casa Albor", "Chalco", 1190000, "townhouse", "new", 3, 2, 69, 72, "dev-4"],
  [
    "Casa Mezquite",
    "Tizayuca",
    1650000,
    "house",
    "new",
    3,
    2,
    101,
    120,
    "dev-5",
  ],
  ["Casa Cielo", "Tizayuca", 2100000, "house", "used", 4, 3, 145, 168, "dev-5"],
  [
    "Departamento Umbral",
    "Cuautitlán Izcalli",
    2100000,
    "apartment",
    "used",
    2,
    2,
    86,
    0,
    "",
  ],
  [
    "Casa Jardín Central",
    "Cuautitlán Izcalli",
    3500000,
    "house",
    "used",
    4,
    3,
    210,
    250,
    "",
  ],
] as const;

export const seedProperties: Property[] = propertyRaw.map((r, index) => {
  const [
    title,
    municipality,
    price,
    propertyType,
    condition,
    bedrooms,
    bathrooms,
    constructionM2,
    landM2,
    developmentId,
  ] = r;
  const state = municipality === "Tizayuca" ? "Hidalgo" : "Estado de México";
  const g = gallery(index);
  return {
    id: `prop-${index + 1}`,
    slug: String(title)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, ""),
    title,
    shortTitle: title,
    subtitle: "Espacios claros para una vida cotidiana más tranquila",
    operation: "sale",
    propertyType,
    condition,
    status: index === 6 ? "reserved" : "available",
    published: true,
    featured: [0, 3, 5, 12, 15].includes(index),
    price,
    currency: "MXN",
    priceLabel: developmentId ? "from" : "fixed",
    state,
    municipality,
    neighborhood: index % 2 ? "Centro" : "Los Héroes",
    address: `${municipality}, zona residencial`,
    latitude:
      (seedLocations.find((l) => l.name === municipality)?.latitude || 19.7) +
      (index % 3) * 0.006,
    longitude:
      (seedLocations.find((l) => l.name === municipality)?.longitude || -99) +
      (index % 4) * 0.005,
    bedrooms,
    bathrooms,
    halfBathrooms: bathrooms ? index % 2 : 0,
    parkingSpaces: propertyType === "land" ? 0 : index % 3 === 0 ? 2 : 1,
    constructionM2: constructionM2 || undefined,
    landM2: landM2 || undefined,
    levels: propertyType === "apartment" || propertyType === "land" ? 1 : 2,
    shortDescription:
      "Una vivienda luminosa, bien distribuida y conectada con los servicios que hacen sencilla la vida diaria.",
    description:
      "Esta propiedad reúne una distribución práctica, buena entrada de luz natural y materiales pensados para el uso cotidiano. La estancia conecta con las áreas sociales y permite adaptar el espacio a distintos momentos del día. Las habitaciones mantienen privacidad y proporciones cómodas. Su ubicación ofrece acceso a comercios, escuelas y vías principales, conservando una sensación residencial tranquila.",
    amenities:
      index % 2
        ? ["Seguridad", "Área de juegos", "Áreas verdes"]
        : ["Patio", "Jardín", "Acceso controlado"],
    internalFeatures: ["Cocina integral", "Clósets", "Iluminación natural"],
    externalFeatures: ["Cisterna", "Patio de servicio", "Calles iluminadas"],
    developmentId: developmentId || undefined,
    developerId: developmentId ? `builder-${developmentId}` : undefined,
    heroImage: g[0],
    gallery: g,
    floorplans:
      index % 3 === 0
        ? [img("photo-1600607688969-a5bfcd646154", 1400, 1000)]
        : undefined,
    videoUrl:
      index === 0 ? "https://www.youtube.com/watch?v=dQw4w9WgXcQ" : undefined,
    tour360Url: index === 0 ? "https://example.com/tour-demo" : undefined,
    createdAt: new Date(Date.parse(now) - index * 86400000).toISOString(),
    updatedAt: new Date(Date.parse(now) - index * 43200000).toISOString(),
    internal: {
      commissionPercent: 3,
      notes: "Seguimiento interno de demostración.",
      reference: `CV-${String(index + 1).padStart(4, "0")}`,
    },
  };
});

seedDevelopments.forEach((d) => {
  d.propertyIds = seedProperties
    .filter((p) => p.developmentId === d.id)
    .map((p) => p.id);
});

export const seedGuides: Guide[] = [
  [
    "guia-1",
    "vivir-en-tecamac",
    "Vivir en Tecámac: una guía para mirar con calma",
    "zonas",
    2,
    125,
  ],
  [
    "guia-2",
    "como-comparar-una-casa",
    "Cómo comparar dos casas más allá del precio",
    "compra",
    7,
    98,
  ],
  [
    "guia-3",
    "espacios-que-crecen-contigo",
    "Espacios que pueden crecer contigo",
    "hogar",
    10,
    77,
  ],
  [
    "guia-4",
    "entender-el-mercado-local",
    "Una forma sencilla de entender el mercado local",
    "mercado",
    14,
    63,
  ],
  [
    "guia-5",
    "vivir-en-tizayuca",
    "Vivir en Tizayuca: conexiones y vida cotidiana",
    "zonas",
    18,
    51,
  ],
].map(([id, slug, title, category, p, viewCount]) => ({
  id: String(id),
  slug: String(slug),
  title: String(title),
  category: category as Guide["category"],
  viewCount: Number(viewCount),
  heroImage: img(photos[Number(p)]),
  published: true,
  featured: id === "guia-1",
  createdAt: now,
  excerpt:
    "Claves concretas para conocer la zona y tomar una decisión informada, sin prisas ni promesas vacías.",
  content: `## Mirar la zona como parte de la casa\n\nElegir vivienda también es elegir los trayectos, comercios y ritmos que formarán parte de cada semana. Conviene visitar más de una vez y en distintos horarios.\n\n### Lo que vale la pena observar\n\n- Accesos y tiempos reales de traslado.\n- Servicios que utilizarás con frecuencia.\n- Espacios públicos y vida de la calle.\n- Posibilidades de adaptar la vivienda.\n\n> Una buena decisión empieza con información clara y tiempo para comparar.\n\n## Antes de decidir\n\nHaz una lista breve con lo indispensable y otra con lo deseable. Esa separación ayuda a comparar opciones sin perder de vista lo que realmente importa.`,
}));

export const seedInquiries: Inquiry[] = [
  {
    id: "inq-1",
    createdAt: now,
    name: "Mariana López",
    email: "mariana@example.mx",
    phone: "55 1234 5678",
    message: "Quisiera conocer los horarios disponibles para visitar.",
    source: "property",
    privacyConsent: true,
    propertyId: "prop-1",
    status: "new",
  },
  {
    id: "inq-2",
    createdAt: "2026-08-08T15:00:00.000Z",
    name: "Diego Ramos",
    email: "diego@example.mx",
    phone: "55 9876 4321",
    message: "Busco una casa de tres recámaras en Tecámac.",
    source: "contact",
    privacyConsent: true,
    subject: "Ayuda con mi búsqueda",
    status: "viewed",
  },
];

export const seedHomeContent: HomeContent = {
  heroEyebrow: "Propiedades en México",
  heroTitle: "Encuentra el lugar que quieres llamar hogar",
  heroSlides: seedProperties
    .filter((p) => p.featured)
    .slice(0, 5)
    .map((p, order) => ({
      id: `slide-${order + 1}`,
      propertyId: p.id,
      eyebrow: `${p.municipality}, ${p.state}`,
      title: p.title,
      subtitle: p.shortDescription,
      order,
      active: true,
    })),
  featuredPropertyIds: seedProperties
    .filter((p) => p.featured)
    .map((p) => p.id),
  featuredLocationIds: seedLocations.map((l) => l.id),
  featuredDevelopmentIds: seedDevelopments
    .filter((d) => d.featured)
    .map((d) => d.id),
  editorialTitle:
    "Tu casa no es sólo un lugar.\nEs donde empieza lo que sigue.",
  editorialBody:
    "CasaViva presenta cada propiedad con claridad, contexto y el cuidado visual que merece.",
  editorialImage: img("photo-1600607687920-4e2a09cf159d", 2200, 1400),
};

export const seed = {
  properties: seedProperties,
  developments: seedDevelopments,
  locations: seedLocations,
  guides: seedGuides,
  inquiries: seedInquiries,
  homeContent: seedHomeContent,
};
