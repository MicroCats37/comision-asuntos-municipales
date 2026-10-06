"use client";

/**
 * DelegadoOperacionSmartField — Smart Field para elegir el periodo vigente del delegado.
 *
 * BAJO DEMANDA:
 * - Cuando el usuario ingresa un CIP válido, consulta automáticamente
 *   GET /delegados/operatividades-vigentes?cip={cip}
 *   y muestra los periodos vigentes como tarjetas seleccionables.
 * - `onSelect` retorna el periodo vigente seleccionado con todos los datos derivados:
 *   id, municipalidad_id, tipo_liquidacion_id, tipo_delegado
 * - El componente maneja el estado de loading/error/empty internamente.
 */
import { Building2, Briefcase, Loader2, MapPin, User } from "lucide-react";
import { useCallback } from "react";
import type { DelegadoOperacionVigente } from "@/features/finanzas/schemas/rh-delegado-mensual.schema";
import { useDelegadoOperatividadesVigentes } from "@/features/finanzas/hooks/useDelegadoOperatividadesVigentes";

export interface DelegadoOperacionSelection {
  /** ID de la DelegadoOperacion seleccionada */
  id: string;
  /** ID de la municipalidad */
  municipalidad_id: string;
  /** Nombre de la municipalidad */
  municipalidad_nombre: string;
  /** ID del tipo de liquidación (null si es wildcard) */
  tipo_liquidacion_id: string | null;
  /** Código del tipo de liquidación */
  tipo_liquidacion_codigo: string | null;
  /** Nombre del tipo de liquidación */
  tipo_liquidacion_nombre: string | null;
  /** ID de la especialidad */
  especialidad_id: string;
  /** Nombre de la especialidad */
  especialidad_nombre: string;
  /** TITULAR or ALTERNO */
  tipo: string;
}

interface DelegadoOperacionSmartFieldProps {
  /** CIP del delegado (ingresado por el usuario) */
  cip: string;
  /** Callback cuando se selecciona un periodo vigente */
  onSelect: (selection: DelegadoOperacionSelection | null) => void;
  /** Periodo vigente actualmente seleccionado (para mostrar feedback) */
  selectedId?: string | null;
  /** Si está deshabilitado */
  disabled?: boolean;
}

function tipoDelegadoLabel(tipo: string): string {
  return tipo === "TITULAR" ? "Principal" : "Alterno";
}

function tipoDelegadoColor(tipo: string): string {
  return tipo === "TITULAR"
    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
    : "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
}

export function DelegadoOperacionSmartField({
  cip,
  onSelect,
  selectedId,
  disabled = false,
}: DelegadoOperacionSmartFieldProps) {
  const {
    data: operatividadesData,
    isLoading,
    isError,
  } = useDelegadoOperatividadesVigentes({
    cip,
    enabled: cip.length === 6,
  });

  const operatividades = operatividadesData?.operatividades ?? [];

  const handleSelect = useCallback(
    (op: DelegadoOperacionVigente) => {
      const selection: DelegadoOperacionSelection = {
        id: op.id,
        municipalidad_id: op.municipalidad_id,
        municipalidad_nombre: op.municipalidad_nombre,
        tipo_liquidacion_id: op.tipo_liquidacion_id ?? null,
        tipo_liquidacion_codigo: op.tipo_liquidacion_codigo ?? null,
        tipo_liquidacion_nombre: op.tipo_liquidacion_nombre ?? null,
        especialidad_id: op.especialidad_id,
        especialidad_nombre: op.especialidad_nombre,
        tipo: op.tipo,
      };
      onSelect(selection);
    },
    [onSelect],
  );

  // Estado: sin CIP
  if (!cip.trim()) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Ingresa el CIP del delegado para cargar sus periodos vigentes.
        </p>
      </div>
    );
  }

  // Estado: CIP parcial (menos de 6 dígitos)
  if (cip.trim().length > 0 && cip.trim().length < 6) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Ingresa los 6 dígitos del CIP del delegado.
        </p>
      </div>
    );
  }

  // Estado: cargando
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-3">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Buscando periodos vigentes para CIP {cip}...
        </span>
      </div>
    );
  }

  // Estado: error
  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
        <p className="text-xs text-destructive">
          No se pudieron cargar los periodos vigentes. Verifica el CIP e intenta
          nuevamente.
        </p>
      </div>
    );
  }

  // Estado: sin resultados
  if (!isLoading && operatividades.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted/20 p-3">
        <p className="text-xs text-muted-foreground">
          No hay periodos vigentes para el CIP{" "}
          <span className="font-semibold">{cip}</span>.
        </p>
      </div>
    );
  }

  // Estado: con resultados — tarjetas seleccionables
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">
          {operatividades.length} periodo(s) vigente(s) encontrado(s) para{" "}
          <span className="font-semibold">{cip}</span>
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2 max-h-72 overflow-y-auto pr-1">
        {operatividades.map((op) => {
          const isSelected = op.id === selectedId;
          return (
            <button
              key={op.id}
              type="button"
              onClick={() => handleSelect(op)}
              disabled={disabled}
              className={[
                "w-full flex items-start gap-3 px-3 py-3 rounded-xl border transition-all text-left",
                isSelected
                  ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30"
                  : "bg-card border-border/70 hover:border-primary/40",
                disabled ? "opacity-50 cursor-not-allowed" : "",
              ].join(" ")}
            >
              {/* Icono */}
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/80 text-muted-foreground">
                <Building2 className="h-4 w-4" />
              </div>

              {/* Info principal */}
              <div className="flex flex-col min-w-0 flex-1 gap-1">
                {/* Municipalidad + Tipo */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-foreground truncate">
                    {op.municipalidad_nombre}
                  </span>
                  <span
                    className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tipoDelegadoColor(op.tipo)}`}
                  >
                    {tipoDelegadoLabel(op.tipo)}
                  </span>
                </div>

                {/* Tipo Liquidación + Especialidad */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Briefcase className="h-3 w-3" />
                    {op.tipo_liquidacion_nombre}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {op.especialidad_nombre}
                  </span>
                </div>

                {/* Periodo de vigencia */}
                {op.periodo_inicio && (
                  <div className="text-[10px] text-muted-foreground/70">
                    Vigente desde{" "}
                    {new Date(op.periodo_inicio).toLocaleDateString("es-PE", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                    {op.periodo_fin &&
                      ` hasta ${new Date(op.periodo_fin).toLocaleDateString("es-PE", { year: "numeric", month: "short", day: "numeric" })}`}
                    {!op.periodo_fin && " — Sin fecha fin"}
                  </div>
                )}
              </div>

              {/* Indicador de selección */}
              <span
                className={[
                  "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                  isSelected ? "border-primary" : "border-border",
                ].join(" ")}
              >
                {isSelected && (
                  <span className="h-2 w-2 rounded-full bg-primary" />
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
