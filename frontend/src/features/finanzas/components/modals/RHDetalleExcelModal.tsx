"use client";

/**
 * RHDetalleExcelModal — exportación del detalle RH a Excel en DOS pasos.
 *
 * Reutiliza `RhMensualModalShell` — el MISMO shell con stepper que usan los
 * wizards de RH mensual (Inspector y Delegado) — para que toda la línea UI
 * del módulo RH se vea igual: encabezado, indicador de pasos y footer.
 *
 * Paso 1 — Filtros: el año (periodo) y el mes son obligatorios. Para Delegados
 *          el tipo de liquidación también lo es porque el endpoint lo exige.
 *
 * Paso 2 — Registros: se consulta el conjunto COMPLETO del periodo con
 *          `sin_paginacion=true` (una sola respuesta, sin paginación) y se
 *          ofrece la descarga. El usuario nunca ve páginas: ve el total y la
 *          descarga contiene todas las filas.
 *
 * El modal NO modifica el listado principal: ese sigue paginado como siempre.
 */
import {
  Building2,
  Calendar,
  FileSpreadsheet,
  Filter,
  Hash,
  UserRound,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  SearchableSelect,
  type SearchableSelectOption,
} from "@/components/ui/searchable-select";
import {
  RhMensualModalShell,
  type RhModalStep,
} from "@/features/finanzas/components/modals/RhMensualModalShell";
import {
  formatDelegadoRow,
  formatInspectorRow,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";
import { useRHDetalleDelegados } from "@/features/finanzas/hooks/useRHDetalleDelegados";
import { useRHDetalleInspectores } from "@/features/finanzas/hooks/useRHDetalleInspectores";
import {
  exportRhDetalleDelegadosExcel,
  exportRhDetalleInspectoresExcel,
} from "@/features/finanzas/utils/export-rh-detalle-excel";
import { formatCurrency } from "@/features/liquidaciones/components/liquidacion-ui";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";

const MIN_YEAR = 2010;
const MAX_YEAR = new Date().getFullYear();

const ANIOS: SearchableSelectOption[] = Array.from(
  { length: MAX_YEAR - MIN_YEAR + 1 },
  (_, i) => ({
    value: String(MIN_YEAR + i),
    label: String(MIN_YEAR + i),
  }),
);

const MESES: SearchableSelectOption[] = [
  { value: "1", label: "01 - Enero" },
  { value: "2", label: "02 - Febrero" },
  { value: "3", label: "03 - Marzo" },
  { value: "4", label: "04 - Abril" },
  { value: "5", label: "05 - Mayo" },
  { value: "6", label: "06 - Junio" },
  { value: "7", label: "07 - Julio" },
  { value: "8", label: "08 - Agosto" },
  { value: "9", label: "09 - Setiembre" },
  { value: "10", label: "10 - Octubre" },
  { value: "11", label: "11 - Noviembre" },
  { value: "12", label: "12 - Diciembre" },
];

/** Tipos de liquidación disponibles para el detalle de Delegados. */
export const RH_DETALLE_TIPOS_LIQUIDACION: Array<{
  codigo: string;
  label: string;
}> = [
  { codigo: "EDIFICACION", label: "Edificación" },
  { codigo: "HABILITACION_URBANA", label: "Habilitación Urbana" },
  { codigo: "MECANICA_SUELOS", label: "Mecánica de Suelos" },
  { codigo: "IMPACTO_VIAL", label: "Impacto Vial" },
  { codigo: "TALUDES", label: "Taludes" },
];

/** Stepper del modal — misma línea UI que los wizards de RH mensual. */
const EXCEL_STEPS: RhModalStep[] = [
  {
    icon: Filter,
    label: "Filtrar",
    description: "Selecciona el periodo y los filtros del detalle",
  },
  {
    icon: FileSpreadsheet,
    label: "Descargar",
    description: "Revisa los registros del periodo y descarga el Excel",
  },
];

export type RHDetalleExcelVariante = "delegados" | "inspectores";

interface RHDetalleExcelModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variante: RHDetalleExcelVariante;
}

type Step = 1 | 2;

