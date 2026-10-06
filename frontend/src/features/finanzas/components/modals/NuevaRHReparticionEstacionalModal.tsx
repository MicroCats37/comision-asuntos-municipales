"use client";

/**
 * NuevaRHReparticionEstacionalModal — Modal wizard for creating RH Reparticion Estacional.
 *
 * Flow:
 * - Step 1: Configuration (periodo, trimester, especialidad)
 * - Step 2: Select delegates (checkbox list)
 * - Step 3: Preview + Cotizar / Confirm + Crear
 *
 * Endpoints:
 *   GET  /liquidaciones/especialidades-revision
 *   GET  /liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id=
 *   POST /finanzas/reparticiones-estacionales/cotizar
 *   POST /finanzas/reparticiones-estacionales
 */
import {
  Eye,
  FileSpreadsheet,
  Loader2,
  PieChart,
  Receipt,
  Settings2,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { notify } from "@/errors";
import { useCotizarRHReparticionEstacional } from "@/features/finanzas/hooks/useCotizarRHReparticionEstacional";
import { useCrearRHReparticionEstacional } from "@/features/finanzas/hooks/useCrearRHReparticionEstacional";
import type {
  RHReparticionEstacionalCotizar,
  RHReparticionEstacionalCotizarIn,
} from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";
import {
  useDelegadosVigentesPorEspecialidad,
  useEspecialidadesRevision,
} from "@/features/liquidaciones/hooks";

interface NuevaRHReparticionEstacionalModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type Step = 1 | 2 | 3;

const TRIMESTER_OPTIONS = [
  { value: "T1", label: "T1 (Ene–Mar)", mesDesde: 1, mesHasta: 3 },
  { value: "T2", label: "T2 (Abr–Jun)", mesDesde: 4, mesHasta: 6 },
  { value: "T3", label: "T3 (Jul–Sep)", mesDesde: 7, mesHasta: 9 },
  { value: "T4", label: "T4 (Oct–Dic)", mesDesde: 10, mesHasta: 12 },
];

const getCurrentYear = () => new Date().getFullYear();

const formatCurrency = (value?: number | null) =>
  value == null ? "S/ 0.00" : `S/ ${value.toFixed(2)}`;

/** Step guide entry — icon, short label, and long description per step */
type StepGuideEntry = {
  icon: typeof Settings2;
  label: string;
  description: string;
};

const STEP_GUIDE: Record<1 | 2 | 3, StepGuideEntry> = {
  1: {
    icon: Settings2,
    label: "Configurar",
    description: "Configura el periodo, trimestre y especialidad",
  },
  2: {
    icon: Users,
    label: "Seleccionar",
    description: "Selecciona los delegados vigentes para la distribución",
  },
  3: {
    icon: Eye,
    label: "Revisar",
    description: "Revisa la previsualización antes de confirmar",
  },
};

export function NuevaRHReparticionEstacionalModal({
  open,
  onOpenChange,
  onSuccess,
}: NuevaRHReparticionEstacionalModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [periodo, setPeriodo] = useState(String(getCurrentYear()));
  const [trimester, setTrimester] = useState<
    (typeof TRIMESTER_OPTIONS)[number] | null
  >(null);
  const [especialidadRevisionId, setEspecialidadRevisionId] =
    useState<string>("");
  const [selectedDelegadoIds, setSelectedDelegadoIds] = useState<Set<string>>(
    new Set(),
  );
  const [cotizarResult, setCotizarResult] =
    useState<RHReparticionEstacionalCotizar | null>(null);

  const cotizarMutation = useCotizarRHReparticionEstacional();
  const crearMutation = useCrearRHReparticionEstacional();

  const { data: especialidades, isLoading: isLoadingEspecialidades } =
    useEspecialidadesRevision();

  const { data: delegados, isLoading: isLoadingDelegados } =
    useDelegadosVigentesPorEspecialidad(
      especialidadRevisionId || null,
      null,
      true,
    );

  const resetForm = useCallback(() => {
    setStep(1);
    setPeriodo(String(getCurrentYear()));
    setTrimester(null);
    setEspecialidadRevisionId("");
    setSelectedDelegadoIds(new Set());
    setCotizarResult(null);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [onOpenChange, resetForm]);

  // ── Step 1 → 2: validate config and proceed ──────────────────────────────
  const handleNextStep1 = useCallback(() => {
    if (!periodo || !/^\d{4}$/.test(periodo)) {
      notify.error("Ingresa un periodo válido (YYYY)");
      return;
    }
    if (!trimester) {
      notify.error("Selecciona un trimestre");
      return;
    }
    if (!especialidadRevisionId) {
      notify.error("Selecciona una especialidad de revisión");
      return;
    }
    setCotizarResult(null);
    setStep(2);
  }, [periodo, trimester, especialidadRevisionId]);

  // ── Step 2 → 3: cotizar ─────────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    if (!trimester) return;
    if (selectedDelegadoIds.size === 0) {
      notify.error("Selecciona al menos un delegado");
      return;
    }

    const payload: RHReparticionEstacionalCotizarIn = {
      especialidad_revision_id: especialidadRevisionId,
      periodo: Number(periodo),
      mes_desde: trimester.mesDesde,
      mes_hasta: trimester.mesHasta,
      delegado_ids: Array.from(selectedDelegadoIds),
    };

    try {
      const result = await cotizarMutation.cotizar(payload);
      setCotizarResult(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [
    periodo,
    trimester,
    especialidadRevisionId,
    selectedDelegadoIds,
    cotizarMutation,
  ]);

  // ── Step 3: confirmar + crear ────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!trimester) return;

    const payload: RHReparticionEstacionalCotizarIn = {
      especialidad_revision_id: especialidadRevisionId,
      periodo: Number(periodo),
      mes_desde: trimester.mesDesde,
      mes_hasta: trimester.mesHasta,
      delegado_ids: Array.from(selectedDelegadoIds),
    };

    try {
      await crearMutation.crear(payload);
      notify.success("Repartición estacional creada correctamente");
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [
    periodo,
    trimester,
    especialidadRevisionId,
    selectedDelegadoIds,
    crearMutation,
    handleClose,
    onSuccess,
  ]);

  const isPending = cotizarMutation.isPending || crearMutation.isPending;

  // Delegate checkbox helpers
  const toggleDelegado = useCallback((id: string, checked: boolean) => {
    setSelectedDelegadoIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const isDelegadoSelected = useCallback(
    (id: string) => selectedDelegadoIds.has(id),
    [selectedDelegadoIds],
  );

  const selectedCount = selectedDelegadoIds.size;

  // Find especialidad nombre for display
  const selectedEspecialidadNombre =
    especialidades?.find((e) => e.id === especialidadRevisionId)?.nombre ?? "";

  return (
    <GenericModal open={open} onOpenChange={handleClose} preventClose={false}>
      <GenericModal.Content size="lg">
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
              <PieChart className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Finanzas — RH Trimestral
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                Nueva Trimestral
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                {STEP_GUIDE[step].description}
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6 px-6 py-5">
          {/* Icon-based step indicator */}
          <div className="flex items-center gap-2 justify-center py-1">
            {([1, 2, 3] as const).map((s) => {
              const StepIcon = STEP_GUIDE[s].icon;
              const isActive = step === s;
              const isCompleted = step > s;
              return (
                <div key={s} className="flex items-center gap-2">
                  <div className="flex flex-col items-center gap-1.5 min-w-[5rem]">
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all ${
                        isActive
                          ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/20"
                          : isCompleted
                            ? "bg-primary/15 text-primary border-primary/40"
                            : "bg-secondary/40 text-secondary-foreground/70 border-secondary/50"
                      }`}
                    >
                      <StepIcon className="h-4 w-4" />
                    </div>
                    <span
                      className={`text-[9px] font-bold uppercase tracking-wider text-center ${
                        isActive
                          ? "text-primary"
                          : isCompleted
                            ? "text-primary/70"
                            : "text-muted-foreground/70"
                      }`}
                    >
                      {s}. {STEP_GUIDE[s].label}
                    </span>
                  </div>
                  {s < 3 && (
                    <div
                      className={`h-0.5 w-10 rounded ${
                        step > s ? "bg-primary/50" : "bg-secondary/40"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* ── Step 1: Configuration ── */}
          {step === 1 && (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="periodo">Periodo (Año)</Label>
                  <Select value={periodo} onValueChange={setPeriodo}>
                    <SelectTrigger
                      id="periodo"
                      className="h-10 rounded-xl font-semibold"
                    >
                      <SelectValue placeholder="Seleccionar año" />
                    </SelectTrigger>
                    <SelectContent>
                      {[
                        getCurrentYear() - 1,
                        getCurrentYear(),
                        getCurrentYear() + 1,
                      ].map((y) => (
                        <SelectItem key={y} value={String(y)}>
                          {y}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="trimestre">Trimestre</Label>
                  <Select
                    value={trimester?.value ?? ""}
                    onValueChange={(v) => {
                      setTrimester(
                        TRIMESTER_OPTIONS.find((t) => t.value === v) ?? null,
                      );
                    }}
                  >
                    <SelectTrigger
                      id="trimestre"
                      className="h-10 rounded-xl font-semibold"
                    >
                      <SelectValue placeholder="Seleccionar trimestre" />
                    </SelectTrigger>
                    <SelectContent>
                      {TRIMESTER_OPTIONS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="especialidad">Especialidad de Revisión</Label>
                {isLoadingEspecialidades ? (
                  <div className="flex items-center gap-2 h-10 px-3 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Cargando especialidades…
                  </div>
                ) : (
                  <Select
                    value={especialidadRevisionId}
                    onValueChange={setEspecialidadRevisionId}
                  >
                    <SelectTrigger
                      id="especialidad"
                      className="h-10 rounded-xl font-semibold"
                    >
                      <SelectValue placeholder="Seleccionar especialidad" />
                    </SelectTrigger>
                    <SelectContent>
                      {(especialidades ?? []).map((e) => (
                        <SelectItem key={e.id} value={e.id}>
                          {e.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          )}

          {/* ── Step 2: Delegates ── */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Especialidad:
                  </span>
                  <span className="font-bold">
                    {selectedEspecialidadNombre}
                  </span>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-muted-foreground font-semibold">
                    Trimestre:
                  </span>
                  <span className="font-bold">{trimester?.label}</span>
                </div>
                <div className="flex justify-end mt-2">
                  <span className="text-sm font-bold text-primary">
                    {selectedCount} de {delegados?.length ?? 0} seleccionado(s)
                  </span>
                </div>
              </div>

              {isLoadingDelegados ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : !delegados || delegados.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-muted-foreground text-sm border border-dashed border-border rounded-xl">
                  <Users className="h-8 w-8 mb-2" />
                  No hay delegados vigentes para esta especialidad
                </div>
              ) : (
                <ScrollArea className="max-h-[400px]">
                  <div className="border border-border rounded-xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center gap-3 px-4 py-2.5 bg-muted/40 border-b border-border text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      <div className="w-6 shrink-0" />
                      <div className="w-8 shrink-0">#</div>
                      <div className="flex-1 min-w-0">Nombre completo</div>
                      <div className="w-20 shrink-0">CIP</div>
                    </div>
                    {delegados.map((d, idx) => {
                      const selected = isDelegadoSelected(d.id);
                      return (
                        <div
                          key={d.id}
                          className={`flex items-center gap-3 px-4 py-2.5 border-b border-border/50 last:border-b-0 transition-all duration-150 ${
                            selected ? "bg-primary/[0.04]" : "hover:bg-muted/30"
                          }`}
                        >
                          <Checkbox
                            id={`del-${d.id}`}
                            checked={selected}
                            onCheckedChange={(v) => toggleDelegado(d.id, !!v)}
                            className="shrink-0"
                          />
                          <div className="w-8 shrink-0 text-xs text-muted-foreground">
                            {idx + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">
                              {d.nombre_completo}
                            </p>
                          </div>
                          <div className="w-20 shrink-0">
                            <p className="text-xs font-mono text-muted-foreground">
                              {d.cip}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </div>
          )}

          {/* ── Step 3: Preview / Confirm ── */}
          {step === 3 && cotizarResult && (
            <div className="space-y-4">
              {/* Configuration summary */}
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Especialidad:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.especialidad_revision_nombre}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Periodo:
                  </span>
                  <span className="font-bold">{cotizarResult.periodo}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Trimestre:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.mes_desde}–{cotizarResult.mes_hasta}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Delegados:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.numero_delegados}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Capítulos:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.numero_capitulos}
                  </span>
                </div>
              </div>

              {/* Main summary card */}
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
                <h3 className="text-sm font-black uppercase tracking-wide text-primary">
                  Resumen de Distribución
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">
                      Total Fondo Común
                    </p>
                    <p className="text-base font-bold">
                      {formatCurrency(cotizarResult.total_fondo_comun)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">
                      Divisor Total
                    </p>
                    <p className="text-base font-bold">
                      {cotizarResult.divisor_total}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">
                      Monto por Participación
                    </p>
                    <p className="text-base font-bold text-primary">
                      {formatCurrency(cotizarResult.monto_por_participacion)}
                    </p>
                  </div>
                  {cotizarResult.residual != null &&
                    cotizarResult.residual !== 0 && (
                      <div>
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">
                          Residual
                        </p>
                        <p className="text-base font-bold text-muted-foreground">
                          {formatCurrency(cotizarResult.residual)}
                        </p>
                      </div>
                    )}
                </div>
              </div>

              {/* Delegates detail */}
              {cotizarResult.detalles_delegados.length > 0 && (
                <div className="rounded-xl border border-border overflow-hidden">
                  <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/30 border-b border-border">
                    <Users className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Detalle por Delegado (
                      {cotizarResult.detalles_delegados.length})
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-muted/40">
                          <th className="px-3 py-2 text-left font-bold uppercase tracking-wide text-muted-foreground">
                            #
                          </th>
                          <th className="px-3 py-2 text-left font-bold uppercase tracking-wide text-muted-foreground">
                            Delegado
                          </th>
                          <th className="px-3 py-2 text-right font-bold uppercase tracking-wide text-muted-foreground">
                            Monto
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {cotizarResult.detalles_delegados.map((det, idx) => {
                          const label =
                            det.delegado?.nombre_completo ?? det.delegado_id;
                          return (
                            <tr
                              key={det.delegado_id}
                              className="border-t border-border/50 hover:bg-muted/30"
                            >
                              <td className="px-3 py-2 text-muted-foreground">
                                {idx + 1}
                              </td>
                              <td className="px-3 py-2 font-medium">{label}</td>
                              <td className="px-3 py-2 text-right font-semibold">
                                {formatCurrency(det.monto)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Chapters detail */}
              {cotizarResult.detalles_capitulos.length > 0 && (
                <div className="rounded-xl border border-border overflow-hidden">
                  <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/30 border-b border-border">
                    <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Detalle por Capítulo (
                      {cotizarResult.detalles_capitulos.length})
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-muted/40">
                          <th className="px-3 py-2 text-left font-bold uppercase tracking-wide text-muted-foreground">
                            #
                          </th>
                          <th className="px-3 py-2 text-left font-bold uppercase tracking-wide text-muted-foreground">
                            Capítulo
                          </th>
                          <th className="px-3 py-2 text-right font-bold uppercase tracking-wide text-muted-foreground">
                            Monto
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {cotizarResult.detalles_capitulos.map((det, idx) => (
                          <tr
                            key={det.capitulo_id}
                            className="border-t border-border/50 hover:bg-muted/30"
                          >
                            <td className="px-3 py-2 text-muted-foreground">
                              {idx + 1}
                            </td>
                            <td className="px-3 py-2 font-medium">
                              {det.capitulo?.nombre ?? det.capitulo_id}
                            </td>
                            <td className="px-3 py-2 text-right font-semibold">
                              {formatCurrency(det.monto)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={
                step === 1
                  ? handleClose
                  : step === 2
                    ? () => setStep(1)
                    : () => setStep(2)
              }
              disabled={isPending}
              className="h-10 rounded-xl font-semibold"
            >
              {step === 1 ? "Cancelar" : "Atrás"}
            </Button>

            {step === 1 && (
              <Button
                type="button"
                onClick={handleNextStep1}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                Siguiente
              </Button>
            )}

            {step === 2 && (
              <Button
                type="button"
                onClick={handleCotizar}
                disabled={cotizarMutation.isPending || selectedCount === 0}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {cotizarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Cotizar ({selectedCount})
              </Button>
            )}

            {step === 3 && (
              <Button
                type="button"
                onClick={handleCrear}
                disabled={crearMutation.isPending}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {crearMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                <Receipt className="h-4 w-4" />
                Crear Repartición
              </Button>
            )}
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
