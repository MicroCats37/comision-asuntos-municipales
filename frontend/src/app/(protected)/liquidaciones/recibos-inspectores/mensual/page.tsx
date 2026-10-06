import { redirect } from "next/navigation";
import { RecibosInspectoresView } from "@/features/finanzas/views/RecibosInspectoresView";
import { getUserSession } from "@/lib/auth";

/**
 * Página mensual de Recibos de Honorario de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores/mensual
 */
export default async function RecibosInspectoresMensualPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RecibosInspectoresView />;
}
