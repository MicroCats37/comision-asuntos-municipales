"use client";

import {
  Building2,
  FilePenLine,
  FileText,
  Link2,
  RefreshCw,
} from "lucide-react";
/**
 * LiquidacionEdificacionFormModal — Modal unificado para Edificaciones (PorcentajeObra).
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Misma estructura que los 5 modales
 * shell-based (HU, IV, MS, Taludes, IO). Diferencias con ellos:
 *   - motor: PorcentajeObra (valor_declarado + tarifas[] por especialidad)
 *   - campo extra del proyecto: `tipo_tramite` (TipoTramiteSmartField)
 *   - smart fields: TarifasYEspecialidadesSmartField + CotizacionPorcentajeSmartField
 *   - en edit: las tarifas se cargan con `fecha` (auto-fill histórico)
 *   - `canEditProyecto` extrae `estado === "PAGADA"` (no solo revision number)
 *
 * 4 modes:
 *   - 'create'         → useCrearEdificaciones
 *   - 'edit'           → useEditarEdificaciones
 *   - 'nueva-revision' → useCrearNuevaRevisionEdificaciones
 *   - 'relacionada'    → useCrearRelacionadaEdificaciones
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearEdificaciones } from "../../../hooks/useCrearEdificaciones";
import { useCrearNuevaRevisionEdificaciones } from "../../../hooks/useCrearNuevaRevisionEdificaciones";
import { useCrearRelacionadaEdificaciones } from "../../../hooks/useCrearRelacionadaEdificaciones";
import { useEditarEdificaciones } from "../../../hooks/useEditarEdificaciones";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import type { UltimaRevisionGeneralItem } from "../../../hooks/useUltimaRevisionGeneral";
import type { LiquidacionEdificacionesListItem } from "../../../schemas/liquidacion-edificaciones.schema";
import {
  type EdificacionesFormData,
  edificacionesFormSchema,
} from "../../../schemas/liquidacion-edificaciones-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { CotizacionPorcentajeSmartField } from "../CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { TarifasYEspecialidadesSmartField } from "../TarifasYEspecialidadesSmartField";
import { TipoTramiteSmartField } from "../TipoTramiteSmartField";

const TIPO_SLUG = "edificacion";
const TIPO_PDF = "edificacion";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionEdificacionesListItem;
};
type NuevaRevisionProps = BaseProps & {
  mode: "nueva-revision";
  previa: UltimaRevisionGeneralItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  previa: UltimaRevisionGeneralItem;
};

export type LiquidacionEdificacionFormModalProps =
  | CreateProps
  | EditProps
  | NuevaRevisionProps
  | RelacionadaProps;

/**
 * Construye initial data (EdificacionesFormData) a partir de un item o una previa.
 * Usado por edit, nueva-revision y relacionada.
 *
 * @param options.skipSmartFieldDefaults Si true, NO pre-rellena `tarifa_unica_id` ni
 *   `especialidades_seleccionadas`. Usar en nueva-revision/relacionada donde el usuario
 *   debe elegir explícitamente las especialidades (no se heredan de la previa).
 */
function buildInitialDataFromItem(
  item: UltimaRevisionGeneralItem,
  options: { skipSmartFieldDefaults?: boolean } = {},
): EdificacionesFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } =
    item as LiquidacionEdificacionesListItem;
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
    tipo_tramite: lt.tipo_tramite as EdificacionesFormData["tipo_tramite"],
    tarifa_unica_id: options.skipSmartFieldDefaults
      ? undefined
      : (lt.detalles[0]?.tarifa_aplicada_id ?? undefined),
    especialidades_seleccionadas: options.skipSmartFieldDefaults
      ? undefined
      : lt.detalles.map((d) => d.especialidad_id),
    contacto: toContactoInline(lg.contacto),
  };
}

