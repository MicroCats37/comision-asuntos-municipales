/**
 * Vista para lista de Liquidaciones de Taludes.
 * Ruta: /liquidaciones/taludes
 */
"use client";

import {
  Eye,
  FileDown,
  FilePenLine,
  type LucideIcon,
  Mountain as MountainIcon,
  Receipt,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { DelegadosCell } from "../columns/DelegadosCell";
import { PorcentajeCell } from "../columns/PorcentajeCell";
import { ValorObraCell } from "../columns/ValorObraCell";
import { LiquidacionTaludesCard } from "../components/cards/LiquidacionTaludesCard";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
  LiquidacionDetalleTaludesSection,
} from "../components/detail";
import { ComprobanteFormModal } from "../components/forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../components/forms/EliminarLiquidacionModal";
import { LiquidacionTaludesFormModal } from "../components/forms/taludes/LiquidacionTaludesFormModal";
import { SeleccionarPreviaModal } from "../components/forms/SeleccionarPreviaModal";
import { GestionarDelegadosModal } from "../components/GestionarDelegadosModal";
import {
  LiquidacionesListContent,
  NuevaLiquidacionButton,
  type UseLiquidacionListReturn,
} from "../components/LiquidacionesListContent";
import type { TableColumn } from "../components/tables/LiquidacionesTable";
import type { LiquidacionRowAction } from "../components/tables/LiquidacionesTableRowActions";
import { LiquidacionesTableRowActions } from "../components/tables/LiquidacionesTableRowActions";
import { useLiquidacionesTaludes } from "../hooks/useLiquidacionesTaludes";
import { useLiquidacionFiltersUrl } from "../hooks/useLiquidacionFiltersUrl";
import type { UltimaRevisionGeneralItem } from "../hooks/useUltimaRevisionGeneral";
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import type { LiquidacionTaludesListItem } from "../schemas/liquidacion-taludes.schema";
import { canEditLiquidacion } from "../utils/canEditLiquidacion";
import { formatPublicId } from "../utils/formatPublicId";
import { mapLiquidacionRow } from "../utils/mapLiquidacionRow";

const KIND_ICON: LucideIcon = MountainIcon;
const TIPO_SLUG = "taludes";
const TIPO_PDF = "taludes";

function useTaludesData(): UseLiquidacionListReturn<LiquidacionTaludesListItem> {
  const { filtros } = useLiquidacionFiltersUrl();
  return useLiquidacionesTaludes(filtros);
}

function buildPdfItem(item: LiquidacionTaludesListItem): PdfLiquidacionItem {
  return {
    liquidacion_general:
      item.liquidacion_general as PdfLiquidacionItem["liquidacion_general"],
    liquidacion_especifica:
      item.liquidacion_especifica as PdfLiquidacionItem["liquidacion_especifica"],
    liquidacion_tipo:
      item.liquidacion_tipo as PdfLiquidacionItem["liquidacion_tipo"],
  };
}

