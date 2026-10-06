"use client";

import {
  FilePenLine,
  FileText,
  Link2,
  Mountain,
  RefreshCw,
} from "lucide-react";
/**
 * LiquidacionTaludesFormModal — Modal unificado para Taludes.
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Mismo patrón que Edificaciones
 * pero sin `tipo_tramite` (Taludes no tiene ese concepto) y sin print PDF en create.
 *
 * 4 modes:
 *   - 'create'         → useCrearTaludes
 *   - 'edit'           → useEditarTaludes
 *   - 'nueva-revision' → useCrearNuevaRevisionTaludes
 *   - 'relacionada'    → useCrearRelacionadaTaludes
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
  LiquidacionDetalleTaludesSection,
} from "../../../components/detail";
import { useCrearNuevaRevisionTaludes } from "../../../hooks/useCrearNuevaRevisionTaludes";
import { useCrearRelacionadaTaludes } from "../../../hooks/useCrearRelacionadaTaludes";
import { useCrearTaludes } from "../../../hooks/useCrearTaludes";
import { useEditarTaludes } from "../../../hooks/useEditarTaludes";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import type { LiquidacionTaludesListItem } from "../../../schemas/liquidacion-taludes.schema";
import {
  type TaludesFormData,
  taludesFormSchema,
} from "../../../schemas/liquidacion-taludes-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { CotizacionPorcentajeSmartField } from "../CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { TarifasYEspecialidadesSmartField } from "../TarifasYEspecialidadesSmartField";

const TIPO_PDF = "taludes";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & { mode: "edit"; item: LiquidacionTaludesListItem };
type NuevaRevisionProps = BaseProps & {
  mode: "nueva-revision";
  previa: LiquidacionTaludesListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  previa: LiquidacionTaludesListItem;
};

export type LiquidacionTaludesFormModalProps =
  | CreateProps
  | EditProps
  | NuevaRevisionProps
  | RelacionadaProps;

function buildInitialData(
  item: LiquidacionTaludesListItem,
  options: { skipSmartFieldDefaults?: boolean } = {},
): TaludesFormData {
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
    valor_declarado: lt.valor_declarado,
    tarifa_unica_id: options.skipSmartFieldDefaults
      ? undefined
      : (lt.detalles[0]?.tarifa_aplicada_id ?? undefined),
    especialidades_seleccionadas: options.skipSmartFieldDefaults
      ? undefined
      : lt.detalles.map((d) => d.especialidad_id),
    contacto: toContactoInline(lg.contacto),
  };
}

export function LiquidacionTaludesFormModal(
  props: LiquidacionTaludesFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  const sourceItem: LiquidacionTaludesListItem | null =
    mode === "edit" ? props.item : mode !== "create" ? props.previa : null;

  const crearMutation = useCrearTaludes();
  const editarMutation = useEditarTaludes(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const nuevaRevisionMutation = useCrearNuevaRevisionTaludes();
  const relacionadaMutation = useCrearRelacionadaTaludes();

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
      methods: import("react-hook-form").UseFormReturn<TaludesFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isEdit, isRevisionLike, canEditProyecto } = ctx;
      // En mode='create' sourceItem es null; usamos 0 como default
      const initialData = sourceItem
        ? buildInitialData(sourceItem as LiquidacionTaludesListItem, {
            skipSmartFieldDefaults: isRevisionLike,
          })
        : null;
      const valorDeclaradoInicial = initialData?.valor_declarado ?? 0;

      const tramiteField = (
        <MoneyInput
          name="valor_declarado"
          label="Valor Declarado (S/)"
          placeholder="S/ 0.00"
          control={methods.control}
          required
          defaultValue={isEdit || isRevisionLike ? valorDeclaradoInicial : 0}
        />
      );

      const motorSection = (
        <div className="space-y-3">
          <TarifasYEspecialidadesSmartField
            methods={methods}
            tipo="taludes"
            {...(isEdit || isRevisionLike
              ? {
                  mode: "edit",
                  fecha: sourceItem?.liquidacion_general.fecha_registro,
                  variant: "manual" as const,
                }
              : {})}
          />
          <CotizacionPorcentajeSmartField
            methods={methods}
            tipo="taludes"
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
          tramiteField={tramiteField}
          motorSection={motorSection}
          valoresActualesSection={null}
          canEditProyecto={canEditProyecto}
        />
      );
    },
    [sourceItem],
  );

  const initialData: Partial<TaludesFormData> = (() => {
    if (mode === "create") return { valor_declarado: 0 };
    if (mode === "edit" && sourceItem) return buildInitialData(sourceItem);
    if (sourceItem) {
      return buildInitialData(sourceItem, { skipSmartFieldDefaults: true });
    }
    return {};
  })();

  const onSubmitCreate = useCallback(
    async (data: TaludesFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: TaludesFormData) => {
      await editarMutation.mutateAsync(data);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitNuevaRevision = useCallback(
    async (data: TaludesFormData, _liquidacionPreviaId: string) => {
      return await nuevaRevisionMutation.mutateAsync(
        data,
        _liquidacionPreviaId,
      );
    },
    [nuevaRevisionMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: TaludesFormData, _liquidacionPreviaId: string) => {
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
        "taludes",
        previaParaDetalle.liquidacion_general.fecha_registro,
        previaParaDetalle.liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<TaludesFormData, LiquidacionTaludesListItem>
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={taludesFormSchema}
        initialData={initialData}
        eyebrow="Taludes"
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
          kindBadge="Taludes"
          publicId={detallePublicId}
          estado={previaParaDetalle.liquidacion_general.estado}
          kindIcon={Mountain}
        >
          {composeDetalleSections({
            lg: previaParaDetalle.liquidacion_general,
            lt: previaParaDetalle.liquidacion_tipo,
            tipoSection: (
              <LiquidacionDetalleTaludesSection
                liquidacionTipo={previaParaDetalle.liquidacion_tipo}
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}
    </>
  );
}
