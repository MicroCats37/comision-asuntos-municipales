"use client";

import { Home } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { LiquidacionDetalleCompleta } from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleHabilitacionUrbana } from "@/features/liquidaciones/hooks/useLiquidacionDetalleHabilitacionUrbana";

const KIND_LABEL = "Habilitación Urbana";

export default function LiquidacionDetalleHabilitacionUrbanaPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleHabilitacionUrbana({ id });

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
          kindIcon={Home}
        />
      </div>
    </div>
  );
}
