/**
 * Vista para lista de Liquidaciones de Mecánica de Suelos.
 * Ruta: /liquidaciones/mecanica-suelos
 */
"use client";

import {
  AlertTriangle as AlertTriangleIcon,
  Eye,
  FileDown,
  FilePenLine,
  type LucideIcon,
  Receipt,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { AreaCell } from "../columns/AreaCell";
import { DelegadosCell } from "../columns/DelegadosCell";
import { TarifaMCell } from "../columns/TarifaMCell";
import { LiquidacionMecanicaSuelosCard } from "../components/cards/LiquidacionMecanicaSuelosCard";
import {
  composeDetalleSections,
  LiquidacionDetalleMecanicaSuelosSection,
  LiquidacionDetalleModal,
} from "../components/detail";
import { ComprobanteFormModal } from "../components/forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../components/forms/EliminarLiquidacionModal";
import { LiquidacionMecanicaSuelosFormModal } from "../components/forms/mecanica-suelos/LiquidacionMecanicaSuelosFormModal";
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
import { useLiquidacionesMecanicaSuelos } from "../hooks/useLiquidacionesMecanicaSuelos";
import { useLiquidacionFiltersUrl } from "../hooks/useLiquidacionFiltersUrl";
import type { UltimaRevisionGeneralItem } from "../hooks/useUltimaRevisionGeneral";
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import type { LiquidacionMecanicaSuelosListItem } from "../schemas/liquidacion-mecanica-suelos.schema";
import { canEditLiquidacion } from "../utils/canEditLiquidacion";
import { formatPublicId } from "../utils/formatPublicId";
import { mapLiquidacionRow } from "../utils/mapLiquidacionRow";

const KIND_ICON: LucideIcon = AlertTriangleIcon;
const TIPO_SLUG = "mecanica-suelos";
const TIPO_PDF = "mecanica-suelos";

function useMsData(): UseLiquidacionListReturn<LiquidacionMecanicaSuelosListItem> {
  const { filtros } = useLiquidacionFiltersUrl();
  return useLiquidacionesMecanicaSuelos(filtros);
}

function buildPdfItem(
  item: LiquidacionMecanicaSuelosListItem,
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

export function LiquidacionesMecanicaSuelosView() {
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [selectPreviaOpen, setSelectPreviaOpen] = useState(false);
  const [nuevaRevisionOpen, setNuevaRevisionOpen] = useState(false);
  const [previa, setPrevia] = useState<UltimaRevisionGeneralItem | null>(null);

  const [detalleItem, setDetalleItem] =
    useState<LiquidacionMecanicaSuelosListItem | null>(null);
  const [delegadosItem, setDelegadosItem] =
    useState<LiquidacionMecanicaSuelosListItem | null>(null);
  const [editItem, setEditItem] =
    useState<LiquidacionMecanicaSuelosListItem | null>(null);
  const [comprobanteItem, setComprobanteItem] =
    useState<LiquidacionMecanicaSuelosListItem | null>(null);
  const [deleteItem, setDeleteItem] =
    useState<LiquidacionMecanicaSuelosListItem | null>(null);

  const buildRowActions = useCallback(
    (item: LiquidacionMecanicaSuelosListItem): LiquidacionRowAction[] => {
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

  const buildExtraColumns =
    (): TableColumn<LiquidacionMecanicaSuelosListItem>[] => [
      {
        key: "area",
        header: "Área",
        width: "minmax(140px,auto)",
        render: (item) => <AreaCell lt={item.liquidacion_tipo} />,
      },
      {
        key: "tarifa",
        header: "Tarifa",
        width: "minmax(160px,auto)",
        render: (item) => (
          <TarifaMCell costo_por_m2={item.liquidacion_tipo.costo_por_m2} />
        ),
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
      <LiquidacionesListContent<LiquidacionMecanicaSuelosListItem>
        icon={KIND_ICON}
        title="Liquidaciones — Mecánica de Suelos"
        description="Listado de liquidaciones de Mecánica de Suelos"
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
        useListData={useMsData}
        renderCard={(item, refetch) => (
          <LiquidacionMecanicaSuelosCard item={item} onUpdated={refetch} />
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

      <LiquidacionMecanicaSuelosFormModal
        mode="create"
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        onSuccess={() => setFormModalOpen(false)}
      />

      <SeleccionarPreviaModal
        open={selectPreviaOpen}
        onOpenChange={setSelectPreviaOpen}
        tiposPermitidos={["MECANICA_SUELOS"]}
        onSelect={(p) => {
          setPrevia(p);
          setSelectPreviaOpen(false);
          setNuevaRevisionOpen(true);
        }}
      />

      {previa && (
        <LiquidacionMecanicaSuelosFormModal
          mode="nueva-revision"
          open={nuevaRevisionOpen}
          onOpenChange={setNuevaRevisionOpen}
          previa={previa as unknown as LiquidacionMecanicaSuelosListItem}
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
          kindBadge="Mecánica de Suelos"
          publicId={detallePublicId ?? ""}
          estado={detalleItem.liquidacion_general.estado}
          kindIcon={AlertTriangleIcon}
        >
          {composeDetalleSections({
            lg: detalleItem.liquidacion_general,
            tipoSection: (
              <LiquidacionDetalleMecanicaSuelosSection
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
        <LiquidacionMecanicaSuelosFormModal
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
