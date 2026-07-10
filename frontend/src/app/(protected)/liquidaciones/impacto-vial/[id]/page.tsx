"use client";

import { useParams, useRouter } from "next/navigation";
import { Car } from "lucide-react";
import { useLiquidacionDetalleImpactoVial } from "@/features/liquidaciones/hooks/useLiquidacionDetalleImpactoVial";
import {
  LiquidacionDetalleCompleta,
  type LiquidacionCardBase,
} from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";

const KIND_LABEL = "Impacto Vial";

export default function LiquidacionDetalleImpactoVialPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: item, isLoading, isError } = useLiquidacionDetalleImpactoVial({ id });

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
          kindLabel={KIND_LABEL}
          kindIcon={Car}
        />
      </div>
    </div>
  );
}