export function LiquidacionEdificacionFormModal(
  props: LiquidacionEdificacionFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  // ── sourceItem: item (edit) o previa (nueva-revision/relacionada) o null (create)
  const sourceItem:
    | LiquidacionEdificacionesListItem
    | UltimaRevisionGeneralItem
    | null =
    mode === "edit" ? props.item : mode !== "create" ? props.previa : null;

  // ── Hooks de mutación (uno por mode; solo se usa el del mode activo) ─────
  const crearMutation = useCrearEdificaciones();
  const editarMutation = useEditarEdificaciones(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const nuevaRevisionMutation = useCrearNuevaRevisionEdificaciones();
  const relacionadaMutation = useCrearRelacionadaEdificaciones();

  const primaryLoading =
    mode === "create"
      ? crearMutation.isPending
      : mode === "edit"
        ? editarMutation.isPending
        : mode === "nueva-revision"
          ? nuevaRevisionMutation.isPending
          : relacionadaMutation.isPending;

  // ── Visual config ──────────────────────────────────────────────────────────
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

  const description =
    mode === "nueva-revision" || mode === "relacionada"
      ? (props.previa as UltimaRevisionGeneralItem).liquidacion_general
          .denominacion_de_proyecto
        ? `Sobre: ${(props.previa as UltimaRevisionGeneralItem).liquidacion_general.denominacion_de_proyecto}`
        : undefined
      : undefined;

  // ── Revision number para badge (mismo +2 que el default del shell)
  const revisionNumber: number | undefined =
    mode === "edit"
      ? Number(props.item.liquidacion_general.numero_revision)
      : mode === "nueva-revision" || mode === "relacionada"
        ? (() => {
            const n = Number(
              (props.previa as UltimaRevisionGeneralItem).liquidacion_general
                .numero_revision,
            );
            return Number.isFinite(n) ? n + 2 : undefined;
          })()
        : undefined;

  // ── canEditProyecto: incluye regla PAGADA además de revision>1
  const computeCanEditProyecto = useCallback(
    (m: typeof mode, item: typeof sourceItem): boolean => {
      if (m === "create" || m === "nueva-revision") return true;
      if (m === "edit" && item) {
        return canEditLiquidacion(
          (item as LiquidacionEdificacionesListItem).liquidacion_general,
        ).canEditProyecto;
      }
      return false;
    },
    [],
  );

  // ── Body render ───────────────────────────────────────────────────────────
  // Capturamos la fecha y el id aquí arriba (fuera del useCallback) para que
  // TypeScript narrowe correctamente el discriminated union de `props`.
  const sourceFechaRegistro = (
    sourceItem as { liquidacion_general?: { fecha_registro?: string } } | null
  )?.liquidacion_general?.fecha_registro;
  const sourceId = (
    sourceItem as { liquidacion_general?: { id: string } } | null
  )?.liquidacion_general?.id;

  const renderBody = useCallback(
    (ctx: {
      methods: import("react-hook-form").UseFormReturn<EdificacionesFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isEdit, isRevisionLike, canEditProyecto } = ctx;
      const initialData = sourceItem
        ? buildInitialDataFromItem(sourceItem as UltimaRevisionGenericItem)
        : null;
      const valorDeclaradoInicial = initialData?.valor_declarado ?? 0;

      const tramiteField = (
        <MoneyInput
          name="valor_declarado"
          label="Valor Declarado (S/)"
          placeholder="S/ 0.00"
          control={methods.control}
          required
          defaultValue={valorDeclaradoInicial}
        />
      );

      const motorSection = (
        <div className="space-y-3">
          <TarifasYEspecialidadesSmartField
            methods={methods}
            {...(isEdit || isRevisionLike
              ? {
                  mode: isEdit
                    ? "edit"
                    : (mode as "nueva-revision" | "relacionada"),
                  fecha: sourceFechaRegistro,
                  variant: "manual" as const,
                }
              : {})}
          />
          <CotizacionPorcentajeSmartField
            methods={methods}
            hasTipoTramite
            {...(isEdit || isRevisionLike
              ? {
                  mode: "edit",
                  tipo: "edificaciones",
                  liquidacionId: sourceId,
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
          proyectoFieldsExtra={
            <TipoTramiteSmartField
              methods={methods}
              revisionNumber={revisionNumber}
            />
          }
          valoresActualesSection={null}
          canEditProyecto={canEditProyecto}
        />
      );
    },
    [sourceItem, mode, revisionNumber, sourceFechaRegistro, sourceId],
  );

  const initialData: Partial<EdificacionesFormData> = (() => {
    if (mode === "create") return { valor_declarado: 0 };
    if (mode === "edit") return buildInitialDataFromItem(props.item);
    return buildInitialDataFromItem(props.previa as UltimaRevisionGenericItem, {
      skipSmartFieldDefaults: true,
    });
  })();

  // ── Submit handlers ──────────────────────────────────────────────────────
  const onSubmitCreate = useCallback(
    async (data: EdificacionesFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: EdificacionesFormData, canEditProyecto: boolean) => {
      await editarMutation.mutateAsync(data, canEditProyecto);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitNuevaRevision = useCallback(
    async (data: EdificacionesFormData, liquidacionPreviaId: string) => {
      return await nuevaRevisionMutation.mutateAsync(data, liquidacionPreviaId);
    },
    [nuevaRevisionMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: EdificacionesFormData, liquidacionPreviaId: string) => {
      return await relacionadaMutation.mutateAsync(data, liquidacionPreviaId);
    },
    [relacionadaMutation],
  );

  const onVerDetalle = useCallback(() => {
    if (mode === "nueva-revision" || mode === "relacionada") {
      setDetalleOpen(true);
    }
  }, [mode]);

  // ── Datos del item/previa para "Ver detalle" ─────────────────────────────
  const previaParaDetalle =
    mode === "nueva-revision" || mode === "relacionada"
      ? (props.previa as UltimaRevisionGeneralItem)
      : null;

  const detallePublicId = previaParaDetalle
    ? formatPublicId(
        TIPO_SLUG,
        previaParaDetalle.liquidacion_general.fecha_registro,
        (previaParaDetalle as LiquidacionEdificacionesListItem)
          .liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<
        EdificacionesFormData,
        LiquidacionEdificacionesListItem | UltimaRevisionGeneralItem
      >
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={edificacionesFormSchema}
        initialData={initialData}
        eyebrow="Edificaciones"
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
          kindBadge="Edificación"
          publicId={detallePublicId}
          estado={previaParaDetalle.liquidacion_general.estado}
          kindIcon={Building2}
        >
          {composeDetalleSections({
            lg: previaParaDetalle.liquidacion_general,
            lt: (previaParaDetalle as LiquidacionEdificacionesListItem)
              .liquidacion_tipo as never,
            tipoSection: (
              <LiquidacionDetalleEdificacionesSection
                liquidacionTipo={
                  (previaParaDetalle as LiquidacionEdificacionesListItem)
                    .liquidacion_tipo as never
                }
              />
            ),
          })}
        </LiquidacionDetalleModal>
      )}
    </>
  );
}

// ── Local type alias (UltimaRevisionGeneralItem structurally matches EdificacionesListItem)
// biome-ignore lint/suspicious/noExplicitAny: structural compat alias for type narrowing
type UltimaRevisionGenericItem = any;
