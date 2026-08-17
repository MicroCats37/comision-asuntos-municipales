import { redirect } from "next/navigation";
import { RecibosDelegadosView } from "@/features/finanzas/views/RecibosDelegadosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Recibos de Honorario de Delegados.
 * Ruta: /liquidaciones/recibos-delegados
 */
export default async function RecibosDelegadosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RecibosDelegadosView />;
}
