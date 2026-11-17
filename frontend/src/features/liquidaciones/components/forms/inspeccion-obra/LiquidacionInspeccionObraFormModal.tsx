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
import type { UseFormReturn } from "react-hook-form";
import { IncrementerInput } from "@/components/genericForm/inputs/IncrementerInput";
import {
  composeDetalleSections,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleModal,
} from "../../../components/detail";
import { useCrearInspeccionObra } from "../../../hooks/useCrearInspeccionObra";
import { useCrearRelacionadaInspeccionObra } from "../../../hooks/useCrearRelacionadaInspeccionObra";
import { useEditarInspeccionObra } from "../../../hooks/useEditarInspeccionObra";
import type { LiquidacionPreviaItem } from "../../../hooks/useLiquidacionesPrevias";
import { useLiquidacionPdfOnAfter } from "../../../hooks/useLiquidacionPdfOnAfter";
import { useTiposLiquidacion } from "../../../hooks/useTiposLiquidacion";
import type { LiquidacionInspeccionObraListItem } from "../../../schemas/liquidacion-inspeccion-obra.schema";
import {
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_NORMAL,
} from "../../../schemas/liquidacion-io-modo-cotizacion.schema";
import {
  type VisitasFormData,
  visitasFormSchema,
  visitasLegacyFormSchema,
} from "../../../schemas/liquidacion-visitas-form.schema";
import { canEditLiquidacion } from "../../../utils/canEditLiquidacion";
import { toContactoInline } from "../../../utils/contacto";
import { formatPublicId } from "../../../utils/formatPublicId";
import { getLiquidacionTipoInfo } from "../../../utils/liquidacionTipoInfo";
import { hidratarModoCotizacionDesdeItem } from "../../../utils/modoCotizacionIo";
import { BuscarInspectorPorCipModal } from "../BuscarInspectorPorCipModal";
import { LiquidacionFormBodyBase } from "../LiquidacionFormBodyBase";
import { LiquidacionFormShell } from "../LiquidacionFormShell";
import { SeleccionarInspectorModal } from "../SeleccionarInspectorModal";
import { SeleccionarPreviaModal } from "../SeleccionarPreviaModal";
import { TarifasVisitasSinPreviaSmartField } from "../TarifasVisitasSinPreviaSmartField";
import {
  deriveContinuidadDefaults,
  deriveContinuidadEditDefaults,
} from "./ContinuidadVisitasPanel";

const TIPO_PDF = "inspeccion-obra";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type CreateProps = BaseProps & {
  mode: "create";
  /**
   * Liquidación previa (A) desde la que se inició la acción "Continuar".
   * Cuando viene, la sección de continuidad arranca activada y prellena.
   */
  continuidadPrevia?: LiquidacionInspeccionObraListItem | null;
};
type LegacyProps = BaseProps & { mode: "legacy" };
type EditProps = BaseProps & {
  mode: "edit";
  item: LiquidacionInspeccionObraListItem;
};
type RelacionadaProps = BaseProps & {
  mode: "relacionada";
  // SeleccionarPreviaModal devuelve LiquidacionPreviaItem (union de todos los
  // tipos, con la forma { liquidacion_general, liquidacion_especifica, liquidacion_tipo }).
  // En IO no pre-llenamos categoria/tarifa/inspector — el usuario los elige fresh.
  previa: LiquidacionPreviaItem;
};

export type LiquidacionInspeccionObraFormModalProps =
  | CreateProps
  | LegacyProps
  | EditProps
  | RelacionadaProps;

function DefaultTipoLiquidacionSync({
  methods,
  tipoEdificacionId,
  enabled,
}: {
  methods: UseFormReturn<VisitasFormData>;
  tipoEdificacionId?: string;
  enabled: boolean;
}) {
  useEffect(() => {
    if (!enabled || !tipoEdificacionId) return;
    if (methods.getValues("tipo_liquidacion_id")) return;
    methods.setValue("tipo_liquidacion_id", tipoEdificacionId, {
      shouldValidate: false,
      shouldDirty: false,
    });
  }, [enabled, methods, tipoEdificacionId]);

  return null;
}

function ReferenceSelectionSync({
  methods,
  reference,
}: {
  methods: UseFormReturn<VisitasFormData>;
  reference: LiquidacionInspeccionObraListItem | null;
}) {
  useEffect(() => {
    if (!reference) return;

    methods.setValue("modo_cotizacion", MODO_COTIZACION_IO_CONTINUAR, {
      shouldValidate: true,
    });
    methods.setValue("continuidad", deriveContinuidadDefaults(reference), {
      shouldDirty: true,
      shouldValidate: true,
    });
  }, [methods, reference]);

  return null;
}

