"use client";

import { useParams } from "next/navigation";
import { RHReparticionEstacionalDetalleView } from "@/features/finanzas/views/RHReparticionEstacionalDetalleView";

export default function ReparticionEstacionalDetallePage() {
  const params = useParams();
  const id = params.id as string;

  return <RHReparticionEstacionalDetalleView reparticionId={id} />;
}