export function RHDetalleExcelModal({
  open,
  onOpenChange,
  variante,
}: RHDetalleExcelModalProps) {
  const esDelegados = variante === "delegados";

  const [step, setStep] = useState<Step>(1);
  const [periodo, setPeriodo] = useState<string>("");
  const [mes, setMes] = useState<string>("");
  const [tipoCodigo, setTipoCodigo] = useState<string>(
    RH_DETALLE_TIPOS_LIQUIDACION[0].codigo,
  );
  const [cip, setCip] = useState<string>("");
  const [municipalidadId, setMunicipalidadId] = useState<string>("");
  const [numeroLiquidacion, setNumeroLiquidacion] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const { data: municipalidades = [], isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  const periodoNum = periodo ? Number(periodo) : null;
  const mesNum = mes ? Number(mes) : null;
  const hayPeriodo = periodoNum !== null && !Number.isNaN(periodoNum);
  const hayMes = mesNum !== null && !Number.isNaN(mesNum);

  const consultaLista = useRHDetalleDelegados({
    periodo: hayPeriodo ? periodoNum : undefined,
    mes: hayMes ? mesNum : undefined,
    tipoLiquidacionCodigo: esDelegados ? tipoCodigo : undefined,
    delegadoCip: cip.trim() || undefined,
    municipalidadId: municipalidadId || undefined,
    numeroLiquidacion: numeroLiquidacion
      ? Number(numeroLiquidacion)
      : undefined,
    enabled: step === 2 && hayPeriodo && hayMes,
    sinPaginacion: true,
  });

  const consultaInspector = useRHDetalleInspectores({
    periodo: hayPeriodo ? periodoNum : undefined,
    mes: hayMes ? mesNum : undefined,
    inspectorCip: cip.trim() || undefined,
    municipalidadId: municipalidadId || undefined,
    numeroLiquidacion: numeroLiquidacion
      ? Number(numeroLiquidacion)
      : undefined,
    enabled: step === 2 && hayPeriodo && hayMes,
    sinPaginacion: true,
  });

  const items = esDelegados ? consultaLista.items : consultaInspector.items;
  const total = esDelegados ? consultaLista.total : consultaInspector.total;
  const isLoading = esDelegados
    ? consultaLista.isLoading
    : consultaInspector.isLoading;
  const isError = esDelegados
    ? consultaLista.isError
    : consultaInspector.isError;

  /** Muestra de las primeras filas del conjunto completo. */
  const vistaPrevia = useMemo(() => {
    if (esDelegados) {
      return consultaLista.items.slice(0, 8).map((row) => {
        const flat = formatDelegadoRow(row);
        return {
          id: flat.id,
          expediente: flat.expediente ?? "—",
          persona: flat.delegadoNombre ?? "—",
          periodo:
            flat.periodo && flat.mes != null
              ? `${flat.periodo}/${String(flat.mes).padStart(2, "0")}`
              : "—",
          importe: flat.impBruto ?? 0,
          neto: flat.neto ?? 0,
        };
      });
    }
    return consultaInspector.items.slice(0, 8).map((row) => {
      const flat = formatInspectorRow(row);
      return {
        id: flat.id,
        expediente: flat.expediente ?? "—",
        persona: flat.inspectorNombre ?? "—",
        periodo:
          flat.periodo != null && flat.mes != null
            ? `${flat.periodo}/${String(flat.mes).padStart(2, "0")}`
            : "—",
        importe: flat.subTotal ?? 0,
        neto: flat.honorarios ?? 0,
      };
    });
  }, [consultaLista.items, consultaInspector.items, esDelegados]);

  const reset = useCallback(() => {
    setStep(1);
    setPeriodo("");
    setMes("");
    setTipoCodigo(RH_DETALLE_TIPOS_LIQUIDACION[0].codigo);
    setCip("");
    setMunicipalidadId("");
    setNumeroLiquidacion("");
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [onOpenChange, reset]);

  /** Valida los filtros obligatorios y pasa al paso 2. */
  const handleVerRegistros = useCallback(() => {
    if (!hayPeriodo) {
      setError("Selecciona el año del periodo.");
      return;
    }
    if (!hayMes) {
      setError("Selecciona el mes del periodo.");
      return;
    }
    setError(null);
    setStep(2);
  }, [hayMes, hayPeriodo]);

  const handleDescargar = useCallback(() => {
    if (!hayPeriodo || !hayMes || items.length === 0) return;
    const contexto = { periodo: periodoNum as number, mes: mesNum as number };
    if (esDelegados) {
      exportRhDetalleDelegadosExcel(consultaLista.items, contexto);
    } else {
      exportRhDetalleInspectoresExcel(consultaInspector.items, contexto);
    }
  }, [
    consultaInspector.items,
    consultaLista.items,
    esDelegados,
    hayMes,
    hayPeriodo,
    items.length,
    mesNum,
    periodoNum,
  ]);

  const titulo = esDelegados
    ? "Exportar detalle de Delegados"
    : "Exportar detalle de Inspectores";

  const acciones =
    step === 1 ? (
      <Button
        type="button"
        className="h-10 rounded-xl font-semibold"
        onClick={handleVerRegistros}
      >
        Ver registros
      </Button>
    ) : (
      <Button
        type="button"
        className="gap-2 h-10 rounded-xl font-semibold"
        onClick={handleDescargar}
        disabled={isLoading || items.length === 0}
      >
        <FileSpreadsheet className="h-4 w-4" />
        Descargar Excel
      </Button>
    );

  return (
    <RhMensualModalShell
      open={open}
      onClose={handleClose}
      eyebrow="Finanzas — Detalle RH"
      title={titulo}
      description={EXCEL_STEPS[step - 1]?.description}
      steps={EXCEL_STEPS}
      currentStep={step}
      isPending={isLoading}
      error={error}
      backLabel={step === 1 ? "Cancelar" : "Atrás"}
      onBack={step === 1 ? handleClose : () => setStep(1)}
      actions={acciones}
    >
      {step === 1 ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SearchableSelect
              id="rh-detalle-excel-periodo"
              label="Año *"
              value={periodo || null}
              onValueChange={(v) => {
                setPeriodo(v ?? "");
                setError(null);
              }}
              options={ANIOS}
              placeholder="Buscar año..."
              icon={Calendar}
              showLabel
              className="[--input-height:40px] [&_button]:rounded-xl [&_button]:font-semibold"
            />

            <SearchableSelect
              id="rh-detalle-excel-mes"
              label="Mes *"
              value={mes || null}
              onValueChange={(v) => {
                setMes(v ?? "");
                setError(null);
              }}
              options={MESES}
              placeholder="Buscar mes..."
              icon={Hash}
              showLabel
              className="[--input-height:40px] [&_button]:rounded-xl [&_button]:font-semibold"
            />
          </div>

          {esDelegados && (
            <div className="space-y-2">
              <Label>Tipo de liquidación *</Label>
              <div className="flex flex-wrap gap-2">
                {RH_DETALLE_TIPOS_LIQUIDACION.map((t) => (
                  <button
                    key={t.codigo}
                    type="button"
                    onClick={() => setTipoCodigo(t.codigo)}
                    className={
                      tipoCodigo === t.codigo
                        ? "rounded-lg border border-primary/40 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary"
                        : "rounded-lg border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:border-primary/40 hover:text-primary"
                    }
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="rh-detalle-excel-cip">
              {esDelegados ? "CIP del Delegado" : "CIP del Inspector"}
            </Label>
            <div className="relative">
              <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
              <Input
                id="rh-detalle-excel-cip"
                placeholder={esDelegados ? "Ej. 118318" : "Ej. 123456"}
                maxLength={6}
                inputMode="numeric"
                value={cip}
                onChange={(e) => setCip(e.target.value)}
                className="pl-10 w-full"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="rh-detalle-excel-numero">N° Liquidación</Label>
            <Input
              id="rh-detalle-excel-numero"
              type="number"
              placeholder="Opcional"
              min={1}
              value={numeroLiquidacion}
              onChange={(e) => setNumeroLiquidacion(e.target.value)}
            />
          </div>

          <SearchableSelect
            id="rh-detalle-excel-municipalidad"
            label="Municipalidad"
            value={municipalidadId || null}
            onValueChange={(v) => setMunicipalidadId(v ?? "")}
            options={municipalidades.map((m) => ({
              value: m.id,
              label: m.codigo ? `${m.codigo} - ${m.nombre}` : m.nombre,
            }))}
            placeholder={
              isLoadingMunicipalidades
                ? "Cargando municipalidades..."
                : "Buscar municipalidad..."
            }
            icon={Building2}
            disabled={isLoadingMunicipalidades}
            showLabel
            className="[--input-height:40px] [&_button]:rounded-xl [&_button]:font-semibold"
          />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/10 px-3 py-2">
            <span className="text-sm text-muted-foreground">Periodo</span>
            <span className="text-sm font-bold">
              {periodoNum} · {MESES[(mesNum ?? 1) - 1]?.label}
              {esDelegados ? ` · ${tipoCodigo}` : ""}
            </span>
          </div>

          {isLoading && (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <FileSpreadsheet className="h-4 w-4 animate-pulse" />
              Consultando los registros del periodo...
            </div>
          )}

          {isError && (
            <p className="py-6 text-center text-sm text-destructive">
              No se pudieron consultar los registros del periodo.
            </p>
          )}

          {!isLoading && !isError && (
            <>
              <p className="text-sm text-muted-foreground">
                Se encontraron{" "}
                <span className="font-bold text-foreground">{total}</span>{" "}
                registros. El archivo Excel los incluye todos.
              </p>

              {vistaPrevia.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-border/60">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/40">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-muted-foreground">
                          Expediente
                        </th>
                        <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-muted-foreground">
                          {esDelegados ? "Delegado" : "Inspector"}
                        </th>
                        <th className="px-3 py-2 text-center font-semibold uppercase tracking-wide text-muted-foreground">
                          Periodo
                        </th>
                        <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-muted-foreground">
                          Importe
                        </th>
                        <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-muted-foreground">
                          Neto
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {vistaPrevia.map((fila) => (
                        <tr key={fila.id} className="border-t border-border/50">
                          <td className="px-3 py-1.5 font-mono">
                            {fila.expediente}
                          </td>
                          <td className="px-3 py-1.5">{fila.persona}</td>
                          <td className="px-3 py-1.5 text-center font-mono">
                            {fila.periodo}
                          </td>
                          <td className="px-3 py-1.5 text-right">
                            {formatCurrency(fila.importe)}
                          </td>
                          <td className="px-3 py-1.5 text-right font-semibold">
                            {formatCurrency(fila.neto)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {total > vistaPrevia.length && (
                <p className="text-xs text-muted-foreground">
                  Se muestran {vistaPrevia.length} de {total} registros. El
                  Excel contiene la totalidad.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </RhMensualModalShell>
  );
}
