import { redirect } from "next/navigation";
import { TarifasView } from "@/features/finanzas/views/TarifasView";
import { getUserSession } from "@/lib/auth";

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
