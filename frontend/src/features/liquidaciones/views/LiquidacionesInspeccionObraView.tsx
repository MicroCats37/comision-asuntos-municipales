/**
 * Vista para lista de Liquidaciones de Inspección de Obra.
 * Ruta: /liquidaciones/inspeccion-obra
 *
 * Flujo de creación (gateway único):
 *  - "Nueva Liquidación" abre InspeccionObraNuevaLiquidacionChoiceModal
 *  - "Sin previa"  → LiquidacionInspeccionObraFormModal mode='create'
 *  - "Con previa"  → SeleccionarPreviaModal → LiquidacionInspeccionObraFormModal mode='relacionada'
 *
 * Tabla: NO incluye la acción "Delegados" — Inspección de Obra tiene flujo
 * propio de asignación de inspectores, no delegados.
 */
"use client";

import {
  ClipboardCheck as ClipboardCheckIcon,
  Eye,
  FileDown,
  FilePenLine,
  type LucideIcon,
  Receipt,
  Trash2,
} from "lucide-react";
import { useCallback, useState } from "react";
import { CostoPorVisitaCell } from "../columns/CostoPorVisitaCell";
import { InspectoresCell } from "../columns/InspectoresCell";
import { VisitasCell } from "../columns/VisitasCell";
import { VisitasPorcentajeCell } from "../columns/VisitasPorcentajeCell";
import { LiquidacionInspeccionObraCard } from "../components/cards/LiquidacionInspeccionObraCard";
import {
  composeDetalleSections,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleModal,
} from "../components/detail";
import { ComprobanteFormModal } from "../components/forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../components/forms/EliminarLiquidacionModal";
import { InspeccionObraNuevaLiquidacionChoiceModal } from "../components/forms/InspeccionObraNuevaLiquidacionChoiceModal";
import { LiquidacionInspeccionObraFormModal } from "../components/forms/inspeccion-obra/LiquidacionInspeccionObraFormModal";
import { SeleccionarPreviaModal } from "../components/forms/SeleccionarPreviaModal";
import {
  LiquidacionesListContent,
  NuevaLiquidacionButton,
  type UseLiquidacionListReturn,
} from "../components/LiquidacionesListContent";
import type { TableColumn } from "../components/tables/LiquidacionesTable";
import type { LiquidacionRowAction } from "../components/tables/LiquidacionesTableRowActions";
import { LiquidacionesTableRowActions } from "../components/tables/LiquidacionesTableRowActions";
import { useLiquidacionesInspeccionObra } from "../hooks/useLiquidacionesInspeccionObra";
import { useLiquidacionFiltersUrl } from "../hooks/useLiquidacionFiltersUrl";
import type { UltimaRevisionGeneralItem } from "../hooks/useUltimaRevisionGeneral";
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import type { LiquidacionInspeccionObraListItem } from "../schemas/liquidacion-inspeccion-obra.schema";
import { canEditLiquidacion } from "../utils/canEditLiquidacion";
import { formatPublicId } from "../utils/formatPublicId";
import { mapLiquidacionRow } from "../utils/mapLiquidacionRow";

const KIND_ICON: LucideIcon = ClipboardCheckIcon;
const TIPO_SLUG = "inspeccion-obra";
const TIPO_PDF = "inspeccion-obra";

function useIoData(): UseLiquidacionListReturn<LiquidacionInspeccionObraListItem> {
  const { filtros } = useLiquidacionFiltersUrl();
  return useLiquidacionesInspeccionObra(filtros);
}

function buildPdfItem(
  item: LiquidacionInspeccionObraListItem,
): PdfLiquidacionItem {
  return {
    liquidacion_general:
      item.liquidacion_general as PdfLiquidacionItem["liquidacion_general"],
    liquidacion_especifica:
      item.liquidacion_especifica as PdfLiquidacionItem["liquidacion_especifica"],
    liquidacion_tipo:
      item.liquidacion_tipo as PdfLiquidacionItem["liquidacion_tipo"],
  };
}

