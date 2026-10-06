/**
 * Vista para lista de Liquidaciones Generales (todas las liquidaciones).
 * Ruta: /liquidaciones/generales
 *
 * Usa el chrome compartido `LiquidacionesListContent` (URL state,
 * view toggle, pagination, cards/table). La vista "Ver detalle" es
 * polimórfica — usa `LiquidacionGeneralDetalleModal` que fetch-ea el
 * detalle completo por tipo y renderiza la sección tipo-específica.
 */
"use client";

import { Eye, FileText, type LucideIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { ClientOnly } from "@/components-app/ClientOnly";
import { LiquidacionGeneralDetalleModal } from "../components/detail/LiquidacionGeneralDetalleModal";
import {
  LiquidacionesListContent,
  type UseLiquidacionListReturn,
} from "../components/LiquidacionesListContent";
import type { LiquidacionRowAction } from "../components/tables/LiquidacionesTableRowActions";
import { LiquidacionesTableRowActions } from "../components/tables/LiquidacionesTableRowActions";
import { useLiquidacionesGenerales } from "../hooks/useLiquidacionesGenerales";
import type { LiquidacionGeneralItem } from "../hooks/useLiquidacionesGenerales";
import { getTipoSlugFromCodigo } from "../utils/formatPublicId";
import { mapLiquidacionRow } from "../utils/mapLiquidacionRow";

const KIND_ICON: LucideIcon = FileText;

function useGeneralesData(): UseLiquidacionListReturn<LiquidacionGeneralItem> {
  return useLiquidacionesGenerales() as UseLiquidacionListReturn<LiquidacionGeneralItem>;
}

export function LiquidacionesGeneralesView() {
  const [detalleItem, setDetalleItem] =
    useState<LiquidacionGeneralItem | null>(null);

  const buildRowActions = useCallback(
    (item: LiquidacionGeneralItem): LiquidacionRowAction[] => {
      return [
        {
          icon: Eye,
          label: "Ver detalle",
          onAction: () => setDetalleItem(item),
          variant: "primary",
        },
      ];
    },
    [],
  );

  return (
    <>
      <LiquidacionesListContent<LiquidacionGeneralItem>
        icon={KIND_ICON}
        title="Liquidaciones — Generales"
        description="Listado general de todas las liquidaciones"
        primaryAction={undefined}
        useListData={useGeneralesData}
        renderCard={() => null}
        formatRow={(item) => {
          // NOTE: workaround for TypeScript incorrectly resolving tipo_liquidacion
          // as liquidacion_especifica type in some module resolution scenarios.
          const tipoCodigo = (item.tipo_liquidacion as { codigo?: string | null | undefined } | null | undefined)?.codigo ?? null;
          return mapLiquidacionRow(
            getTipoSlugFromCodigo(tipoCodigo),
            item.liquidacion_general,
            item.liquidacion_especifica?.numero ?? null,
          );
        }}
        extraColumns={[]}
        renderRowActions={(item) => (
          <LiquidacionesTableRowActions actions={buildRowActions(item)} />
        )}
      />

      <ClientOnly>
        {detalleItem && (
          <LiquidacionGeneralDetalleModal
            item={detalleItem}
            open
            onOpenChange={(open: boolean) => {
              if (!open) setDetalleItem(null);
            }}
          />
        )}
      </ClientOnly>
    </>
  );
}
