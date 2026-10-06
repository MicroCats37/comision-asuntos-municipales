"use client";

import { Car } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { LiquidacionDetalleCompleta } from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleImpactoVial } from "@/features/liquidaciones/hooks/useLiquidacionDetalleImpactoVial";

const KIND_LABEL = "Impacto Vial";

export default function LiquidacionDetalleImpactoVialPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleImpactoVial({ id });

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
          kindIcon={Car}
        />
      </div>
    </div>
  );
}
