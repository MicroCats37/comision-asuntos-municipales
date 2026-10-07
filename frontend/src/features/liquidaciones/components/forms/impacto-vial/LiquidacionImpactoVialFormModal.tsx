"use client";

import { Car, FilePenLine, FileText, Link2, RefreshCw } from "lucide-react";
/**
 * LiquidacionImpactoVialFormModal — Modal unificado para Impacto Vial.
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Mismo patrón que Taludes
 * pero con tipo="impacto-vial" en smart fields.
 *
 * 4 modes:
 *   - 'create'         → useCrearImpactoVial
 *   - 'edit'           → useEditarImpactoVial
 *   - 'nueva-revision' → useCrearNuevaRevisionImpactoVial
 *   - 'relacionada'    → useCrearRelacionadaImpactoVial
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleImpactoVialSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearImpactoVial } from "../../../hooks/useCrearImpactoVial";
import { useCrearNuevaRevisionImpactoVial } from "../../../hooks/useCrearNuevaRevisionImpactoVial";
import { useCrearRelacionadaImpactoVial } from "../../../hooks/useCrearRelacionadaImpactoVial";
import { useEditarImpactoVial } from "../../../hooks/useEditarImpactoVial";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import type { LiquidacionImpactoVialListItem } from "../../../schemas/liquidacion-impacto-vial.schema";
import {
  type ImpactoVialFormData,
  impactoVialFormSchema,
} from "../../../schemas/liquidacion-impacto-vial-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { CotizacionPorcentajeSmartField } from "../CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { TarifasYEspecialidadesSmartField } from "../TarifasYEspecialidadesSmartField";

const TIPO_PDF = "impacto-vial";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionImpactoVialListItem;
};
type NuevaRevisionProps = BaseProps & {
  mode: "nueva-revision";
  previa: LiquidacionImpactoVialListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  previa: LiquidacionImpactoVialListItem;
};

export type LiquidacionImpactoVialFormModalProps =
  | CreateProps
  | EditProps
  | NuevaRevisionProps
  | RelacionadaProps;

function buildInitialData(
  item: LiquidacionImpactoVialListItem,
  options: { skipSmartFieldDefaults?: boolean } = {},
): ImpactoVialFormData {
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

export function LiquidacionImpactoVialFormModal(
  props: LiquidacionImpactoVialFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  const sourceItem: LiquidacionImpactoVialListItem | null =
    mode === "edit" ? props.item : mode !== "create" ? props.previa : null;

  const crearMutation = useCrearImpactoVial();
  const editarMutation = useEditarImpactoVial(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const nuevaRevisionMutation = useCrearNuevaRevisionImpactoVial();
  const relacionadaMutation = useCrearRelacionadaImpactoVial();

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
      methods: import("react-hook-form").UseFormReturn<ImpactoVialFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isEdit, isRevisionLike, canEditProyecto } = ctx;
      // En mode='create' sourceItem es null; usamos 0 como default
      const initialData = sourceItem
        ? buildInitialData(sourceItem as LiquidacionImpactoVialListItem, {
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
            tipo="impacto-vial"
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
            tipo="impacto-vial"
            {...(isEdit
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

  const initialData: Partial<ImpactoVialFormData> = (() => {
    if (mode === "create") return { valor_declarado: 0 };
    if (mode === "edit" && sourceItem) return buildInitialData(sourceItem);
    if (sourceItem) {
      return buildInitialData(sourceItem, { skipSmartFieldDefaults: true });
    }
    return {};
  })();

  const onSubmitCreate = useCallback(
    async (data: ImpactoVialFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: ImpactoVialFormData) => {
      await editarMutation.mutateAsync(data);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitNuevaRevision = useCallback(
    async (data: ImpactoVialFormData, _liquidacionPreviaId: string) => {
      return await nuevaRevisionMutation.mutateAsync(
        data,
        _liquidacionPreviaId,
      );
    },
    [nuevaRevisionMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: ImpactoVialFormData, _liquidacionPreviaId: string) => {
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
        "impacto-vial",
        previaParaDetalle.liquidacion_general.fecha_registro,
        previaParaDetalle.liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<ImpactoVialFormData, LiquidacionImpactoVialListItem>
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={impactoVialFormSchema}
        initialData={initialData}
        eyebrow="Impacto Vial"
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
          kindBadge="Impacto Vial"
          publicId={detallePublicId}
          estado={previaParaDetalle.liquidacion_general.estado}
          kindIcon={Car}
        >
          {composeDetalleSections({
            lg: previaParaDetalle.liquidacion_general,
            lt: previaParaDetalle.liquidacion_tipo,
            tipoSection: (
              <LiquidacionDetalleImpactoVialSection
                liquidacionTipo={previaParaDetalle.liquidacion_tipo}
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}
    </>
  );
}
