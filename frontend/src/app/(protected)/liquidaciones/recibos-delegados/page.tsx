import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Recibos de Honorario de Delegados.
 * Redirige a /mensual (vista mensual agrupada por mes).
 * Ruta: /liquidaciones/recibos-delegados
 */
export default async function RecibosDelegadosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  redirect("/liquidaciones/recibos-delegados/mensual");
}
