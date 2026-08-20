import { EmptyState, Footer, PublicHeader } from "@/components/ui";
export default function NotFound() { return <><PublicHeader /><main className="section"><EmptyState title="No encontramos esta página" body="La dirección puede haber cambiado o el contenido ya no está disponible." href="/" action="Volver al inicio" /></main><Footer /></>; }
