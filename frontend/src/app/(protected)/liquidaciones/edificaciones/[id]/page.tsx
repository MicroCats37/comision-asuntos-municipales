"use client";

import { FileText } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import {
  kindLabel,
  LiquidacionDetalleCompleta,
} from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleEdificacion } from "@/features/liquidaciones/hooks/useLiquidacionDetalleEdificacion";

const KIND_LABEL = "Edificación";

export default function LiquidacionDetalleEdificacionPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleEdificacion({ id });

  const handleBack = () => {
    router.back();
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <LiquidacionDetalleCompleta
          item={item}
          isLoading={isLoading}
          isError={isError}
          onBack={handleBack}
          kindLabel={
            kindLabel(item?.liquidacion_general?.tipo_liquidacion?.codigo) ??
            KIND_LABEL
          }
          kindIcon={FileText}
        />
      </div>
    </div>
  );
}
