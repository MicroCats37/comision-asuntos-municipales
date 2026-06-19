import { redirect } from "next/navigation";
import { LiquidacionesView } from "@/features/liquidaciones/views/LiquidacionesView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Liquidaciones - protegida por auth
 */
export default async function LiquidacionesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <LiquidacionesView />;
}
