"use client";

import { useEffect, type ReactNode } from "react";
import { useCasaVivaStore } from "@/stores/casaviva-store";

export function DataProvider({ children }: { children: ReactNode }) {
  const initialize = useCasaVivaStore((s) => s.initialize);
  useEffect(() => { void initialize(); }, [initialize]);
  return children;
}
