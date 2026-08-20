import { DevelopmentFormPage } from "@/components/admin";
export default async function Page({ params }: { params: Promise<{ id: string }> }) { return <DevelopmentFormPage id={(await params).id} />; }
