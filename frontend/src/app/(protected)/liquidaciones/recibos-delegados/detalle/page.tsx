import { redirect } from "next/navigation";
import { RHDetalleDelegadosView } from "@/features/finanzas/views/RHDetalleDelegadosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de detalle de Recibos de Honorario de Delegados.
 * Ruta: /liquidaciones/recibos-delegados/detalle
 */
export default async function RecibosDelegadosDetallePage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RHDetalleDelegadosView />;
}
