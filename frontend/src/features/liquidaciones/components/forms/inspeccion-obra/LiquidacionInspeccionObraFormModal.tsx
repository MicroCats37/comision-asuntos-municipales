"use client";

import { FilePenLine, FileText, Link2 } from "lucide-react";
/**
 * LiquidacionInspeccionObraFormModal — Modal unificado para Inspección de Obra.
 *
 * Wrapper delgado sobre `LiquidacionFormShell`. Diferencias con PO/M2:
 *  - `cantidad_visitas` en lugar de `valor_declarado` / `area_solicitada`
 *  - `TarifasVisitasSinPreviaSmartField` es self-contained (incluye inspector)
 *  - Modal de inspector (`SeleccionarInspectorModal`) como sibling
 *
 * 3 modes:
 *   - 'create'        → useCrearInspeccionObra
 *   - 'edit'          → useEditarInspeccionObra
 *   - 'relacionada'   → useCrearRelacionadaInspeccionObra (con previa preseteada)
 *
 * Nota: en IO, "con previa" crea `relacionada` (revision 1), NO `nueva-revision`.
 * La lógica `nueva-revision` (revision N+2) no aplica a IO porque siempre arranca en 1.
 */
import { useCallback, useEffect, useState } from "react";
import { IncrementerInput } from "@/components/genericForm/inputs/IncrementerInput";
import { notify } from "@/errors";
import {
  composeDetalleSections,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearInspeccionObra } from "../../../hooks/useCrearInspeccionObra";
import { useCrearRelacionadaInspeccionObra } from "../../../hooks/useCrearRelacionadaInspeccionObra";
import { useEditarInspeccionObra } from "../../../hooks/useEditarInspeccionObra";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import { useTiposLiquidacion } from "../../../hooks/useTiposLiquidacion";
import type { UltimaRevisionGeneralItem } from "../../../hooks/useUltimaRevisionGeneral";
import type { LiquidacionInspeccionObraListItem } from "../../../schemas/liquidacion-inspeccion-obra.schema";
import {
  type VisitasFormData,
  visitasFormSchema,
} from "../../../schemas/liquidacion-visitas-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { getLiquidacionTipoInfo } from "../../../utils/liquidacionTipoInfo";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { SeleccionarInspectorModal } from "../SeleccionarInspectorModal";
import { TarifasVisitasSinPreviaSmartField } from "../TarifasVisitasSinPreviaSmartField";

const TIPO_PDF = "inspeccion-obra";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & { mode: "create" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionInspeccionObraListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  // SeleccionarPreviaModal devuelve UltimaRevisionGeneralItem (union de todos los
  // tipos, con la forma { liquidacion_general, liquidacion_especifica, liquidacion_tipo }).
  // En IO no pre-llenamos categoria/tarifa/inspector — el usuario los elige fresh.
  previa: UltimaRevisionGeneralItem;
};

export type LiquidacionInspeccionObraFormModalProps =
  | CreateProps
  | EditProps
  | RelacionadaProps;

function buildInitialData(
  item: LiquidacionInspeccionObraListItem,
  options: { skipSmartFieldDefaults?: boolean } = {},
): VisitasFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;

  // Normalizar categoría que viene del backend ("1" → "C1")
  let catNormalizada = String(lt.categoria);
  if (
    catNormalizada === "1" ||
    catNormalizada === "2" ||
    catNormalizada === "3" ||
    catNormalizada === "4"
  ) {
    catNormalizada = `C${catNormalizada}`;
  }
  const categoriaValida = ["C1", "C2", "C3", "C4"].includes(catNormalizada)
    ? catNormalizada
    : undefined;

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
    // tipo_liquidacion_id is used by SeleccionarInspectorModal to filter inspectors (frontend-only, never sent to backend).
    tipo_liquidacion_id: (lg as { tipo_liquidacion?: { id?: string } })
      .tipo_liquidacion?.id,
    cantidad_visitas: lt.cantidad_visitas,
    categoria: categoriaValida as VisitasFormData["categoria"],
    tarifa_visitas_id: options.skipSmartFieldDefaults
      ? undefined
      : (lt.tarifa_aplicada_id ?? undefined),
    contacto: toContactoInline(lg.contacto),
    // inspector_operacion_id is the relation table id (lt.inspectores[0]?.inspector_operacion_id)
    inspector_operacion_id: options.skipSmartFieldDefaults
      ? undefined
      : (lt.inspectores?.[0]?.inspector_operacion_id ?? undefined),
    // inspector_id is the actual inspector id (lt.inspectores[0]?.inspector_id)
    inspector_id: options.skipSmartFieldDefaults
      ? undefined
      : (lt.inspectores?.[0]?.inspector_id ?? undefined),
  };
}

