import { redirect } from "next/navigation";
import { ProyectosView } from "@/features/proyectos/views/ProyectosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Proyectos - protegida por auth.
 *
 * Lista proyectos con liquidaciones de edificaciones usando paginación.
 * Endpoint: GET /api/proyectos/?page=&page_size=
 */
export default async function ProyectosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="page-section">
      <ProyectosView />
    </div>
  );
}
