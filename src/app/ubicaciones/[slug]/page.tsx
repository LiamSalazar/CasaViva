import { LocationPage } from "@/components/editorial-pages";
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <LocationPage slug={slug} />;
}
