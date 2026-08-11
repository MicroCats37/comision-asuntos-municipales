import { redirect } from "next/navigation";
import { InspectoresView } from "@/features/inspectores/views/InspectoresView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Inspectores — protegida por auth
 * Ruta: /liquidaciones/inspectores
 */
export default async function InspectoresPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <InspectoresView />;
}