export function LiquidacionInspeccionObraFormModal(
  props: LiquidacionInspeccionObraFormModalProps,
) {
  const { mode, open, onOpenChange, onSuccess } = props;
  const [detalleOpen, setDetalleOpen] = useState(false);

  // ── State específico de IO (no aplica al shell) ─────────────────
  const [inspectorModalOpen, setInspectorModalOpen] = useState(false);
  const [inspectorNombre, setInspectorNombre] = useState("");

  // ── Hooks ──────────────────────────────────────────────────────────
  const crearMutation = useCrearInspeccionObra();
  const editarMutation = useEditarInspeccionObra(
    mode === "edit" ? props.item.liquidacion_general.id : "",
  );
  const relacionadaMutation = useCrearRelacionadaInspeccionObra();
  const { data: tiposAll = [] } = useTiposLiquidacion();
  // IO solo permite EDIFICACION + HU como previa. Filtramos los tipos disponibles
  // para el selector del modal de inspector (en create mode).
  const tipos = tiposAll.filter((t) =>
    ["EDIFICACION", "HABILITACION_URBANA"].includes(t.codigo),
  );

  // sourceItem: en edit es el list item completo. En relacionada es un
  // UltimaRevisionGeneralItem (que ya tiene la forma { liquidacion_general, ... })
  // — se pasa directo al shell que extrae previousValues/revisionNumber.
  const sourceItem: LiquidacionInspeccionObraListItem | null =
    mode === "edit"
      ? props.item
      : mode === "relacionada" && props.previa
        ? (props.previa as unknown as LiquidacionInspeccionObraListItem)
        : null;

  // ── Reset del state específico al abrir el modal ───────────────
  useEffect(() => {
    if (open) {
      setInspectorNombre("");
    }
  }, [open]);

  // ── Visual por mode ─────────────────────────────────────────────
  const icon =
    mode === "edit" ? (
      <FilePenLine className="h-5 w-5 text-primary" />
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
        : mode === "relacionada"
          ? relacionadaMutation.isPending
          : false;

  const description =
    mode === "relacionada" &&
    sourceItem?.liquidacion_general.denominacion_de_proyecto
      ? `Sobre: ${sourceItem.liquidacion_general.denominacion_de_proyecto}`
      : undefined;

  const computeCanEditProyecto = useCallback(
    (
      m: "create" | "edit" | "nueva-revision" | "relacionada",
      item: typeof sourceItem,
    ): boolean => {
      if (m === "create") return true;
      if (m === "edit" && item) {
        return canEditLiquidacion(item.liquidacion_general).canEditProyecto;
      }
      return false;
    },
    [],
  );

  const renderBody = useCallback(
    (ctx: {
      methods: import("react-hook-form").UseFormReturn<VisitasFormData>;
      isEdit: boolean;
      isRevisionLike: boolean;
      sourceItem: typeof sourceItem;
      canEditProyecto: boolean;
    }) => {
      const { methods, isRevisionLike, canEditProyecto } = ctx;
      const initialData = sourceItem
        ? buildInitialData(sourceItem, {
            skipSmartFieldDefaults: isRevisionLike,
          })
        : null;
      const cantidadInicial = initialData?.cantidad_visitas ?? 1;
      const categoriaInicial = initialData?.categoria ?? "";

      const categoriaWatch =
        (methods.watch("categoria") as VisitasFormData["categoria"]) ??
        categoriaInicial;
      const tipoLiquidacionIdWatch =
        (methods.watch("tipo_liquidacion_id") as string) ?? "";

      const tramiteField = (
        <IncrementerInput
          name="cantidad_visitas"
          control={methods.control}
          label="Cantidad de Visitas"
          min={1}
          max={9999}
          suffix="visitas"
          required
          defaultValue={cantidadInicial}
        />
      );

      const motorSection = (
        <TarifasVisitasSinPreviaSmartField
          methods={methods}
          inspectorNombre={inspectorNombre}
          onOpenInspector={() => setInspectorModalOpen(true)}
          disabled={!categoriaWatch}
        />
      );

      return (
        <>
          <LiquidacionFormBodyBase
            control={methods.control as never}
            methods={methods}
            tramiteField={tramiteField}
            motorSection={motorSection}
            valoresActualesSection={null}
            canEditProyecto={canEditProyecto}
          />
          {/* Modal inspector — sibling del body, solo IO */}
          <SeleccionarInspectorModal
            open={inspectorModalOpen}
            onOpenChange={setInspectorModalOpen}
            tiposLiquidacion={tipos}
            tipoLiquidacionId={tipoLiquidacionIdWatch}
            // En edit/relacionada el tipo de liquidación es fijo (heredado);
            // solo en create se muestra el selector dentro del modal.
            fallbackTipoLiquidacionCodigo={
              mode === "create"
                ? null
                : ((
                    sourceItem?.liquidacion_general as {
                      tipo_liquidacion?: { codigo?: string };
                    }
                  )?.tipo_liquidacion?.codigo ?? null)
            }
            // Solo pasamos onTipoLiquidacionChange en create — su presencia en el
            // modal hace que se muestre el selector de tipo. En edit/relacionada
            // el tipo está fijo (heredado de la previa o del item), no debe mostrarse.
            {...(mode === "create"
              ? {
                  onTipoLiquidacionChange: (id: string) => {
                    methods.setValue("tipo_liquidacion_id", id, {
                      shouldValidate: false,
                    });
                  },
                }
              : {})}
            categoriaForm={categoriaWatch || null}
            selectedId={methods.watch("inspector_id") || undefined}
            onSelect={(id, nombre) => {
              methods.setValue("inspector_id", id, { shouldValidate: true });
              setInspectorNombre(nombre);
            }}
          />
        </>
      );
    },
    [inspectorNombre, inspectorModalOpen, sourceItem, tipos, mode],
  );

  const initialData: Partial<VisitasFormData> = (() => {
    if (mode === "create") return { cantidad_visitas: 1 };
    if (sourceItem) {
      return buildInitialData(sourceItem, {
        skipSmartFieldDefaults: mode === "relacionada",
      });
    }
    return {};
  })();
  const onSubmitCreate = useCallback(
    async (data: VisitasFormData) => {
      return await crearMutation.mutateAsync(data);
    },
    [crearMutation],
  );

  const onAfterSubmit = useLiquidacionPdfOnAfter(TIPO_PDF);

  const onSubmitEdit = useCallback(
    async (data: VisitasFormData) => {
      await editarMutation.mutateAsync(data);
      notify.success("Liquidación editada correctamente");
    },
    [editarMutation],
  );

  const onSubmitRelacionada = useCallback(
    async (data: VisitasFormData, liquidacionPreviaId: string) => {
      // useCrearRelacionadaInspeccionObra espera NuevaRevisionInspeccionObraFormData;
      // mapeamos desde VisitasFormData (form unificado).
      return await relacionadaMutation.mutateAsync({
        liquidacion_previa_id: liquidacionPreviaId,
        cantidad_visitas: data.cantidad_visitas,
        categoria: data.categoria,
        tarifa_visitas_id: data.tarifa_visitas_id ?? "",
        inspector_id: data.inspector_id ?? "",
        contacto: data.contacto,
      });
    },
    [relacionadaMutation],
  );

  const onVerDetalle = useCallback(() => {
    if (mode === "relacionada") {
      setDetalleOpen(true);
    }
  }, [mode]);
  const previaParaDetalle = mode === "relacionada" ? sourceItem : null;

  // El "tipo" del publicId viene del codigo del tipo_liquidacion de la previa
  // (ej: "EDIFICACION", "HABILITACION_URBANA"), NO se hardcodea "inspeccion-obra".
  const tipoSlugParaPublicId = (
    previaParaDetalle?.liquidacion_general.tipo_liquidacion?.codigo ??
    "INSPECCION_OBRA"
  )
    .toLowerCase()
    .replace(/_/g, "-");
  const detallePublicId = previaParaDetalle
    ? formatPublicId(
        tipoSlugParaPublicId,
        previaParaDetalle.liquidacion_general.fecha_registro,
        previaParaDetalle.liquidacion_especifica.numero,
      )
    : "";

  return (
    <>
      <LiquidacionFormShell<VisitasFormData, LiquidacionInspeccionObraListItem>
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode={mode}
        sourceItem={sourceItem}
        schema={visitasFormSchema}
        initialData={initialData}
        eyebrow="Inspección de Obra"
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
        onSubmitRelacionada={onSubmitRelacionada}
        computeCanEditProyecto={computeCanEditProyecto}
        onVerDetalle={onVerDetalle}
      />

      {(() => {
        if (!previaParaDetalle) return null;
        // Auto-determinar el tipo de la liquidación previa para armar el badge
        // y el icono del modal de detalle. No se requiere que el caller lo pase.
        const tipoInfo = getLiquidacionTipoInfo(
          previaParaDetalle.liquidacion_general.tipo_liquidacion?.codigo,
        );
        return (
          <LiquidacionDetalleModal
            open={detalleOpen}
            onOpenChange={setDetalleOpen}
            kindBadge={tipoInfo.label}
            publicId={detallePublicId}
            estado={previaParaDetalle.liquidacion_general.estado}
            kindIcon={tipoInfo.icon}
          >
            {composeDetalleSections({
              lg: previaParaDetalle.liquidacion_general,
              // composeDetalleSections solo soporta PorcentajeObraDatosOut; IO usa Visitas
              // pero el detalle usa la sección tipo-specific (VisitasDatosOut) que ya pasamos abajo.
              lt: (previaParaDetalle as unknown as { liquidacion_tipo: never })
                .liquidacion_tipo,
              tipoSection: (
                <LiquidacionDetalleInspeccionObraSection
                  liquidacionTipo={
                    (
                      previaParaDetalle as unknown as {
                        liquidacion_tipo: Parameters<
                          typeof LiquidacionDetalleInspeccionObraSection
                        >[0]["liquidacionTipo"];
                      }
                    ).liquidacion_tipo
                  }
                />
              ),
            })}
          </LiquidacionDetalleModal>
        );
      })()}
    </>
  );
}
