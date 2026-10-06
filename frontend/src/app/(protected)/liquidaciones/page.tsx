import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";

/**
 * Redirect to /liquidaciones/edificaciones (same as login flow).
 * Ruta: /liquidaciones
 */
export default async function LiquidacionesPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  redirect("/liquidaciones/edificaciones");
}
