"use client";

import {
  FilePenLine,
  FileText,
  Link2,
  Mountain,
  RefreshCw,
} from "lucide-react";
/**
 * LiquidacionMecanicaSuelosFormModal — Modal unificado para MS (M2).
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Misma estructura que HU
 * pero con tipo="mecanica-suelos" en smart fields.
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleMecanicaSuelosSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearMecanicaSuelos } from "../../../hooks/useCrearMecanicaSuelos";
import { useCrearNuevaRevisionMecanicaSuelos } from "../../../hooks/useCrearNuevaRevisionMecanicaSuelos";
import { useCrearRelacionadaMecanicaSuelos } from "../../../hooks/useCrearRelacionadaMecanicaSuelos";
import { useEditarMecanicaSuelos } from "../../../hooks/useEditarMecanicaSuelos";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import type { LiquidacionMecanicaSuelosListItem } from "../../../schemas/liquidacion-mecanica-suelos.schema";
import {
  type MecanicaSuelosFormData,
  mecanicaSuelosFormSchema,
} from "../../../schemas/liquidacion-mecanica-suelos-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { CotizacionM2SmartField } from "../CotizacionM2SmartField";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { TarifasM2SmartField } from "../TarifasM2SmartField";

const TIPO_PDF = "mecanica-suelos";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionMecanicaSuelosListItem;
};
type NuevaRevisionProps = BaseProps & {
  mode: "nueva-revision";
  previa: LiquidacionMecanicaSuelosListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  previa: LiquidacionMecanicaSuelosListItem;
};

export type LiquidacionMecanicaSuelosFormModalProps =
  | CreateProps
  | EditProps
  | NuevaRevisionProps
  | RelacionadaProps;

function buildInitialData(
  item: LiquidacionMecanicaSuelosListItem,
): MecanicaSuelosFormData {
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

export function LiquidacionMecanicaSuelosFormModal(
  props: LiquidacionMecanicaSuelosFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  const sourceItem: LiquidacionMecanicaSuelosListItem | null =
    mode === "edit" ? props.item : mode !== "create" ? props.previa : null;

  const crearMutation = useCrearMecanicaSuelos();
  const editarMutation = useEditarMecanicaSuelos(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const nuevaRevisionMutation = useCrearNuevaRevisionMecanicaSuelos();
  const relacionadaMutation = useCrearRelacionadaMecanicaSuelos();

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
      methods: import("react-hook-form").UseFormReturn<MecanicaSuelosFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isEdit, isRevisionLike, canEditProyecto } = ctx;
      // En mode='create' sourceItem es null; usamos 0 como default
      const initialData = sourceItem
        ? buildInitialData(sourceItem as LiquidacionMecanicaSuelosListItem)
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
          <TarifasM2SmartField methods={methods} tipo="mecanica-suelos" />
          <CotizacionM2SmartField
            methods={methods}
            tipo="mecanica-suelos"
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

  const initialData: Partial<MecanicaSuelosFormData> = (() => {
    if (mode === "create") return { area_solicitada: 0 };
    if (sourceItem) return buildInitialData(sourceItem);
    return {};
  })();

  const onSubmitCreate = useCallback(
    async (data: MecanicaSuelosFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: MecanicaSuelosFormData) => {
      await editarMutation.mutateAsync(data);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitNuevaRevision = useCallback(
    async (data: MecanicaSuelosFormData, _liquidacionPreviaId: string) => {
      return await nuevaRevisionMutation.mutateAsync(
        data,
        _liquidacionPreviaId,
      );
    },
    [nuevaRevisionMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: MecanicaSuelosFormData, _liquidacionPreviaId: string) => {
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
        "mecanica-suelos",
        previaParaDetalle.liquidacion_general.fecha_registro,
        previaParaDetalle.liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<
        MecanicaSuelosFormData,
        LiquidacionMecanicaSuelosListItem
      >
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={mecanicaSuelosFormSchema}
        initialData={initialData}
        eyebrow="Mecánica de Suelos"
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
          kindBadge="Mecánica de Suelos"
          publicId={detallePublicId}
          estado={previaParaDetalle.liquidacion_general.estado}
          kindIcon={Mountain}
        >
          {composeDetalleSections({
            lg: previaParaDetalle.liquidacion_general,
            lt: previaParaDetalle.liquidacion_tipo as never,
            tipoSection: (
              <LiquidacionDetalleMecanicaSuelosSection
                liquidacionTipo={previaParaDetalle.liquidacion_tipo}
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}
    </>
  );
}
