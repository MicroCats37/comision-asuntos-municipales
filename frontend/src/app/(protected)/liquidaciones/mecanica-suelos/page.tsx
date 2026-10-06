import { redirect } from "next/navigation";
import { LiquidacionesMecanicaSuelosView } from "@/features/liquidaciones/views/LiquidacionesMecanicaSuelosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Mecánica de Suelos — protegida por auth.
 * Ruta: /liquidaciones/mecanica-suelos
 */
export default async function LiquidacionesMecanicaSuelosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesMecanicaSuelosView />;
}
