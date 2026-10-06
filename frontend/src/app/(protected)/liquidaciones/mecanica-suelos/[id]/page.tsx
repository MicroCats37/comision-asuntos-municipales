"use client";

import { Mountain } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { LiquidacionDetalleCompleta } from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleMecanicaSuelos } from "@/features/liquidaciones/hooks/useLiquidacionDetalleMecanicaSuelos";

const KIND_LABEL = "Mecánica de Suelos";

export default function LiquidacionDetalleMecanicaSuelosPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleMecanicaSuelos({ id });

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
          kindIcon={Mountain}
        />
      </div>
    </div>
  );
}
