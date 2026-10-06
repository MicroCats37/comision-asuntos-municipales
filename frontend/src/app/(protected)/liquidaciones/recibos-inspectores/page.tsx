import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Recibos de Honorario de Inspectores.
 * Redirige a /mensual (vista mensual agrupada por mes).
 * Ruta: /liquidaciones/recibos-inspectores
 */
export default async function RecibosInspectoresPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  redirect("/liquidaciones/recibos-inspectores/mensual");
}
