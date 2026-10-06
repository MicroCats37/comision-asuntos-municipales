/**
 * Vista para lista de Liquidaciones de Edificaciones.
 * Ruta: /liquidaciones/edificaciones
 *
 * Usa el chrome compartido `LiquidacionesListContent` (URL state,
 * view toggle, pagination, cards/table). Los modales viven como siblings:
 * - Form modals son específicos de Edificaciones (Nueva / Tercera revisión).
 * - Detail / delegados / edit / comprobante modals están LIFTED para ser
 *   disparados desde la columna Actions de la vista Tabla. En Cards, los
 *   modales viven dentro de cada card y la state lifted nunca se activa.
 */
"use client";

import {
  Building2,
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
import { ClientOnly } from "@/components-app/ClientOnly";
import { DelegadosCell } from "../columns/DelegadosCell";
import { PorcentajeCell } from "../columns/PorcentajeCell";
import { TarifaCell } from "../columns/TarifaCell";
import { ValorObraCell } from "../columns/ValorObraCell";
import { LiquidacionEdificacionesCard } from "../components/cards/LiquidacionEdificacionesCard";
import {
  composeDetalleSections,
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleModal,
} from "../components/detail";
import { ComprobanteFormModal } from "../components/forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../components/forms/EliminarLiquidacionModal";
import { LiquidacionEdificacionFormModal } from "../components/forms/edificacion/LiquidacionEdificacionFormModal";
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
import { useLiquidacionesEdificaciones } from "../hooks/useLiquidacionesEdificaciones";
import { useLiquidacionFiltersUrl } from "../hooks/useLiquidacionFiltersUrl";
import type { UltimaRevisionGeneralItem } from "../hooks/useUltimaRevisionGeneral";
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import type { LiquidacionEdificacionesListItem } from "../schemas/liquidacion-edificaciones.schema";
import { canEditLiquidacion } from "../utils/canEditLiquidacion";
import { formatPublicId } from "../utils/formatPublicId";
import { mapLiquidacionRow } from "../utils/mapLiquidacionRow";

const TIPO_TRAMITE_LABELS: Record<string, string> = {
  OBRA_NUEVA: "Obra Nueva",
  DEMOLICION: "Demolición",
  AMPLIACION: "Ampliación",
  REMODELACION: "Remodelación",
  MODIFICACION_LICENCIA: "Modificación",
  REINTEGRO: "Reintegro",
  PROYECTO_CON_PLANTAS_TIPICAS: "Plantas Típicas",
};

const KIND_ICON: LucideIcon = Building2;
const TIPO_SLUG = "edificacion";
const TIPO_PDF = "edificacion";

function useEdificacionesData(): UseLiquidacionListReturn<LiquidacionEdificacionesListItem> {
  const { filtros } = useLiquidacionFiltersUrl();
  return useLiquidacionesEdificaciones(filtros);
}

function buildPdfItem(
  item: LiquidacionEdificacionesListItem,
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

export function LiquidacionesEdificacionesView() {
  // Form modals (Edificaciones-specific).
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [selectPreviaOpen, setSelectPreviaOpen] = useState(false);
  const [nuevaRevisionOpen, setNuevaRevisionOpen] = useState(false);
  const [previa, setPrevia] = useState<UltimaRevisionGeneralItem | null>(null);

  // Lifted modals — fired by Table view's row actions.
  const [detalleItem, setDetalleItem] =
    useState<LiquidacionEdificacionesListItem | null>(null);
  const [delegadosItem, setDelegadosItem] =
    useState<LiquidacionEdificacionesListItem | null>(null);
  const [editItem, setEditItem] =
    useState<LiquidacionEdificacionesListItem | null>(null);
  const [comprobanteItem, setComprobanteItem] =
    useState<LiquidacionEdificacionesListItem | null>(null);
  const [deleteItem, setDeleteItem] =
    useState<LiquidacionEdificacionesListItem | null>(null);

  const buildRowActions = useCallback(
    (item: LiquidacionEdificacionesListItem): LiquidacionRowAction[] => {
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
    (): TableColumn<LiquidacionEdificacionesListItem>[] => [
      {
        key: "pct",
        header: "% Liq.",
        width: "120px",
        render: (item) => {
          const tipoTramite = item.liquidacion_tipo.tipo_tramite ?? undefined;
          const label = tipoTramite
            ? TIPO_TRAMITE_LABELS[tipoTramite]
            : undefined;
          return (
            <PorcentajeCell
              lt={item.liquidacion_tipo}
              tipoTramiteLabel={label}
            />
          );
        },
      },
      {
        key: "valor",
        header: "Valor de Obra",
        width: "150px",
        render: (item) => <ValorObraCell lt={item.liquidacion_tipo} />,
      },
      {
        key: "tarifa",
        header: "Tarifas",
        width: "minmax(200px,1fr)",
        render: (item) => <TarifaCell lt={item.liquidacion_tipo} />,
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
      <LiquidacionesListContent<LiquidacionEdificacionesListItem>
        icon={KIND_ICON}
        title="Liquidaciones — Edificaciones"
        description="Listado de liquidaciones de Edificaciones"
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
        useListData={useEdificacionesData}
        renderCard={(item, refetch) => (
          <LiquidacionEdificacionesCard item={item} onUpdated={refetch} />
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

      {/* Form modals unificados (Edificaciones) — 4 modes en 1 componente.
          ClientOnly evita que los mutation hooks (`useCrearEdificaciones`,
          `useEditarEdificaciones`, etc.) corran durante SSR y disparen
          "No QueryClient set" antes de que el provider hidrate. */}
      <ClientOnly>
        <LiquidacionEdificacionFormModal
          mode="create"
          open={formModalOpen}
          onOpenChange={setFormModalOpen}
          onSuccess={() => setFormModalOpen(false)}
        />
      </ClientOnly>

      <SeleccionarPreviaModal
        open={selectPreviaOpen}
        onOpenChange={setSelectPreviaOpen}
        tiposPermitidos={["EDIFICACION"]}
        onSelect={(p) => {
          setPrevia(p);
          setSelectPreviaOpen(false);
          setNuevaRevisionOpen(true);
        }}
      />

      {previa && (
        <LiquidacionEdificacionFormModal
          mode="nueva-revision"
          open={nuevaRevisionOpen}
          onOpenChange={setNuevaRevisionOpen}
          previa={previa}
          onSuccess={() => {
            setNuevaRevisionOpen(false);
            setPrevia(null);
          }}
        />
      )}

      {/* Lifted modals — Table view's row actions. Conditional render so each
          modal only mounts with a fully-typed item (avoids Zod-vs-prop type
          mismatch when state is null). */}
      {detalleItem && (
        <LiquidacionDetalleModal
          open
          onOpenChange={(open) => {
            if (!open) setDetalleItem(null);
          }}
          kindBadge="Edificación"
          publicId={detallePublicId ?? ""}
          estado={detalleItem.liquidacion_general.estado}
          kindIcon={Building2}
        >
          {composeDetalleSections({
            lg: detalleItem.liquidacion_general,
            lt: detalleItem.liquidacion_tipo,
            tipoSection: (
              <LiquidacionDetalleEdificacionesSection
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
        <LiquidacionEdificacionFormModal
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
