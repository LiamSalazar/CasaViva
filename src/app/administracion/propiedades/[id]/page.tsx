import { PropertyFormPage } from "@/components/admin";
export default async function Page({ params }: { params: Promise<{ id: string }> }) { return <PropertyFormPage id={(await params).id} />; }
