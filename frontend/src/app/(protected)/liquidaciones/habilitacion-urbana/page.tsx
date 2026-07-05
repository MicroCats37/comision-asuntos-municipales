import { redirect } from "next/navigation";
import { LiquidacionesHabilitacionUrbanaView } from "@/features/liquidaciones/views/LiquidacionesHabilitacionUrbanaView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Habilitación Urbana — protegida por auth.
 * Ruta: /liquidaciones/habilitacion-urbana
 */
export default async function LiquidacionesHabilitacionUrbanaPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesHabilitacionUrbanaView />;
}
