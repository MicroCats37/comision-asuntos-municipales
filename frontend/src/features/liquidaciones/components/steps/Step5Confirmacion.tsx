"use client";

import {
  BadgeCheck,
  Banknote,
  Building2,
  Calculator,
  CheckCircle2,
  FileText,
  Mail,
  MapPin,
  Phone,
  Receipt,
  User,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
import { useCotizacionPrimeraRevision } from "../../hooks/useCotizacion";
import type { VariablesFinancieras } from "../../types/liquidacion-edificaciones";
import type { LiquidacionStepperStore } from "../../store";

const TIPO_TRAMITE_LABELS: Record<string, string> = {
  OBRA_NUEVA: "Obra nueva",
  DEMOLICION: "Demolición",
  AMPLIACION: "Ampliación",
  REMODELACION: "Remodelación",
  MODIFICACION_LICENCIA: "Modificación de licencia",
  REINTEGRO: "Reintegro",
  PROYECTO_CON_PLANTAS_TIPICAS: "Proyecto con plantas típicas",
};

interface DataRowProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

function DataRow({ label, children, className = "" }: DataRowProps) {
  return (
    <div className={`space-y-0.5 min-w-0 ${className}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="text-sm font-medium text-foreground">{children}</div>
    </div>
  );
}

interface SectionTitleProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
}

function SectionTitle({ icon: Icon, title }: SectionTitleProps) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="p-1.5 bg-primary/10 rounded-md text-primary">
        <Icon className="h-3.5 w-3.5" />
      </div>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
    </div>
  );
}

interface Step5ConfirmacionProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  store: LiquidacionStepperStore;
  // Data for labels
  municipalidades?: Array<{ id: string; nombre: string }>;
  especialidadLabels?: Record<string, string>;
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
}

export function Step5Confirmacion({
  methods,
  isActive,
  store,
  municipalidades = [],
  especialidadLabels = {},
  variablesFinancieras,
  isLoadingVariables,
}: Step5ConfirmacionProps) {
  const {
    selectedProyecto,
    proyectoInline,
    selectedProyectistas,
    selectedContactos,
    selectedTarifasIds,
    cotizacion,
    setCotizacionQuote,
    setCotizacionCalculating,
    setCotizacionError,
  } = store;

  const cotizacionMutation = useCotizacionPrimeraRevision();
  const hasAutoCalculated = useRef(false);

  const { watch } = methods;
  const watchedValues = watch([
    "municipalidad_id",
    "tipo_tramite",
    "valor_proyecto",
    "expediente",
    "valor_base_calculo",
    "observacion",
  ]);
  const [
    municipalidadId,
    tipoTramite,
    valorProyecto,
    expediente,
    valorBaseCalculo,
    observacion,
  ] = watchedValues;

  const municipalidad = municipalidades.find((m) => m.id === municipalidadId);
  const cotizacionQuote = cotizacion.quote;

  const valorBase =
    valorBaseCalculo && Number(valorBaseCalculo) > 0
      ? Number(valorBaseCalculo)
      : Number(valorProyecto);
  const hasValidValorBase = Number(valorBase) > 0;
  const hasVariablesFinancieras = !!variablesFinancieras;
  const hasTarifa = selectedTarifasIds.length === 1;
  const hasAllDependencies =
    hasValidValorBase && hasVariablesFinancieras && hasTarifa;

  const formatSoles = (value: number) =>
    `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;

  // Stable refs for latest values used in the cotizacion callback
  const latestRef = useRef({
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite,
    valorProyecto,
    valorBase,
  });
  latestRef.current = {
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite,
    valorProyecto,
    valorBase,
  };

  const runCotizacion = useCallback(async () => {
    const latest = latestRef.current;
    if (
      !latest.hasValidValorBase ||
      !latest.hasTarifa ||
      latest.selectedTarifasIds.length === 0
    )
      return;

    setCotizacionCalculating(true);
    setCotizacionError(null);

    try {
      const result = await cotizacionMutation.mutateAsync({
        tipo_tramite: latest.tipoTramite as string,
        valor_proyecto: Number(latest.valorProyecto),
        valor_base_calculo: latest.valorBase,
        tarifas_ids: latest.selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
    } finally {
      setCotizacionCalculating(false);
    }
  }, [
    cotizacionMutation,
    setCotizacionCalculating,
    setCotizacionError,
    setCotizacionQuote,
  ]);

  // Auto-calculate when entering confirmation if no quote exists
  useEffect(() => {
    if (!isActive) {
      hasAutoCalculated.current = false;
      return;
    }

    if (
      hasAllDependencies &&
      !cotizacionQuote &&
      !hasAutoCalculated.current &&
      !cotizacion.isCalculating &&
      !isLoadingVariables
    ) {
      hasAutoCalculated.current = true;
      runCotizacion();
    }
  }, [
    isActive,
    hasAllDependencies,
    cotizacionQuote,
    cotizacion.isCalculating,
    isLoadingVariables,
    runCotizacion,
  ]);

  if (!isActive) return null;

  const hasProyecto = !!selectedProyecto || !!proyectoInline;

  return (
    <div className="space-y-4 min-w-0 max-w-full">
      {/* Header summary */}
      <div className="flex items-center gap-4 p-4 rounded-xl bg-primary/5 border border-primary/20">
        <div className="p-2.5 bg-primary/15 rounded-lg text-primary shadow-sm">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-bold text-foreground leading-tight">
            Revisión final
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Verifica que toda la información sea correcta antes de crear la
            liquidación
          </p>
        </div>
      </div>

      {/* Single card with all data */}
      <div className="rounded-xl border border-border bg-card overflow-hidden min-w-0">
        {/* Card header */}
        <div className="flex items-center gap-2 px-4 py-3 bg-muted/40 border-b border-border">
          <div className="p-1.5 bg-primary/10 rounded-md text-primary">
            <FileText className="h-3.5 w-3.5" />
          </div>
          <h4 className="text-sm font-semibold text-foreground">
            Resumen de la liquidación
          </h4>
        </div>

        {/* Card content — horizontal on desktop, vertical on mobile */}
        <div className="p-4">
          <div className="flex flex-col lg:flex-row gap-6 min-w-0">
            {/* Left column: Proyecto + Liquidación */}
            <div className="flex-1 min-w-0 space-y-4">
              {/* Proyecto */}
              <div className="bg-muted/20 rounded-lg p-4">
                <SectionTitle icon={Building2} title="Proyecto" />
                {!hasProyecto ? (
                  <p className="text-sm text-muted-foreground italic">
                    Sin proyecto seleccionado
                  </p>
                ) : selectedProyecto ? (
                  <div className="space-y-3 min-w-0">
                    <DataRow label="Denominación">
                      {selectedProyecto.denominacion}
                    </DataRow>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <DataRow label="Código">
                        {selectedProyecto.public_id}
                      </DataRow>
                      {selectedProyecto.direccion && (
                        <DataRow label="Dirección">
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3 text-muted-foreground" />
                            {selectedProyecto.direccion}
                          </span>
                        </DataRow>
                      )}
                      {selectedProyecto.distrito && (
                        <DataRow label="Distrito">
                          {selectedProyecto.distrito}
                        </DataRow>
                      )}
                    </div>
                    {selectedProyecto.entidad?.nombre && (
                      <DataRow label="Entidad">
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3 w-3 text-muted-foreground" />
                          {selectedProyecto.entidad.nombre}
                        </span>
                      </DataRow>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3 min-w-0">
                    <DataRow label="Denominación">
                      {proyectoInline?.denominacion}
                    </DataRow>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {proyectoInline?.direccion && (
                        <DataRow label="Dirección">
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3 text-muted-foreground" />
                            {proyectoInline.direccion}
                          </span>
                        </DataRow>
                      )}
                      <DataRow label="Propietario">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3 text-muted-foreground" />
                          {proyectoInline?.nombre_propietario}
                        </span>
                      </DataRow>
                    </div>
                    {proyectoInline?.entidad && (
                      <DataRow label="Entidad">
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3 w-3 text-muted-foreground" />
                          {proyectoInline.entidad.razon_social} (
                          {proyectoInline.entidad.tipo_documento}:{" "}
                          {proyectoInline.entidad.numero_documento})
                        </span>
                      </DataRow>
                    )}
                  </div>
                )}
              </div>

              {/* Liquidación */}
              <div className="bg-muted/20 rounded-lg p-4">
                <SectionTitle icon={Banknote} title="Liquidación" />
                <div className="space-y-3 min-w-0">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <DataRow label="Municipalidad">
                      {municipalidad?.nombre ?? "—"}
                    </DataRow>
                    <DataRow label="Tipo Trámite">
                      {TIPO_TRAMITE_LABELS[tipoTramite as string] ??
                        (tipoTramite as string) ??
                        "—"}
                    </DataRow>
                    <DataRow label="Valor Proyecto">
                      <span className="text-primary">
                        {formatSoles(Number(valorProyecto || 0))}
                      </span>
                    </DataRow>
                    {expediente && (
                      <DataRow label="Expediente">{expediente}</DataRow>
                    )}
                    {valorBaseCalculo && valorBaseCalculo !== valorProyecto && (
                      <DataRow label="Valor Base Cálculo">
                        {formatSoles(Number(valorBaseCalculo))}
                      </DataRow>
                    )}
                  </div>
                  {observacion && (
                    <DataRow label="Observación">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {observacion}
                      </p>
                    </DataRow>
                  )}
                </div>
              </div>
            </div>

            {/* Divider on desktop */}
            <div className="hidden lg:block w-px bg-border shrink-0" />

            {/* Mobile divider */}
            <div className="lg:hidden h-px bg-border shrink-0" />

            {/* Center column: Tarifa + Proyectistas + Contactos */}
            <div className="flex-[1.5] min-w-0 space-y-4">
              {/* Tarifa / Revisión */}
              <div className="bg-muted/20 rounded-lg p-4">
                <SectionTitle icon={Receipt} title="Tarifa / Revisión" />
                {!cotizacionQuote ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground italic">
                      {cotizacion.isCalculating
                        ? "Calculando cotización..."
                        : "Sin cotización calculada"}
                    </p>
                    {!hasAllDependencies && !cotizacion.isCalculating && (
                      <div className="flex flex-col gap-1 text-xs text-muted-foreground">
                        {!hasValidValorBase && (
                          <span>• Ingresa un valor de proyecto válido</span>
                        )}
                        {!hasTarifa && (
                          <span>• Selecciona una revisión/tarifa</span>
                        )}
                        {!hasVariablesFinancieras && (
                          <span>• Variables financieras no disponibles</span>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="text-xs">
                        Revisión #{cotizacionQuote.numero_revision}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        UIT: {formatSoles(cotizacionQuote._metadata.uit_valor)}
                      </span>
                    </div>
                    {cotizacionQuote.revisiones.map((rev) => (
                      <div
                        key={rev.id}
                        className="rounded-lg border border-border bg-muted/30 p-3 space-y-2"
                      >
                        <div className="flex flex-wrap gap-1.5">
                          {rev.especialidades.map((e) => (
                            <Badge
                              key={e.id}
                              variant="secondary"
                              className="text-xs font-medium"
                            >
                              {e.nombre}
                            </Badge>
                          ))}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                          <DataRow label="Monto base">
                            {formatSoles(rev.monto_base)}
                          </DataRow>
                          <DataRow label="Der. Mín.">
                            {formatSoles(rev.tarifa.derecho_minimo)}
                          </DataRow>
                          <DataRow label="Der. Máx.">
                            {rev.tarifa.derecho_maximo !== null
                              ? formatSoles(rev.tarifa.derecho_maximo)
                              : "—"}
                          </DataRow>
                          <DataRow label="% UIT Mín.">
                            {(rev.tarifa.porcentaje_minimo_uit * 100).toFixed(
                              1,
                            )}
                            %
                          </DataRow>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Proyectistas */}
              <div className="bg-muted/20 rounded-lg p-4">
                <SectionTitle
                  icon={Users}
                  title={`Proyectistas (${selectedProyectistas.length})`}
                />
                {selectedProyectistas.length === 0 ? (
                  <p className="text-sm text-muted-foreground italic">
                    Sin proyectistas agregados
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {selectedProyectistas.map((p) => (
                      <div
                        key={p.cip}
                        className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted/30"
                      >
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                          <User className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0 flex-1 space-y-1">
                          <p className="text-sm font-medium truncate">
                            {p.nombres && p.apellidos
                              ? `${p.nombres} ${p.apellidos}`
                              : `CIP ${p.cip}`}
                          </p>
                          <div className="flex flex-wrap gap-1">
                            <Badge variant="outline" className="text-[10px]">
                              CIP {p.cip}
                            </Badge>
                            {p.especialidad_id && (
                              <Badge
                                variant="secondary"
                                className="text-[10px]"
                              >
                                {especialidadLabels[p.especialidad_id] ??
                                  p.especialidad_id}
                              </Badge>
                            )}
                          </div>
                          {p.descripcion && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {p.descripcion}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Contactos */}
              <div className="bg-muted/20 rounded-lg p-4">
                <SectionTitle
                  icon={Phone}
                  title={`Contactos (${selectedContactos.length})`}
                />
                {selectedContactos.length === 0 ? (
                  <p className="text-sm text-muted-foreground italic">
                    Sin contactos agregados
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {selectedContactos.map((c, i) => (
                      <div
                        key={c.localId ?? i}
                        className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted/30"
                      >
                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                          <Phone className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-sm font-medium truncate">
                              {c.nombres} {c.apellidos}
                            </p>
                            {c.principal && (
                              <Badge className="text-[10px] bg-primary/10 text-primary">
                                Principal
                              </Badge>
                            )}
                          </div>
                          <div className="flex flex-col gap-0.5 text-xs text-muted-foreground">
                            {c.cargo && <span>{c.cargo}</span>}
                            {(c.telefono || c.celular) && (
                              <span className="flex items-center gap-1">
                                <Phone className="h-3 w-3" />
                                {[c.telefono, c.celular]
                                  .filter(Boolean)
                                  .join(" / ")}
                              </span>
                            )}
                            {c.email && (
                              <span className="flex items-center gap-1 truncate">
                                <Mail className="h-3 w-3" />
                                {c.email}
                              </span>
                            )}
                            {c.dni && <span>DNI: {c.dni}</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Divider on desktop */}
            <div className="hidden lg:block w-px bg-border shrink-0" />

            {/* Mobile divider */}
            <div className="lg:hidden h-px bg-border shrink-0" />

            {/* Right column: Cotización */}
            <div className="flex-1 min-w-0 bg-muted/20 rounded-lg p-4">
              <SectionTitle icon={Calculator} title="Cotización" />
              {!cotizacionQuote ? (
                <p className="text-sm text-muted-foreground italic">
                  {cotizacion.isCalculating
                    ? "Calculando..."
                    : "Sin cotización calculada"}
                </p>
              ) : (
                <div className="space-y-4 min-w-0">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Subtotal</span>
                      <span className="font-medium">
                        {formatSoles(cotizacionQuote.totales.subtotal)}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">
                        IGV ({cotizacionQuote._metadata.igv_valor * 100}%)
                      </span>
                      <span className="font-medium">
                        {formatSoles(cotizacionQuote.totales.igv)}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-primary bg-primary/5 p-4 space-y-2">
                    <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
                      <BadgeCheck className="h-4 w-4" />
                      Total a Pagar
                    </span>
                    <span className="text-2xl font-bold text-primary">
                      {formatSoles(cotizacionQuote.totales.total_a_pagar)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <FileText className="h-3 w-3 text-primary" />
                    Revisión #{cotizacionQuote.numero_revision} · UIT{" "}
                    {formatSoles(cotizacionQuote._metadata.uit_valor)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
