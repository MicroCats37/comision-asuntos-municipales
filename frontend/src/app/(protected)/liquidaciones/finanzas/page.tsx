import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";
import { TarifasView } from "@/features/finanzas/views/TarifasView";

/**
 * Página de Finanzas — Tarifas Históricas.
 * Ruta: /liquidaciones/finanzas
 */
export default async function FinanzasPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <TarifasView />;
}
