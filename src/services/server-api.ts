const backend = process.env.DJANGO_INTERNAL_URL || "http://127.0.0.1:8000";

export async function serverApi<T>(path: string): Promise<T | undefined> {
  try {
    const response = await fetch(`${backend}${path}`, { next: { revalidate: 300 } });
    return response.ok ? response.json() : undefined;
  } catch {
    return undefined;
  }
}
