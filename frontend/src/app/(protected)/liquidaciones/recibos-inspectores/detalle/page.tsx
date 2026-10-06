import { redirect } from "next/navigation";
import { RHDetalleInspectoresView } from "@/features/finanzas/views/RHDetalleInspectoresView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de detalle de Recibos de Honorario de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores/detalle
 */
export default async function RecibosInspectoresDetallePage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RHDetalleInspectoresView />;
}
