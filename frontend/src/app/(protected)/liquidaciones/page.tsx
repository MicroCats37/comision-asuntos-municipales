import { redirect } from "next/navigation";
import { LiquidacionesGeneralesView } from "@/features/liquidaciones/views/LiquidacionesGeneralesView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones Generales - protegida por auth
 * Ruta: /liquidaciones
 */
export default async function LiquidacionesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesGeneralesView />;
}
