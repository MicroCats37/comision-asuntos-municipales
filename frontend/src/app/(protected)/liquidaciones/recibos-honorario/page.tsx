import { redirect } from "next/navigation";
import { ReciboHonorariosView } from "@/features/finanzas/views/ReciboHonorariosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Recibos de Honorario.
 * Ruta: /liquidaciones/recibos-honorario
 */
export default async function RecibosHonorarioPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <ReciboHonorariosView />;
}
