import { redirect } from "next/navigation";
import { LiquidacionesInspeccionObraView } from "@/features/liquidaciones/views/LiquidacionesInspeccionObraView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Inspección de Obra — protegida por auth.
 * Ruta: /liquidaciones/inspeccion-obra
 */
export default async function LiquidacionesInspeccionObraPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesInspeccionObraView />;
}
