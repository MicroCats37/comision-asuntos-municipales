"use client";

import { ClipboardCheck } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { LiquidacionDetalleCompleta } from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleInspeccionObra } from "@/features/liquidaciones/hooks/useLiquidacionDetalleInspeccionObra";

const KIND_LABEL = "Inspección de Obra";

export default function LiquidacionDetalleInspeccionObraPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleInspeccionObra({ id });

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
          kindLabel={KIND_LABEL}
          kindIcon={ClipboardCheck}
        />
      </div>
    </div>
  );
}
