import { GuideFormPage } from "@/components/admin";
export default async function Page({ params }: { params: Promise<{ id: string }> }) { return <GuideFormPage id={(await params).id} />; }
