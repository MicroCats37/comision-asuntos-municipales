"use client";

import {
  Building2,
  FilePenLine,
  FileText,
  Link2,
  RefreshCw,
} from "lucide-react";
/**
 * LiquidacionHabilitacionUrbanaFormModal — Modal unificado para HU (M2).
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Diferencias con PO:
 * - `area_solicitada` en lugar de `valor_declarado`
 * - `tarifa_m2_id` singular en lugar de array de especialidades
 * - `showUrbanizacion` (HU y MS tienen este campo extra)
 * - Smart fields: `TarifasM2SmartField` + `CotizacionM2SmartField`
 *
 * 4 modes:
 *   - 'create'         → useCrearHabilitacionUrbana
 *   - 'edit'           → useEditarHabilitacionUrbana
 *   - 'nueva-revision' → useCrearNuevaRevisionHabilitacionUrbana
 *   - 'relacionada'    → useCrearRelacionadaHabilitacionUrbana
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleHabilitacionUrbanaSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearHabilitacionUrbana } from "../../../hooks/useCrearHabilitacionUrbana";
import { useCrearNuevaRevisionHabilitacionUrbana } from "../../../hooks/useCrearNuevaRevisionHabilitacionUrbana";
import { useCrearRelacionadaHabilitacionUrbana } from "../../../hooks/useCrearRelacionadaHabilitacionUrbana";
import { useEditarHabilitacionUrbana } from "../../../hooks/useEditarHabilitacionUrbana";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import type { LiquidacionHabilitacionUrbanaListItem } from "../../../schemas/liquidacion-habilitacion-urbana.schema";
import {
  type HabilitacionUrbanaFormData,
  habilitacionUrbanaFormSchema,
} from "../../../schemas/liquidacion-habilitacion-urbana-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { CotizacionM2SmartField } from "../CotizacionM2SmartField";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { TarifasM2SmartField } from "../TarifasM2SmartField";

const TIPO_PDF = "habilitacion-urbana";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionHabilitacionUrbanaListItem;
};
type NuevaRevisionProps = BaseProps & {
  mode: "nueva-revision";
  previa: LiquidacionHabilitacionUrbanaListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  previa: LiquidacionHabilitacionUrbanaListItem;
};

export type LiquidacionHabilitacionUrbanaFormModalProps =
  | CreateProps
  | EditProps
  | NuevaRevisionProps
  | RelacionadaProps;

function buildInitialData(
  item: LiquidacionHabilitacionUrbanaListItem,
): HabilitacionUrbanaFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  return {
    denominacion: lg.denominacion_de_proyecto ?? "",
    municipalidad_id: lg.municipalidad?.id ?? "",
    expediente: lg.expediente ?? "",
    observacion: lg.observacion ?? "",
    retencion: lg.retencion ?? false,
    nombre_propietario: lg.proyecto.nombre_propietario,
    direccion: lg.proyecto.direccion,
    distrito_id: lg.proyecto.distrito?.id ?? "",
    urbanizacion: lg.proyecto.urbanizacion ?? undefined,
    entidad_tipo_documento:
      lg.proyecto.entidad?.tipo_documento === "DNI" ? "DNI" : "RUC",
    entidad_numero_documento: lg.proyecto.entidad?.numero_documento ?? "",
    entidad_razon_social: lg.proyecto.entidad?.razon_social ?? "",
    area_solicitada: lt.area_m2,
    tarifa_m2_id: lt.tarifa_aplicada_id ?? undefined,
    contacto: toContactoInline(lg.contacto),
  };
}

export function LiquidacionHabilitacionUrbanaFormModal(
  props: LiquidacionHabilitacionUrbanaFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  const sourceItem: LiquidacionHabilitacionUrbanaListItem | null =
    mode === "edit" ? props.item : mode !== "create" ? props.previa : null;

  const crearMutation = useCrearHabilitacionUrbana();
  const editarMutation = useEditarHabilitacionUrbana(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const nuevaRevisionMutation = useCrearNuevaRevisionHabilitacionUrbana();
  const relacionadaMutation = useCrearRelacionadaHabilitacionUrbana();

  const icon =
    mode === "edit" ? (
      <FilePenLine className="h-5 w-5 text-primary" />
    ) : mode === "nueva-revision" ? (
      <RefreshCw className="h-5 w-5 text-primary" />
    ) : mode === "relacionada" ? (
      <Link2 className="h-5 w-5 text-primary" />
    ) : (
      <FileText className="h-5 w-5 text-primary" />
    );

  const titlePrefix = (() => {
    switch (mode) {
      case "create":
        return "Nueva Liquidación";
      case "edit":
        return "Editar Liquidación";
      case "nueva-revision":
        return "Nueva Revisión";
      case "relacionada":
        return "Liquidación Relacionada";
    }
  })();

  const primaryLabel = (() => {
    switch (mode) {
      case "create":
        return "Crear Liquidación";
      case "edit":
        return "Guardar cambios";
      case "nueva-revision":
        return "Crear Revisión";
      case "relacionada":
        return "Crear Relacionada";
    }
  })();

  const primaryLoadingLabel = mode === "edit" ? "Guardando..." : "Creando...";

  const primaryLoading =
    mode === "create"
      ? crearMutation.isPending
      : mode === "edit"
        ? editarMutation.isPending
        : mode === "nueva-revision"
          ? nuevaRevisionMutation.isPending
          : relacionadaMutation.isPending;

  const description =
    mode === "nueva-revision" || mode === "relacionada"
      ? sourceItem?.liquidacion_general.denominacion_de_proyecto
        ? `Sobre: ${sourceItem.liquidacion_general.denominacion_de_proyecto}`
        : undefined
      : undefined;

  const computeCanEditProyecto = useCallback(
    (m: typeof mode, item: typeof sourceItem): boolean => {
      if (m === "create" || m === "nueva-revision") return true;
      if (m === "edit" && item) {
        return canEditLiquidacion(item.liquidacion_general).canEditProyecto;
      }
      return false;
    },
    [],
  );

  const renderBody = useCallback(
    (ctx: {
      methods: import("react-hook-form").UseFormReturn<HabilitacionUrbanaFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isEdit, isRevisionLike, canEditProyecto } = ctx;
      // En mode='create' sourceItem es null; usamos 0 como default
      const initialData = sourceItem
        ? buildInitialData(sourceItem as LiquidacionHabilitacionUrbanaListItem)
        : null;
      const areaInicial = initialData?.area_solicitada ?? 0;

      const tramiteField = (
        <MoneyInput
          name="area_solicitada"
          label="Área Solicitada (m²)"
          required
          control={methods.control}
          min={0}
          defaultValue={isEdit || isRevisionLike ? areaInicial : 0}
          className="w-full"
        />
      );

      const motorSection = (
        <div className="space-y-3">
          <TarifasM2SmartField methods={methods} tipo="habilitacion-urbana" />
          <CotizacionM2SmartField
            methods={methods}
            tipo="habilitacion-urbana"
            {...(isEdit || isRevisionLike
              ? {
                  mode: "edit",
                  liquidacionId: sourceItem?.liquidacion_general.id,
                }
              : {})}
          />
        </div>
      );

      return (
        <LiquidacionFormBodyBase
          control={methods.control as never}
          methods={methods}
          showUrbanizacion
          tramiteField={tramiteField}
          motorSection={motorSection}
          valoresActualesSection={null}
          canEditProyecto={canEditProyecto}
        />
      );
    },
    [sourceItem],
  );

  const initialData: Partial<HabilitacionUrbanaFormData> = (() => {
    if (mode === "create") return { area_solicitada: 0 };
    if (sourceItem) return buildInitialData(sourceItem);
    return {};
  })();

  const onSubmitCreate = useCallback(
    async (data: HabilitacionUrbanaFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: HabilitacionUrbanaFormData) => {
      await editarMutation.mutateAsync(data);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitNuevaRevision = useCallback(
    async (data: HabilitacionUrbanaFormData, _liquidacionPreviaId: string) => {
      return await nuevaRevisionMutation.mutateAsync(
        data,
        _liquidacionPreviaId,
      );
    },
    [nuevaRevisionMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: HabilitacionUrbanaFormData, _liquidacionPreviaId: string) => {
      return await relacionadaMutation.mutateAsync(data, _liquidacionPreviaId);
    },
    [relacionadaMutation],
  );

  const onVerDetalle = useCallback(() => {
    if (mode === "nueva-revision" || mode === "relacionada") {
      setDetalleOpen(true);
    }
  }, [mode]);

  const previaParaDetalle =
    mode === "nueva-revision" || mode === "relacionada" ? props.previa : null;

  const detallePublicId = previaParaDetalle
    ? formatPublicId(
        "habilitacion-urbana",
        previaParaDetalle.liquidacion_general.fecha_registro,
        previaParaDetalle.liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<
        HabilitacionUrbanaFormData,
        LiquidacionHabilitacionUrbanaListItem
      >
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={habilitacionUrbanaFormSchema}
        initialData={initialData}
        eyebrow="Habilitación Urbana"
        icon={icon}
        titlePrefix={titlePrefix}
        description={description}
        primaryLabel={primaryLabel}
        primaryLoadingLabel={primaryLoadingLabel}
        primaryLoading={primaryLoading}
        renderBody={renderBody}
        onSubmitCreate={onSubmitCreate}
        onAfterSubmit={onAfterSubmit}
        onSubmitEdit={onSubmitEdit}
        onSubmitNuevaRevision={onSubmitNuevaRevision}
        onSubmitRelacionada={onSubmitRelacionada}
        computeCanEditProyecto={computeCanEditProyecto}
        onVerDetalle={onVerDetalle}
      />

      {previaParaDetalle && (
        <LiquidacionDetalleModal
          open={detalleOpen}
          onOpenChange={setDetalleOpen}
          kindBadge="Habilitación Urbana"
          publicId={detallePublicId}
          estado={previaParaDetalle.liquidacion_general.estado}
          kindIcon={Building2}
        >
          {composeDetalleSections({
            lg: previaParaDetalle.liquidacion_general,
            // composeDetalleSections solo soporta PorcentajeObraDatosOut; HU usa M2
            // pero el detalle usa la sección tipo-specific (M2DatosOut) que ya pasamos abajo.
            lt: previaParaDetalle.liquidacion_tipo as never,
            tipoSection: (
              <LiquidacionDetalleHabilitacionUrbanaSection
                liquidacionTipo={previaParaDetalle.liquidacion_tipo}
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}
    </>
  );
}
