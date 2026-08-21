const backend = process.env.DJANGO_INTERNAL_URL || "http://127.0.0.1:8000";

export async function serverApi<T>(path: string): Promise<T | undefined> {
  try {
    const response = await fetch(`${backend}${path}`, { next: { revalidate: 300 } });
    return response.ok ? response.json() : undefined;
  } catch {
    return undefined;
  }
}

export async function serverFetchAllPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let next: string | null = path;
  while (next) {
    const normalized: string = next.startsWith("http")
      ? `${new URL(next).pathname}${new URL(next).search}`
      : next;
    const page = await serverApi<{ results: T[]; next: string | null }>(normalized);
    if (!page) break;
    items.push(...page.results);
    next = page.next;
  }
  return items;
}
