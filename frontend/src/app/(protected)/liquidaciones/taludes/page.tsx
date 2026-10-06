import { redirect } from "next/navigation";
import { LiquidacionesTaludesView } from "@/features/liquidaciones/views/LiquidacionesTaludesView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones de Taludes — protegida por auth.
 * Ruta: /liquidaciones/taludes
 */
export default async function LiquidacionesTaludesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesTaludesView />;
}
