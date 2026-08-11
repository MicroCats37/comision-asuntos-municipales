import { redirect } from "next/navigation";
import { DelegadosView } from "@/features/delegados/views/DelegadosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Delegados — protegida por auth
 * Ruta: /liquidaciones/delegados
 */
export default async function DelegadosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return <DelegadosView />;
}
