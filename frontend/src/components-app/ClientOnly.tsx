"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * ClientOnly — Renderiza children solo después de hydration.
 *
 * Uso: envolver componentes que llaman hooks de React Query (u otros) durante
 * el render inicial, para evitar errores "No QueryClient set" en SSR cuando
 * esos hooks se ejecutan antes de que el provider termine de propagarse.
 *
 * Patrón:
 *   <ClientOnly>
 *     <ModalQueUsaQueryHooks ... />
 *   </ClientOnly>
 *
 * En SSR: retorna `null` (no renderiza el árbol interno).
 * En cliente tras mount: renderiza children.
 *
 * Esto agrega un flash donde el modal es invisible por 1 frame durante la
 * hidratación inicial — aceptable para modales que arrancan con `open=false`.
 */
export function ClientOnly({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  if (!mounted) return null;
  return <>{children}</>;
}