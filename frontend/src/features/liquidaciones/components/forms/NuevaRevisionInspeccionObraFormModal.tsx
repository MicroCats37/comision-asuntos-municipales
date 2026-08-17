"use client";

import {
  Building2,
  ClipboardCheck,
  FileText,
  HardHat,
  IdCard,
  MapPin,
} from "lucide-react";
/**
 * NuevaRevisionInspeccionObraFormModal — Form LIVIANO para nueva revisión de Inspección de Obra
 * (primera-revisión desde liquidación previa).
 *
 * Schema propio reducido (NO usa el form general):
 *  - Se hereda de la previa: proyecto, municipalidad, entidad, expediente, observacion, retencion
 *  - Se edita: cantidad_visitas, categoria, tarifa_visitas_id, inspector_id
 *
 * Layout responsivo 2 columnas como los demás formularios.
 * El cálculo (visitas × costo por visita + IGV) lo maneja TarifasVisitasNuevaRevisionSmartField.
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision-desde-previa
 */
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useCrearInspeccionObraDesdePrevia } from "../../hooks/useCrearInspeccionObraDesdePrevia";
import type { LiquidacionGeneralItem } from "../../hooks/useLiquidacionesGenerales";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import {
  type NuevaRevisionInspeccionObraFormData,
  nuevaRevisionInspeccionObraFormSchema,
} from "../../schemas/liquidacion-nueva-revision-io.schema";
import { SeleccionarInspectorModal } from "./SeleccionarInspectorModal";
import { TarifasVisitasNuevaRevisionSmartField } from "./TarifasVisitasNuevaRevisionSmartField";

interface NuevaRevisionInspeccionObraFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Liquidación previa COMPLETA (output general) — se hereda proyecto/municipalidad/entidad */
  previa: LiquidacionGeneralItem | null;
  onSuccess?: () => void;
}

