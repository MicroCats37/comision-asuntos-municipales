"use client";

import { useParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useLiquidacionDetalleEdificacion } from "@/features/liquidaciones/hooks/useLiquidacionDetalleEdificacion";
import {
  LiquidacionDetalleCompleta,
  kindLabel,
  type LiquidacionCardBase,
} from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";

const KIND_LABEL = "Edificación";

export default function LiquidacionDetalleEdificacionPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: item, isLoading, isError } = useLiquidacionDetalleEdificacion({ id });

  const handleBack = () => {
    router.back();
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <LiquidacionDetalleCompleta
          item={item as unknown as LiquidacionCardBase | null}
          isLoading={isLoading}
          isError={isError}
          onBack={handleBack}
          kindLabel={kindLabel(item?.tipo_liquidacion) ?? KIND_LABEL}
          kindIcon={FileText}
        />
      </div>
    </div>
  );
}
