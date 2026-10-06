import { redirect } from "next/navigation";
import { RHReparticionesEstacionalesView } from "@/features/finanzas/views/RHReparticionesEstacionalesView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Reparticiones Estacionales.
 * Ruta: /liquidaciones/reparticiones-estacionales
 */
export default async function ReparticionesEstacionalesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <RHReparticionesEstacionalesView />;
}
