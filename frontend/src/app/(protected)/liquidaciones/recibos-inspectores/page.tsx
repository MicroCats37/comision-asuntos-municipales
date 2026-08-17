import { redirect } from "next/navigation";
import { RecibosInspectoresView } from "@/features/finanzas/views/RecibosInspectoresView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Recibos de Honorario de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores
 */
export default async function RecibosInspectoresPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RecibosInspectoresView />;
}
