"use client";

import { FileText, MessageSquare, Building2, CheckCircle2, Loader2, MapPin, Banknote, Hash, FileCheck } from "lucide-react";
import { useCallback, useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { useCrearNuevaRevision } from "../hooks/useNuevaRevision";
import { useCotizacionNuevaRevision } from "../hooks/useCotizacion";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import { useRevisionesVigentes } from "../hooks/useRevisionesVigentes";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";
import { CotizacionSection } from "./CotizacionSection";
import { ProyectistasSection } from "./ProyectistasSection";
import { notify } from "@/errors";
import type { ProyectistaResult } from "../types/proyectista";
import type { CotizacionQuote, LiquidacionSnapshotListItem } from "../types/liquidacion-edificaciones";
import { z } from "zod";

/** Format enum values to human-readable labels */
function formatEnumLabel(value: string | undefined | null): string {
  if (!value) return "—";
  const KNOWN: Record<string, string> = {
    OBRA_NUEVA: "Obra nueva",
    PRIMERA_REVISION: "Primera revisión",
    // Add more known mappings here as needed
  };
  if (KNOWN[value]) return KNOWN[value];
  // Generic fallback: replace underscores with spaces, lower-case, capitalize first letter
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

interface NuevaRevisionFormModalProps {
  /** Snapshot list item with inherited project/municipalidad data */
  liquidacionBase: LiquidacionSnapshotListItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const nuevaRevisionSchema = z.object({
  observacion: z.string().optional(),
});

type FormData = z.infer<typeof nuevaRevisionSchema>;

export function NuevaRevisionFormModal({
  liquidacionBase,
  open,
  onOpenChange,
  onSuccess,
}: NuevaRevisionFormModalProps) {
  // Child modal state
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);

  // Selected proyectistas — initialized empty; synced via useEffect when liquidacionBase changes
  const [selectedProyectistas, setSelectedProyectistas] = useState<ProyectistaResult[]>([]);

  // Sync selectedProyectistas when liquidacionBase changes (modal opened / base data loaded)
  useEffect(() => {
    if (!liquidacionBase?.edificaciones.proyectistas) {
      setSelectedProyectistas([]);
      return;
    }
    setSelectedProyectistas(
      liquidacionBase.edificaciones.proyectistas.map((p) => ({
        id: p.id,
        nombres: p.nombres,
        apellidos: p.apellidos,
        cip: p.cip ?? undefined,
        dni: p.dni ?? "",
        cap: p.cap ?? undefined,
        creado: false,
      }))
    );
  }, [liquidacionBase]);

  // Revisiones state
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<string[]>([]);

  // Cotización state
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionQuote | null>(null);

  // Data hooks
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();
  const { data: revisionesVigentes, isLoading: isLoadingRevisiones } =
    useRevisionesVigentes();
  const crearMutation = useCrearNuevaRevision();

  // Cotización hook
  const cotizacionMutation = useCotizacionNuevaRevision();

  // Handle proyectista saved (created or selected)
  const handleProyectistaSaved = useCallback((proyectista: ProyectistaResult) => {
    setSelectedProyectistas((prev) => {
      if (prev.some((p) => p.id === proyectista.id)) {
        return prev;
      }
      return [...prev, proyectista];
    });
    setShowProyectistaModal(false);
  }, []);

  // Remove proyectista from selection
  const handleRemoveProyectista = useCallback((proyectistaId: string) => {
    setSelectedProyectistas((prev) => prev.filter((p) => p.id !== proyectistaId));
  }, []);

  // Handle revision toggle
  const handleRevisionToggle = useCallback((revisionId: string) => {
    setSelectedRevisionIds((prev) => {
      const isSelected = prev.includes(revisionId);
      if (isSelected) {
        return prev.filter((id) => id !== revisionId);
      } else {
        return [...prev, revisionId];
      }
    });
  }, []);

  // Clear cotizacion when relevant fields change
  const watchedValuesRef = useRef<{ revisiones_ids: string[] }>({ revisiones_ids: [] });
  useEffect(() => {
    if (cotizacionQuote !== null) {
      setCotizacionQuote(null);
    }
  }, [selectedRevisionIds]);

  // Handle cotizar
  const handleCotizar = useCallback(async () => {
    if (!liquidacionBase?.liquidacion_id || selectedRevisionIds.length === 0) {
      return;
    }

    try {
      const result = await cotizacionMutation.mutateAsync({
        liquidacion_previa_id: liquidacionBase.liquidacion_id,
        revisiones_ids: selectedRevisionIds,
      });
      setCotizacionQuote(result);
    } catch {
      // Error is handled by the mutation
    }
  }, [cotizacionMutation, liquidacionBase, selectedRevisionIds]);

  // Handle close
  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      onOpenChange(false);
    }
  };

  // Handle form submit
  const handleSubmit = async (data: FormData) => {
    if (!liquidacionBase?.liquidacion_id) {
      alert("No se ha seleccionado una liquidación previa");
      return;
    }

    if (selectedRevisionIds.length === 0) {
      alert("Debe seleccionar al menos una revisión");
      return;
    }

    if (selectedProyectistas.length === 0) {
      alert("Debe seleccionar al menos un proyectista");
      return;
    }

    const submitData = {
      liquidacion_previa_id: liquidacionBase.liquidacion_id,
      revisiones_ids: selectedRevisionIds,
      proyectistas_ids: selectedProyectistas.map((p) => p.id),
      observacion: data.observacion || undefined,
    };

    await crearMutation.mutateAsync(submitData);
    notify.success("Nueva revisión creada correctamente");
    onSuccess?.();
    // Reset state
    setSelectedRevisionIds([]);
    setCotizacionQuote(null);
  };

  // Form instance
  const formMethods = useForm<FormData>({
    resolver: zodResolver(nuevaRevisionSchema),
    defaultValues: {
      observacion: "",
    },
  });
  const {
    register,
    control,
    formState: { errors },
    watch,
    setValue,
  } = formMethods;

  // Derived data from liquidacionBase
  const hasProject = !!liquidacionBase?.liquidacion_id;
  const hasValidRevisiones = selectedRevisionIds.length > 0;
  const numeroRevision = liquidacionBase?.edificaciones.numero_revision ?? 0;
  const nuevoNumeroRevision = numeroRevision + 1;

  return (
    <>
      <GenericModal
        open={open}
        onOpenChange={handleClose}
        preventClose={crearMutation.isPending}
      >
        <GenericModal.Content size="lg">
          {/* ── Header ─────────────────────────────────────────────── */}
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Edificaciones
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                  Nueva Revisión
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  Registra una nueva revisión de edificación
                </p>
              </div>
              <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          {/* ── Body ─────────────────────────────────────────────── */}
          <GenericModal.Body>
            <form
              id="nueva-revision-form"
              onSubmit={formMethods.handleSubmit(handleSubmit)}
            >
            <div className="h-full flex flex-col min-h-0">
              {/* Grid layout */}
              <style>{`
                @media (min-width: 768px) {
                  .nueva-revision-grid {
                    grid-template-areas:
                      "datos datos"
                      "revisiones proyectistas"
                      "cotizacion cotizacion";
                    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                  }
                }
                @media (max-width: 767px) {
                  .nueva-revision-grid {
                    grid-template-areas:
                      "datos"
                      "revisiones"
                      "proyectistas"
                      "cotizacion";
                    grid-template-columns: 1fr;
                  }
                }
              `}</style>

              <div className="nueva-revision-grid grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">

                {/* ── DATOS INHERITADOS (Read-only) ─────────────────── */}
                <div
                  className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                  style={{ gridArea: 'datos' }}
                >
                  {/* Header */}
                  <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                    <Building2 className="h-4 w-4" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Datos de Liquidación Previa
                    </h3>
                  </div>

                  {/* Trámite info — displayed as chips */}
                  <div className="space-y-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Tipo de Trámite
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20 text-sm font-semibold text-primary">
                        <FileCheck className="h-3.5 w-3.5" />
                        {formatEnumLabel(liquidacionBase?.edificaciones.tipo_tramite)}
                      </span>
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary border border-border text-sm font-semibold text-foreground">
                        {formatEnumLabel(liquidacionBase?.edificaciones.tramite_accion)}
                      </span>
                    </div>
                  </div>

                  {/* Revisión number */}
                  <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/40 border border-border/50">
                    <span className="text-xs font-medium text-muted-foreground">
                      Número de Revisión
                    </span>
                    <span className="text-sm font-bold text-foreground">
                      {numeroRevision} → {nuevoNumeroRevision}
                    </span>
                  </div>

                  {/* Project info section */}
                  <div className="space-y-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Proyecto
                    </p>
                    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
                      {/* ID */}
                      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                        <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                          <Hash className="h-3 w-3" /> ID Proyecto
                        </span>
                        <span className="text-xs font-mono font-medium text-foreground truncate max-w-[140px]" title={liquidacionBase?.proyecto.public_id}>
                          {liquidacionBase?.proyecto.public_id ?? "—"}
                        </span>
                      </div>
                      {/* Nombre */}
                      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                        <span className="text-xs text-muted-foreground">Nombre</span>
                        <span className="text-xs font-semibold text-foreground text-right truncate max-w-[160px]" title={liquidacionBase?.proyecto.nombre}>
                          {liquidacionBase?.proyecto.nombre ?? "—"}
                        </span>
                      </div>
                      {/* Valor */}
                      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                        <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                          <Banknote className="h-3 w-3" /> Valor (S/)
                        </span>
                        <span className="text-xs font-bold text-foreground">
                          {liquidacionBase?.proyecto.valor_proyecto != null
                            ? liquidacionBase.proyecto.valor_proyecto.toLocaleString("es-PE", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })
                            : "—"}
                        </span>
                      </div>
                      {/* Entidad */}
                      {liquidacionBase?.proyecto.entidad && (
                        <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                          <span className="text-xs text-muted-foreground">Entidad</span>
                          <span className="text-xs font-semibold text-foreground text-right truncate max-w-[160px]" title={liquidacionBase.proyecto.entidad?.nombre ?? ""}>
                            {liquidacionBase.proyecto.entidad?.nombre ?? "—"}
                          </span>
                        </div>
                      )}
                      {/* Dirección */}
                      {liquidacionBase?.proyecto.direccion && (
                        <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                          <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                            <MapPin className="h-3 w-3" /> Dirección
                          </span>
                          <span className="text-xs font-semibold text-foreground text-right truncate max-w-[160px]" title={liquidacionBase.proyecto.direccion ?? ""}>
                            {liquidacionBase.proyecto.direccion ?? "—"}
                          </span>
                        </div>
                      )}
                      {/* Distrito */}
                      {liquidacionBase?.proyecto.distrito && (
                        <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                          <span className="text-xs text-muted-foreground">Distrito</span>
                          <span className="text-xs font-semibold text-foreground">
                            {liquidacionBase.proyecto.distrito?.nombre ?? "—"}
                          </span>
                        </div>
                      )}
                      {/* Municipalidad */}
                      {liquidacionBase?.municipalidad && (
                        <div className="flex items-center justify-between px-3 py-2">
                          <span className="text-xs text-muted-foreground">Municipalidad</span>
                          <span className="text-xs font-semibold text-foreground">
                            {liquidacionBase.municipalidad.nombre ?? "—"}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Liquidación ID */}
                  <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-muted/40 border border-border/50">
                    <span className="text-xs font-medium text-muted-foreground">
                      ID Liquidación Previa
                    </span>
                    <span className="text-xs font-mono font-medium text-primary truncate max-w-[140px]" title={liquidacionBase?.liquidacion_id ?? ""}>
                      {liquidacionBase?.liquidacion_id
                        ? `...${liquidacionBase.liquidacion_id.slice(-8)}`
                        : "—"}
                    </span>
                  </div>

                  {/* Observación field */}
                  <div className="pt-2">
                    <GenericInput
                      field={{
                        name: "observacion",
                        label: "Observación (opcional)",
                        type: "textarea",
                        placeholder: "Observaciones adicionales...",
                        icon: MessageSquare,
                        labelClassName: "text-primary font-semibold",
                      }}
                      register={register as any}
                      control={control as any}
                      errors={errors}
                    />
                  </div>
                </div>

                {/* ── Revisiones/Especialidades ─────────────────────────── */}
                <div
                  className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                  style={{ gridArea: 'revisiones' }}
                >
                  <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                    <FileText className="h-4 w-4" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Revisiones / Especialidades
                    </h3>
                    <span className="ml-auto text-[10px] font-medium opacity-75">
                      (seleccionar mínimo 1)
                    </span>
                  </div>

                  <RevisionesVigentesTable
                    revisiones={revisionesVigentes || []}
                    selectedIds={selectedRevisionIds}
                    onToggleRevision={handleRevisionToggle}
                    isLoading={isLoadingRevisiones}
                  />
                </div>

                {/* ── Proyectistas ──────────────────────────────────────── */}
                <div
                  className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                  style={{ gridArea: 'proyectistas' }}
                >
                  <ProyectistasSection
                    selectedProyectistas={selectedProyectistas}
                    onAddProyectista={() => setShowProyectistaModal(true)}
                    onRemoveProyectista={handleRemoveProyectista}
                  />
                </div>

                {/* ── Cotizar / Resumen de Cálculo ────────────────────────── */}
                <div
                  className="overflow-auto min-h-0"
                  style={{ gridArea: 'cotizacion' }}
                >
                  <CotizacionSection
                    quote={cotizacionQuote}
                    isLoading={cotizacionMutation.isPending}
                    onCotizar={handleCotizar}
                    hasErrors={Object.keys(errors).length > 0}
                    hasProject={hasProject}
                    hasValidValorProyecto={hasProject}
                    variablesFinancieras={variablesFinancieras}
                    isLoadingVariables={isLoadingVariables}
                  />
                </div>
              </div>
            </div>
            </form>
          </GenericModal.Body>

          {/* ── Footer ─────────────────────────────────────────────── */}
          <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
            <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={crearMutation.isPending}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
                aria-label="Cancelar"
              >
                <FileText className="h-4 w-4 sm:hidden" />
                <span className="hidden sm:inline">Cancelar</span>
              </Button>
              <Button
                type="submit"
                form="nueva-revision-form"
                disabled={crearMutation.isPending || selectedRevisionIds.length === 0}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[160px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
                aria-label="Crear Revisión"
              >
                {crearMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {!crearMutation.isPending && <CheckCircle2 className="h-4 w-4 sm:hidden" />}
                <span className="hidden sm:inline">
                  {crearMutation.isPending ? "Creando..." : "Crear Revisión"}
                </span>
              </Button>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      {/* Child Modal: Proyectista */}
      <ProyectistaFormModal
        open={showProyectistaModal}
        onOpenChange={setShowProyectistaModal}
        onSaved={handleProyectistaSaved}
      />
    </>
  );
}