function buildInitialData(
  item: LiquidacionInspeccionObraListItem,
  options: {
    skipSmartFieldDefaults?: boolean;
    /**
     * Rehidrata el bloque de continuidad desde el registro PERSISTIDO.
     * Solo en `mode="edit"`: en `relacionada` la `liquidacion_tipo` es la de la
     * PREVIA (A), no la de la liquidación que se está creando.
     */
    includeContinuidad?: boolean;
  } = {},
): Partial<VisitasFormData> {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;

  // Compatibilidad al editar registros históricos que todavía tengan C1-C4.
  let catNormalizada = String(lt.categoria);
  if (["C1", "C2", "C3", "C4"].includes(catNormalizada)) {
    catNormalizada = catNormalizada.slice(1);
  }
  const categoriaValida = ["1", "2", "3", "4"].includes(catNormalizada)
    ? catNormalizada
    : undefined;

  return {
    denominacion: lg.denominacion_de_proyecto ?? "",
    municipalidad_id: lg.municipalidad?.id ?? "",
    expediente: lg.expediente ?? "",
    observacion: lg.observacion ?? "",
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
    // Continuidad: se rehidrata SOLO en edición, desde el registro persistido.
    // Sin `modo`: la operación de continuidad solo viaja si el usuario toca
    // el panel (Explorer §7.7).
    ...(options.includeContinuidad && lt.continuidad
      ? { continuidad: deriveContinuidadEditDefaults(lt.continuidad) }
      : {}),
    // Modo de cotización: una IO con continuidad persistida cobra la
    // DIFERENCIA, así que se rehidrata en modo "Continuar" (patrón PO).
    ...(options.includeContinuidad
      ? hidratarModoCotizacionDesdeItem({ liquidacion_tipo: lt })
      : { modo_cotizacion: MODO_COTIZACION_IO_NORMAL }),
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
  const [referenciaModalOpen, setReferenciaModalOpen] = useState(false);
  const [referenciaSeleccionada, setReferenciaSeleccionada] =
    useState<LiquidacionInspeccionObraListItem | null>(null);

  // Previa de la acción "Continuar" (solo aplica al modo create).
  const continuidadPrevia =
    mode === "create"
      ? (referenciaSeleccionada ?? props.continuidadPrevia ?? null)
      : null;

  // ── Hooks ──────────────────────────────────────────────────────────
  const crearMutation = useCrearInspeccionObra(
    mode === "legacy" ? "legacy" : "create",
  );
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
  // LiquidacionPreviaItem (que ya tiene la forma { liquidacion_general, ... })
  // — se pasa directo al shell que extrae previousValues. IO no tiene campo
  // de número de revisión: su liquidación queda fija en revisión 1.
  const sourceItem: LiquidacionInspeccionObraListItem | null =
    mode === "edit"
      ? props.item
      : mode === "relacionada" && props.previa
        ? (props.previa as unknown as LiquidacionInspeccionObraListItem)
        : null;

  // ── Reset del state específico al abrir el modal ───────────────
  useEffect(() => {
    if (open) {
      const inspector = sourceItem?.liquidacion_tipo.inspectores?.[0];
      setInspectorNombre(inspector?.perfil_ingeniero?.nombre_completo ?? "");
    }
  }, [open, sourceItem]);

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
      case "legacy":
        return "Registro Legacy";
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
      case "legacy":
        return "Registrar Legacy";
      case "edit":
        return "Guardar cambios";
      case "relacionada":
        return "Crear Relacionada";
    }
  })();

  const primaryLoadingLabel = mode === "edit" ? "Guardando..." : "Creando...";

  const primaryLoading =
    mode === "create" || mode === "legacy"
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
      m: "create" | "legacy" | "edit" | "nueva-revision" | "relacionada",
      item: typeof sourceItem,
    ): boolean => {
      if (m === "create" || m === "legacy") return true;
      if (m === "relacionada") return true;
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
      const tipoLiquidacionIdWatch =
        (methods.watch("tipo_liquidacion_id") as string) ?? "";
      const tipoLiquidacionIdSeleccionable = tipos.some(
        (t) => t.id === tipoLiquidacionIdWatch,
      )
        ? tipoLiquidacionIdWatch
        : "";

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
          legacy={mode === "legacy"}
          // En edición la cotización y el listado de tarifas usan los valores
          // HISTÓRICOS de `fecha_registro`: son los mismos con los que el
          // PATCH reprecia B (Explorer D6). Con valores vigentes, el preview
          // del panel de continuidad mentiría y la UI podría ofrecer una
          // tarifa que el PATCH rechaza con 400.
          mode={mode === "edit" ? "edit" : "create"}
          liquidacionId={
            mode === "edit" ? sourceItem?.liquidacion_general.id : undefined
          }
          fecha={
            mode === "edit"
              ? sourceItem?.liquidacion_general.fecha_registro
              : undefined
          }
          // El SmartField es el DUEÑO de los modos de cotización de IO:
          //  · `create` → el panel "Continuar" se abre con la previa (A) de la
          //    acción "Continuar" (o con ingreso manual).
          //  · `edit`   → el panel se rehidrata del registro persistido y
          //    permite mantener, activar o desactivar la continuidad (mismo
          //    PATCH).
          // `legacy` y `relacionada` no admiten continuidad: el selector de
          // modo no se monta y el contrato vigente queda intacto.
          soportaModoContinuidad={mode === "create" || mode === "edit"}
          continuidadPrevia={continuidadPrevia}
          continuidadPersistida={
            mode === "edit"
              ? (sourceItem?.liquidacion_tipo.continuidad ?? null)
              : null
          }
          onOpenReferencia={
            mode === "create" ? () => setReferenciaModalOpen(true) : undefined
          }
        />
      );

      return (
        <>
          {mode === "create" && (
            <ReferenceSelectionSync
              methods={methods}
              reference={referenciaSeleccionada}
            />
          )}
          <DefaultTipoLiquidacionSync
            methods={methods}
            tipoEdificacionId={
              tipos.find((tipo) => tipo.codigo === "EDIFICACION")?.id
            }
            enabled={mode === "create"}
          />
          <LiquidacionFormBodyBase
            control={methods.control as never}
            methods={methods}
            tramiteField={tramiteField}
            motorSection={motorSection}
            // El panel de continuidad ya vive DENTRO del SmartField (modo
            // "Continuar"): el modal no monta una sección independiente.
            valoresActualesSection={null}
            canEditProyecto={canEditProyecto}
            // IO es revision-less: no hay campo de número de revisión y su
            // liquidación permanece fija en revisión 1.
            showRevisionField={false}
          />
          {/* La búsqueda histórica conserva la misma operación seleccionada. */}
          {mode === "legacy" ? (
            <BuscarInspectorPorCipModal
              open={inspectorModalOpen}
              onOpenChange={setInspectorModalOpen}
              selectedOperacionId={
                methods.watch("inspector_operacion_id") || undefined
              }
              onSelect={(id, nombre, inspectorOperacionId) => {
                methods.setValue("inspector_id", id, { shouldValidate: false });
                methods.setValue(
                  "inspector_operacion_id",
                  inspectorOperacionId,
                  {
                    shouldValidate: false,
                  },
                );
                setInspectorNombre(nombre);
              }}
            />
          ) : (
            <SeleccionarInspectorModal
              open={inspectorModalOpen}
              onOpenChange={setInspectorModalOpen}
              tiposLiquidacion={tipos}
              tipoLiquidacionId={tipoLiquidacionIdSeleccionable}
              fallbackTipoLiquidacionCodigo={
                mode === "create" || mode === "edit"
                  ? null
                  : ((
                      sourceItem?.liquidacion_general as {
                        tipo_liquidacion?: { codigo?: string };
                      }
                    )?.tipo_liquidacion?.codigo ?? null)
              }
              {...(mode === "create" || mode === "edit"
                ? {
                    onTipoLiquidacionChange: (id: string) => {
                      methods.setValue("tipo_liquidacion_id", id, {
                        shouldValidate: false,
                      });
                      methods.setValue("inspector_id", "", {
                        shouldValidate: false,
                      });
                      methods.setValue("inspector_operacion_id", "", {
                        shouldValidate: false,
                      });
                      setInspectorNombre("");
                    },
                  }
                : {})}
              selectedId={methods.watch("inspector_id") || undefined}
              onSelect={(id, nombre, inspectorOperacionId) => {
                methods.setValue("inspector_id", id, {
                  shouldValidate: false,
                });
                methods.setValue(
                  "inspector_operacion_id",
                  inspectorOperacionId,
                  { shouldValidate: false },
                );
                setInspectorNombre(nombre);
              }}
            />
          )}
        </>
      );
    },
    [
      inspectorNombre,
      inspectorModalOpen,
      sourceItem,
      tipos,
      mode,
      continuidadPrevia,
    ],
  );

  const initialData: Partial<VisitasFormData> = (() => {
    if (mode === "create" || mode === "legacy") {
      // "Continuar": el modo de cotización arranca en CONTINUAR y el bloque
      // prellena con los datos de la liquidación previa (A).
      if (mode === "create" && continuidadPrevia) {
        return {
          cantidad_visitas: 1,
          modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
          continuidad: deriveContinuidadDefaults(continuidadPrevia),
        };
      }
      return {
        cantidad_visitas: 1,
        modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
      };
    }
    if (sourceItem) {
      return buildInitialData(sourceItem, {
        skipSmartFieldDefaults: mode === "relacionada",
        includeContinuidad: mode === "edit",
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
      const result = await editarMutation.mutateAsync(data);
      return result;
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
        tarifa_visitas_id: data.tarifa_visitas_id ?? "",
        inspector_operacion_id: data.inspector_operacion_id,
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
        schema={mode === "legacy" ? visitasLegacyFormSchema : visitasFormSchema}
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

      {mode === "create" && (
        <SeleccionarPreviaModal
          open={referenciaModalOpen}
          onOpenChange={setReferenciaModalOpen}
          tipoPermitido="INSPECCION_OBRA"
          title="Seleccionar IO de referencia"
          description="Busca una IO anterior para consultar sus datos y respaldar el saldo."
          onSelect={(previa) => {
            setReferenciaSeleccionada(
              previa as LiquidacionInspeccionObraListItem,
            );
            setReferenciaModalOpen(false);
          }}
        />
      )}

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
