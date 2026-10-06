import { redirect } from "next/navigation";
import { LiquidacionesImpactoVialView } from "@/features/liquidaciones/views/LiquidacionesImpactoVialView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Impacto Vial — protegida por auth.
 * Ruta: /liquidaciones/impacto-vial
 */
export default async function LiquidacionesImpactoVialPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesImpactoVialView />;
}
