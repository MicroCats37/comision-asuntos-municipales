import { redirect } from "next/navigation";
import { LiquidacionesEdificacionesView } from "@/features/liquidaciones/views/LiquidacionesEdificacionesView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Edificaciones (snapshots) - protegida por auth
 * Ruta: /liquidaciones/edificaciones
 */
export default async function LiquidacionesEdificacionesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesEdificacionesView />;
}