const formatSoles = (value: number | undefined | null): string =>
  value == null
    ? "—"
    : `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatDate = (value?: string | null): string => {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("es-PE", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
};

export function NuevaRevisionInspeccionObraFormModal({
  open,
  onOpenChange,
  previa,
  onSuccess,
}: NuevaRevisionInspeccionObraFormModalProps) {
  const crearMutation = useCrearInspeccionObraDesdePrevia();

  // Estados locales que alimentan el form (cantidad_visitas, categoria, tarifa)
  const [cantidadVisitas, setCantidadVisitas] = useState(1);
  const [categoria, setCategoria] = useState("");
  const [tarifaVisitasId, setTarifaVisitasId] = useState<string | null>(null);
  const [inspectorModalOpen, setInspectorModalOpen] = useState(false);
  const [inspectorNombre, setInspectorNombre] = useState("");

  // Reset del estado local al abrir
  useEffect(() => {
    if (open) {
      setCantidadVisitas(1);
      setCategoria("");
      setTarifaVisitasId(null);
      setInspectorNombre("");
    }
  }, [open]);

  const lg = previa;

  const handleSubmit = useCallback(
    async (data: NuevaRevisionInspeccionObraFormData) => {
      if (!previa) return;
      try {
        const result = await crearMutation.mutateAsync({
          ...data,
          liquidacion_previa_id: previa.id,
        });
        const created = (result as { data?: unknown })?.data as
          | PdfLiquidacionItem
          | undefined;
        // Mismo window de impresión que el botón PDF de las cards
        if (created) {
          printLiquidacion(created, "inspeccion-obra");
        }
        notify.success("Revisión de Inspección de Obra creada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, previa, onSuccess],
  );

  const initialData: Partial<NuevaRevisionInspeccionObraFormData> = {
    liquidacion_previa_id: previa?.id ?? "",
    cantidad_visitas: 1,
    categoria: "",
    tarifa_visitas_id: "",
    inspector_id: "",
  };

  return (
    <AppFormModal<NuevaRevisionInspeccionObraFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Nueva Liquidación"
      description={
        lg
          ? `Basada en: ${lg.proyecto.denominacion}`
          : "Crea la primera liquidación de Inspección de Obra"
      }
      eyebrow="Inspección de Obra — Primera Liquidación"
      icon={<ClipboardCheck className="h-5 w-5 text-primary" />}
      primaryLabel="Crear Liquidación"
      primaryLoadingLabel="Creando..."
      primaryLoading={crearMutation.isPending}
      onPrimary={() => undefined}
      schema={nuevaRevisionInspeccionObraFormSchema}
      initialData={initialData as never}
      onSubmit={handleSubmit}
      size="lg"
    >
      {({ methods }) => (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* ── Columna Izquierda: card de Datos Anteriores ── */}
            <div className="space-y-4">
              {lg && (
                <div className="rounded-xl border border-border/50 bg-muted/20 p-5 space-y-4 h-full">
                  <div className="flex items-center gap-2 border-b border-border/40 pb-3">
                    <FileText className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Datos Anteriores
                    </h3>
                  </div>

                  {/* Header: proyecto + revision */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
                        <Building2 className="h-6 w-6 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-base font-bold text-foreground truncate">
                          {lg.proyecto.denominacion}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {lg.municipalidad?.codigo
                            ? `${lg.municipalidad.codigo} - `
                            : ""}
                          {lg.municipalidad?.nombre ?? "—"}
                        </p>
                      </div>
                    </div>
                    <span className="shrink-0 inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-sm font-bold text-primary">
                      Rev. {lg.numero_revision}
                    </span>
                  </div>

                  {/* Grid de datos heredados */}
                  <div className="grid grid-cols-2 gap-x-5 gap-y-3 text-sm">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Expediente
                      </span>
                      <span className="font-medium truncate">
                        {lg.expediente || "—"}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Fecha Registro
                      </span>
                      <span className="font-medium">
                        {formatDate(lg.fecha_registro)}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Propietario
                      </span>
                      <span className="font-medium truncate">
                        {lg.proyecto.nombre_propietario || "—"}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Tipo
                      </span>
                      <span className="font-medium">
                        {lg.tipo_liquidacion?.nombre ?? "—"}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Subtotal
                      </span>
                      <span className="font-medium">
                        {formatSoles(lg.sub_total)}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Total
                      </span>
                      <span className="font-medium">
                        {formatSoles(lg.total)}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Creado Por
                      </span>
                      <span className="font-medium truncate">
                        {lg.usuario_creador
                          ? [
                              lg.usuario_creador.nombres,
                              lg.usuario_creador.apellidos,
                            ]
                              .filter(Boolean)
                              .join(" ") ||
                            lg.usuario_creador.username ||
                            "—"
                          : "—"}
                      </span>
                    </div>
                  </div>

                  {/* Entidad */}
                  {lg.proyecto.entidad && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground border-t border-border/40 pt-3">
                      <IdCard className="h-3 w-3 text-primary/60 shrink-0" />
                      <span className="truncate">
                        {lg.proyecto.entidad.razon_social} ·{" "}
                        {lg.proyecto.entidad.tipo_documento}{" "}
                        {lg.proyecto.entidad.numero_documento}
                      </span>
                    </div>
                  )}
                  {lg.proyecto.direccion && (
                    <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">
                        {lg.proyecto.direccion}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ── Columna Derecha: Inspector + Datos Visitas + Cálculo ── */}
            <div className="space-y-4">
              {/* Inspector */}
              <div className="rounded-xl border border-border/50 bg-card p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                  <HardHat className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Inspector Asignado
                  </h3>
                </div>
                {/* Botón que abre el modal de selección de inspector */}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setInspectorModalOpen(true)}
                  disabled={!previa?.tipo_liquidacion?.codigo}
                  className="w-full gap-2"
                >
                  <HardHat className="h-4 w-4" />
                  {inspectorNombre
                    ? `Inspector: ${inspectorNombre}`
                    : "Seleccionar inspector"}
                </Button>
              </div>
              <TarifasVisitasNuevaRevisionSmartField
                cantidadVisitas={cantidadVisitas}
                categoria={categoria}
                tarifaVisitasId={tarifaVisitasId}
                onCantidadVisitasChange={(v) => {
                  setCantidadVisitas(v);
                  methods.setValue("cantidad_visitas", v, {
                    shouldValidate: true,
                  });
                }}
                onCategoriaChange={(c) => {
                  setCategoria(c);
                  methods.setValue("categoria", c, { shouldValidate: true });
                }}
                onTarifaChange={(id) => {
                  setTarifaVisitasId(id);
                  methods.setValue("tarifa_visitas_id", id, {
                    shouldValidate: true,
                  });
                }}
              />

              {/* Nota sobre herencia */}
              <div className="rounded-lg bg-muted/20 border border-border/40 p-3">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  La nueva liquidación heredará{" "}
                  <span className="font-semibold text-foreground">
                    proyecto, municipalidad, entidad, expediente y observación
                  </span>{" "}
                  de la liquidación previa. Solo se calculan las visitas de la
                  nueva inspección.
                </p>
              </div>
            </div>
          </div>

          {/* Modal de selección de inspector (adjunta inspector_id al form) */}
          <SeleccionarInspectorModal
            open={inspectorModalOpen}
            onOpenChange={setInspectorModalOpen}
            tipoLiquidacion={previa?.tipo_liquidacion?.codigo ?? null}
            categoriaForm={categoria || null}
            selectedId={methods.watch("inspector_id") || undefined}
            onSelect={(id, nombre) => {
              methods.setValue("inspector_id", id, { shouldValidate: true });
              setInspectorNombre(nombre);
            }}
          />
        </>
      )}
    </AppFormModal>
  );
}
