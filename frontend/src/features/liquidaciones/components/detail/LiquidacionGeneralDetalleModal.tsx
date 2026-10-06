"use client";

import { type LucideIcon } from "lucide-react";
import { useMemo } from "react";
import {
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleHabilitacionUrbanaSection,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleTaludesSection,
} from "./index";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
} from "./index";
import type { LiquidacionGeneralItem } from "@/features/liquidaciones/hooks/useLiquidacionesGenerales";
import { useLiquidacionGeneralDetalle } from "@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle";
import { formatPublicId, getTipoSlugFromCodigo } from "../../utils/formatPublicId";
import { getKindBadgeFromCodigo, getKindIconFromCodigo } from "../liquidacion-ui";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import type { M2DatosOut } from "@/features/liquidaciones/schemas/liquidacion-m2.schema";
import type { VisitasDatosOut } from "@/features/liquidaciones/schemas/liquidacion-visitas.schema";

interface LiquidacionGeneralDetalleModalProps {
  item: LiquidacionGeneralItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Ver detalle" modal for the general (cross-tipo) liquidaciones view.
 * Fetches the full detail data asynchronously and renders the polymorphic
 * tipo-specific section based on `tipo_liquidacion.codigo`.
 */
export function LiquidacionGeneralDetalleModal({
  item,
  open,
  onOpenChange,
}: LiquidacionGeneralDetalleModalProps) {
  const { data: detalle, isLoading } = useLiquidacionGeneralDetalle({
    id: item.liquidacion_general.id,
  });

  // NOTE: tipo_liquidacion type annotation workarounds a TypeScript module-resolution
  // quirk where item.tipo_liquidacion was incorrectly resolved as liquidacion_especifica.
  const tipo_liquidacion: { codigo?: string | null | undefined } | null | undefined =
    item.tipo_liquidacion;
  const tipoCodigo = tipo_liquidacion?.codigo ?? null;
  const tipoSlug = getTipoSlugFromCodigo(tipoCodigo);
  const kindBadge = getKindBadgeFromCodigo(tipoCodigo);
  const KindIcon = getKindIconFromCodigo(tipoCodigo) as LucideIcon;

  const publicId = formatPublicId(
    tipoSlug ?? "",
    item.liquidacion_general.fecha_registro,
    item.liquidacion_especifica?.numero ?? null,
  );

  const tipoSection = useMemo(() => {
    if (!detalle) return null;
    switch (tipoCodigo) {
      case "EDIFICACION":
      case "IMPACTO_VIAL":
      case "TALUDES":
        return (
          <LiquidacionDetalleEdificacionesSection
            liquidacionTipo={detalle.liquidacion_tipo as PorcentajeObraDatosOut}
          />
        );
      case "HABILITACION_URBANA":
      case "MECANICA_SUELOS":
        return (
          <LiquidacionDetalleHabilitacionUrbanaSection
            liquidacionTipo={detalle.liquidacion_tipo as M2DatosOut}
          />
        );
      case "INSPECCION_OBRA":
        return (
          <LiquidacionDetalleInspeccionObraSection
            liquidacionTipo={detalle.liquidacion_tipo as VisitasDatosOut}
          />
        );
      default:
        return null;
    }
  }, [detalle, tipoCodigo]);

  return (
    <LiquidacionDetalleModal
      open={open}
      onOpenChange={onOpenChange}
      kindBadge={kindBadge}
      publicId={publicId}
      estado={item.liquidacion_general.estado}
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
          tipoSection,
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
