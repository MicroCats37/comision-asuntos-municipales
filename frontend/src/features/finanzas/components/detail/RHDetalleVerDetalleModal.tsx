"use client";

import type { LucideIcon } from "lucide-react";
import { useLiquidacionGeneralDetalle } from "@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle";
import {
  LiquidacionDetalleModal,
  composeDetalleSections,
} from "@/features/liquidaciones/components/detail/index";
import {
  formatPublicId,
  getTipoSlugFromCodigo,
} from "@/features/liquidaciones/utils/formatPublicId";
import {
  getKindBadgeFromCodigo,
  getKindIconFromCodigo,
} from "@/features/liquidaciones/components/liquidacion-ui";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import type { M2DatosOut } from "@/features/liquidaciones/schemas/liquidacion-m2.schema";
import type { VisitasDatosOut } from "@/features/liquidaciones/schemas/liquidacion-visitas.schema";

interface RHDetalleVerDetalleModalProps {
  liquidacionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Modal reutilizable de "Ver detalle" para las tablas de RH detalle
 * (delegado e inspector). Recibe solo el `liquidacionId`, fetchea el detalle
 * polimórfico y compone las secciones según el tipo de liquidación.
 *
 * Toda la metadata (publicId, estado, tipo, badge, icono) se deriva del
 * detalle fetcheado, NO del row de la lista (que no trae fecha_registro ni estado).
 */
export function RHDetalleVerDetalleModal({
  liquidacionId,
  open,
  onOpenChange,
}: RHDetalleVerDetalleModalProps) {
  const { data: detalle, isLoading } = useLiquidacionGeneralDetalle({
    id: open ? liquidacionId : null,
  });

  const tipoCodigo =
    detalle?.liquidacion_general?.tipo_liquidacion?.codigo ?? null;
  const tipoSlug = getTipoSlugFromCodigo(tipoCodigo);
  const kindBadge = getKindBadgeFromCodigo(tipoCodigo);
  const KindIcon = getKindIconFromCodigo(tipoCodigo) as LucideIcon;

  const publicId = formatPublicId(
    tipoSlug ?? "",
    detalle?.liquidacion_general?.fecha_registro ?? null,
    detalle?.liquidacion_especifica?.numero ?? null,
  );

  const estado = detalle?.liquidacion_general?.estado ?? null;

  return (
    <LiquidacionDetalleModal
      open={open}
      onOpenChange={onOpenChange}
      kindBadge={kindBadge}
      publicId={publicId}
      estado={estado}
      kindIcon={KindIcon}
    >
      {isLoading ? (
        <DetalleSkeleton />
      ) : detalle ? (
        composeDetalleSections({
          lg: detalle.liquidacion_general,
          lt:
            tipoCodigo === "EDIFICACION" ||
            tipoCodigo === "IMPACTO_VIAL" ||
            tipoCodigo === "TALUDES"
              ? (detalle.liquidacion_tipo as PorcentajeObraDatosOut)
              : null,
          m2:
            tipoCodigo === "HABILITACION_URBANA" ||
            tipoCodigo === "MECANICA_SUELOS"
              ? (detalle.liquidacion_tipo as M2DatosOut)
              : null,
          visitas:
            tipoCodigo === "INSPECCION_OBRA"
              ? (detalle.liquidacion_tipo as VisitasDatosOut)
              : null,
        })
      ) : (
        <DetalleError />
      )}
    </LiquidacionDetalleModal>
  );
}

function DetalleSkeleton() {
  return (
    <div className="col-span-12 flex flex-col gap-4 p-8 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 rounded-xl bg-muted/40 border border-border/40"
        />
      ))}
    </div>
  );
}

function DetalleError() {
  return (
    <div className="col-span-12 flex items-center justify-center p-8 text-destructive">
      Error al cargar el detalle de la liquidación
    </div>
  );
}
