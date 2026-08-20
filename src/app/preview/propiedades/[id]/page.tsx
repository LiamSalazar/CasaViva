import { PropertyDetailPage } from "@/components/search-pages";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PropertyDetailPage previewId={id} />;
}