export function LiquidacionesTaludesView() {
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [selectPreviaOpen, setSelectPreviaOpen] = useState(false);
  const [nuevaRevisionOpen, setNuevaRevisionOpen] = useState(false);
  const [previa, setPrevia] = useState<UltimaRevisionGeneralItem | null>(null);

  const [detalleItem, setDetalleItem] =
    useState<LiquidacionTaludesListItem | null>(null);
  const [delegadosItem, setDelegadosItem] =
    useState<LiquidacionTaludesListItem | null>(null);
  const [editItem, setEditItem] = useState<LiquidacionTaludesListItem | null>(
    null,
  );
  const [comprobanteItem, setComprobanteItem] =
    useState<LiquidacionTaludesListItem | null>(null);
  const [deleteItem, setDeleteItem] =
    useState<LiquidacionTaludesListItem | null>(null);

  const buildRowActions = useCallback(
    (item: LiquidacionTaludesListItem): LiquidacionRowAction[] => {
      const lg = item.liquidacion_general;
      const editState = canEditLiquidacion(lg);
      const comprobanteActivo = lg.comprobantes?.find((c) => c.activo) ?? null;
      return [
        {
          icon: Eye,
          label: "Ver detalle",
          onAction: () => setDetalleItem(item),
          variant: "primary",
        },
        {
          icon: Users,
          label: "Gestionar delegados",
          onAction: () => setDelegadosItem(item),
        },
        {
          icon: FileDown,
          label: "Descargar PDF",
          onAction: () => printLiquidacionPreview(buildPdfItem(item), TIPO_PDF),
        },
        ...(editState.canEdit
          ? [
              {
                icon: FilePenLine,
                label: "Editar",
                onAction: () => setEditItem(item),
              } satisfies LiquidacionRowAction,
              {
                icon: Trash2,
                label: "Eliminar",
                onAction: () => setDeleteItem(item),
              } satisfies LiquidacionRowAction,
            ]
          : []),
        {
          icon: Receipt,
          label: comprobanteActivo
            ? "Reemplazar comprobante"
            : "Agregar comprobante",
          onAction: () => setComprobanteItem(item),
        },
      ];
    },
    [],
  );

  const detallePublicId =
    detalleItem &&
    formatPublicId(
      TIPO_SLUG,
      detalleItem.liquidacion_general.fecha_registro,
      detalleItem.liquidacion_especifica.numero,
    );

  const buildExtraColumns = (): TableColumn<LiquidacionTaludesListItem>[] => [
    {
      key: "pct",
      header: "% Liq.",
      width: "120px",
      render: (item) => <PorcentajeCell lt={item.liquidacion_tipo} />,
    },
    {
      key: "valor",
      header: "Valor de Obra",
      width: "150px",
      render: (item) => <ValorObraCell lt={item.liquidacion_tipo} />,
    },
    {
      key: "delegados",
      header: "Delegados",
      width: "minmax(220px,1fr)",
      render: (item) => (
        <DelegadosCell delegados={item.liquidacion_general.delegados} />
      ),
    },
  ];

  return (
    <>
      <LiquidacionesListContent<LiquidacionTaludesListItem>
        icon={KIND_ICON}
        title="Liquidaciones — Taludes"
        description="Listado de liquidaciones de Taludes"
        primaryAction={
          <NuevaLiquidacionButton onClick={() => setFormModalOpen(true)} />
        }
        extraAction={
          <Button
            variant="outline"
            className="gap-2 h-10 rounded-xl font-semibold shrink-0"
            onClick={() => setSelectPreviaOpen(true)}
          >
            <RefreshCw className="h-4 w-4" />
            Tercera Revisión
          </Button>
        }
        useListData={useTaludesData}
        renderCard={(item, refetch) => (
          <LiquidacionTaludesCard item={item} onUpdated={refetch} />
        )}
        formatRow={(item) =>
          mapLiquidacionRow(
            TIPO_SLUG,
            item.liquidacion_general,
            item.liquidacion_especifica.numero,
          )
        }
        extraColumns={buildExtraColumns()}
        renderRowActions={(item) => (
          <LiquidacionesTableRowActions actions={buildRowActions(item)} />
        )}
      />

      <LiquidacionTaludesFormModal
        mode="create"
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        onSuccess={() => setFormModalOpen(false)}
      />

      <SeleccionarPreviaModal
        open={selectPreviaOpen}
        onOpenChange={setSelectPreviaOpen}
        tiposPermitidos={["TALUDES"]}
        onSelect={(p) => {
          setPrevia(p);
          setSelectPreviaOpen(false);
          setNuevaRevisionOpen(true);
        }}
      />

      {previa && (
        <LiquidacionTaludesFormModal
          mode="nueva-revision"
          open={nuevaRevisionOpen}
          onOpenChange={setNuevaRevisionOpen}
          previa={previa as unknown as LiquidacionTaludesListItem}
          onSuccess={() => {
            setNuevaRevisionOpen(false);
            setPrevia(null);
          }}
        />
      )}

      {detalleItem && (
        <LiquidacionDetalleModal
          open
          onOpenChange={(open) => {
            if (!open) setDetalleItem(null);
          }}
          kindBadge="Taludes"
          publicId={detallePublicId ?? ""}
          estado={detalleItem.liquidacion_general.estado}
          kindIcon={MountainIcon}
        >
          {composeDetalleSections({
            lg: detalleItem.liquidacion_general,
            lt: detalleItem.liquidacion_tipo,
            tipoSection: (
              <LiquidacionDetalleTaludesSection
                liquidacionTipo={detalleItem.liquidacion_tipo}
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}

      {delegadosItem && (
        <GestionarDelegadosModal
          open
          onOpenChange={(open) => {
            if (!open) setDelegadosItem(null);
          }}
          liquidacionGeneral={delegadosItem.liquidacion_general}
        />
      )}

      {editItem && (
        <LiquidacionTaludesFormModal
          mode="edit"
          open
          onOpenChange={(open) => {
            if (!open) setEditItem(null);
          }}
          item={editItem}
          onSuccess={() => setEditItem(null)}
        />
      )}

      {comprobanteItem && (
        <ComprobanteFormModal
          open
          onOpenChange={(open) => {
            if (!open) setComprobanteItem(null);
          }}
          liquidacionGeneral={comprobanteItem.liquidacion_general}
          onSuccess={() => setComprobanteItem(null)}
        />
      )}

      {deleteItem && (
        <EliminarLiquidacionModal
          open
          onOpenChange={(open) => {
            if (!open) setDeleteItem(null);
          }}
          liquidacion={{
            id: deleteItem.liquidacion_general.id,
            publicId: formatPublicId(
              TIPO_SLUG,
              deleteItem.liquidacion_general.fecha_registro,
              deleteItem.liquidacion_especifica.numero,
            ),
          }}
          entidadNombre={
            deleteItem.liquidacion_general.proyecto.entidad?.razon_social ??
            deleteItem.liquidacion_general.proyecto.nombre_propietario ??
            undefined
          }
          onSuccess={() => setDeleteItem(null)}
        />
      )}
    </>
  );
}
