"use client";

import { Triangle } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { LiquidacionDetalleCompleta } from "@/features/liquidaciones/components/LiquidacionDetalleCompleta";
import { useLiquidacionDetalleTaludes } from "@/features/liquidaciones/hooks/useLiquidacionDetalleTaludes";

const KIND_LABEL = "Taludes";

export default function LiquidacionDetalleTaludesPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: item,
    isLoading,
    isError,
  } = useLiquidacionDetalleTaludes({ id });

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
          kindIcon={Triangle}
        />
      </div>
    </div>
  );
}