export function LiquidacionesInspeccionObraView() {
  const [choiceOpen, setChoiceOpen] = useState(false);
  const [selectPreviaOpen, setSelectPreviaOpen] = useState(false);
  const [relacionadaOpen, setRelacionadaOpen] = useState(false);
  const [createSinPreviaOpen, setCreateSinPreviaOpen] = useState(false);
  const [previa, setPrevia] = useState<UltimaRevisionGeneralItem | null>(null);

  const [detalleItem, setDetalleItem] =
    useState<LiquidacionInspeccionObraListItem | null>(null);
  const [editItem, setEditItem] =
    useState<LiquidacionInspeccionObraListItem | null>(null);
  const [comprobanteItem, setComprobanteItem] =
    useState<LiquidacionInspeccionObraListItem | null>(null);
  const [deleteItem, setDeleteItem] =
    useState<LiquidacionInspeccionObraListItem | null>(null);

  const buildRowActions = useCallback(
    (item: LiquidacionInspeccionObraListItem): LiquidacionRowAction[] => {
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

  const buildExtraColumns =
    (): TableColumn<LiquidacionInspeccionObraListItem>[] => [
      {
        key: "visitas",
        header: "Visitas",
        width: "minmax(140px,auto)",
        render: (item) => <VisitasCell lt={item.liquidacion_tipo} />,
      },
      {
        key: "porcentaje",
        header: "% Visita",
        width: "minmax(120px,auto)",
        render: (item) => (
          <VisitasPorcentajeCell
            porcentaje_uit={item.liquidacion_tipo.porcentaje_uit}
          />
        ),
      },
      {
        key: "costo",
        header: "Costo / Visita",
        width: "minmax(140px,auto)",
        render: (item) => (
          <CostoPorVisitaCell
            uit={item.liquidacion_general.uit?.valor}
            porcentaje_uit={item.liquidacion_tipo.porcentaje_uit}
          />
        ),
      },
      {
        key: "inspectores",
        header: "Inspectores",
        width: "minmax(220px,1fr)",
        render: (item) => (
          <InspectoresCell inspectores={item.liquidacion_tipo.inspectores} />
        ),
      },
    ];

  return (
    <>
      <LiquidacionesListContent<LiquidacionInspeccionObraListItem>
        icon={KIND_ICON}
        title="Liquidaciones — Inspección de Obra"
        description="Listado de liquidaciones de Inspección de Obra"
        primaryAction={
          <NuevaLiquidacionButton onClick={() => setChoiceOpen(true)}>
            Nueva Liquidación
          </NuevaLiquidacionButton>
        }
        useListData={useIoData}
        renderCard={(item, refetch) => (
          <LiquidacionInspeccionObraCard item={item} onUpdated={refetch} />
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

      <InspeccionObraNuevaLiquidacionChoiceModal
        open={choiceOpen}
        onOpenChange={setChoiceOpen}
        onChoose={(kind) => {
          setChoiceOpen(false);
          if (kind === "con-previa") setSelectPreviaOpen(true);
          else setCreateSinPreviaOpen(true);
        }}
      />

      <SeleccionarPreviaModal
        open={selectPreviaOpen}
        onOpenChange={setSelectPreviaOpen}
        tiposPermitidos={["EDIFICACION", "HABILITACION_URBANA"]}
        title="Nueva Liquidación"
        description="Busca la liquidación previa (Edificación o Habilitación Urbana) para crear la primera liquidación de Inspección de Obra"
        onCreateSinPrevia={() => setCreateSinPreviaOpen(true)}
        onSelect={(p) => {
          setPrevia(p);
          setSelectPreviaOpen(false);
          setRelacionadaOpen(true);
        }}
      />

      {previa && (
        <LiquidacionInspeccionObraFormModal
          mode="relacionada"
          open={relacionadaOpen}
          onOpenChange={setRelacionadaOpen}
          previa={previa}
          onSuccess={() => {
            setRelacionadaOpen(false);
            setPrevia(null);
          }}
        />
      )}

      <LiquidacionInspeccionObraFormModal
        mode="create"
        open={createSinPreviaOpen}
        onOpenChange={setCreateSinPreviaOpen}
        onSuccess={() => {
          setCreateSinPreviaOpen(false);
        }}
      />

      {detalleItem && (
        <LiquidacionDetalleModal
          open
          onOpenChange={(open) => {
            if (!open) setDetalleItem(null);
          }}
          kindBadge="Inspección de Obra"
          publicId={detallePublicId ?? ""}
          estado={detalleItem.liquidacion_general.estado}
          kindIcon={ClipboardCheckIcon}
        >
          {composeDetalleSections({
            lg: detalleItem.liquidacion_general,
            tipoSection: (
              <LiquidacionDetalleInspeccionObraSection
                liquidacionTipo={detalleItem.liquidacion_tipo}
              />
            ),
            showDelegados: false,
          })}
        </LiquidacionDetalleModal>
      )}

      {editItem && (
        <LiquidacionInspeccionObraFormModal
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
