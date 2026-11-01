"use client";

/**
 * RHMensualExcelModal — exportación del listado de RH MENSUAL a Excel en DOS
 * pasos.
 *
 * Reutiliza `RhMensualModalShell` — el MISMO shell con stepper que usan los
 * wizards de RH mensual — para que la línea UI del módulo RH sea una sola.
 *
 * Paso 1 — Filtros: el año (periodo) y el mes son obligatorios; el CIP y la
 *          municipalidad son opcionales.
 * Paso 2 — Registros: se consulta el conjunto COMPLETO del periodo con
 *          `sin_paginacion=true` y se ofrece la descarga (una fila por recibo).
 *
 * El listado principal NO cambia: sigue paginado y con filtros opcionales.
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
import { useRecibosDelegados } from "@/features/finanzas/hooks/useRecibosDelegados";
import { useRecibosInspectores } from "@/features/finanzas/hooks/useRecibosInspectores";
import {
  buildRhMensualDelegadosRows,
  buildRhMensualInspectoresRows,
  exportRhMensualDelegadosExcel,
  exportRhMensualInspectoresExcel,
} from "@/features/finanzas/utils/export-rh-mensual-excel";
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

const EXCEL_STEPS: RhModalStep[] = [
  {
    icon: Filter,
    label: "Filtrar",
    description: "Selecciona el periodo y los filtros del listado",
  },
  {
    icon: FileSpreadsheet,
    label: "Descargar",
    description: "Revisa los recibos del periodo y descarga el Excel",
  },
];

export type RHMensualExcelVariante = "delegados" | "inspectores";

interface RHMensualExcelModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variante: RHMensualExcelVariante;
}

type Step = 1 | 2;

export function RHMensualExcelModal({
  open,
  onOpenChange,
  variante,
}: RHMensualExcelModalProps) {
  const esDelegados = variante === "delegados";

  const [step, setStep] = useState<Step>(1);
  const [periodo, setPeriodo] = useState<string>("");
  const [mes, setMes] = useState<string>("");
  const [cip, setCip] = useState<string>("");
  const [municipalidadId, setMunicipalidadId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const { data: municipalidades = [], isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  const periodoNum = periodo ? Number(periodo) : null;
  const mesNum = mes ? Number(mes) : null;
  const hayPeriodo = periodoNum !== null && !Number.isNaN(periodoNum);
  const hayMes = mesNum !== null && !Number.isNaN(mesNum);

  const consultaDelegados = useRecibosDelegados({
    periodo: hayPeriodo ? periodoNum : undefined,
    mes: hayMes ? mesNum : undefined,
    delegadoCip: cip.trim() || undefined,
    municipalidadId: municipalidadId || undefined,
    enabled: step === 2 && hayPeriodo && hayMes,
    sinPaginacion: true,
  });

  const consultaInspectores = useRecibosInspectores({
    periodo: hayPeriodo ? periodoNum : undefined,
    mes: hayMes ? mesNum : undefined,
    inspectorCip: cip.trim() || undefined,
    enabled: step === 2 && hayPeriodo && hayMes,
    sinPaginacion: true,
  });

  const total = esDelegados
    ? consultaDelegados.total
    : consultaInspectores.total;
  const isLoading = esDelegados
    ? consultaDelegados.isLoading
    : consultaInspectores.isLoading;
  const isError = esDelegados
    ? consultaDelegados.isError
    : consultaInspectores.isError;

  /**
   * Vista previa de las LIQUIDACIONES del conjunto completo (una fila por
   * liquidación, igual que el Excel). Se reutiliza el mismo aplanado del
   * helper para que la vista previa y el archivo nunca diverjan.
   */
  const filasDetalle = useMemo(
    () =>
      esDelegados
        ? buildRhMensualDelegadosRows(consultaDelegados.items)
        : buildRhMensualInspectoresRows(consultaInspectores.items),
    [consultaDelegados.items, consultaInspectores.items, esDelegados],
  );

  const vistaPrevia = useMemo(
    () =>
      filasDetalle.slice(0, 8).map((fila) => ({
        id: `${fila["N° RH"]}-${fila.Expediente}-${fila.Item}`,
        persona: String(fila.Delegado ?? fila.Inspector ?? "—"),
        expediente: String(fila.Expediente ?? "—"),
        periodo: `${fila.Periodo ?? ""}/${String(fila.Mes ?? "").padStart(2, "0")}`,
        importe: Number(fila["Total liquidacion"] ?? fila["Sub Total"] ?? 0),
        neto: Number(fila["Neto honorario"] ?? fila.Honorarios ?? 0),
      })),
    [filasDetalle],
  );

  const reset = useCallback(() => {
    setStep(1);
    setPeriodo("");
    setMes("");
    setCip("");
    setMunicipalidadId("");
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [onOpenChange, reset]);

  const handleVerRecibos = useCallback(() => {
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
    if (!hayPeriodo || !hayMes || filasDetalle.length === 0) return;
    const contexto = { periodo: periodoNum as number, mes: mesNum as number };
    if (esDelegados) {
      exportRhMensualDelegadosExcel(consultaDelegados.items, contexto);
    } else {
      exportRhMensualInspectoresExcel(consultaInspectores.items, contexto);
    }
  }, [
    consultaDelegados.items,
    consultaInspectores.items,
    esDelegados,
    filasDetalle.length,
    hayMes,
    hayPeriodo,
    mesNum,
    periodoNum,
  ]);

  const titulo = esDelegados
    ? "Exportar RH Mensual - Delegados"
    : "Exportar RH Mensual - Inspectores";

  const acciones =
    step === 1 ? (
      <Button
        type="button"
        className="h-10 rounded-xl font-semibold"
        onClick={handleVerRecibos}
      >
        Ver recibos
      </Button>
    ) : (
      <Button
        type="button"
        className="gap-2 h-10 rounded-xl font-semibold"
        onClick={handleDescargar}
        disabled={isLoading || filasDetalle.length === 0}
      >
        <FileSpreadsheet className="h-4 w-4" />
        Descargar Excel
      </Button>
    );

  return (
    <RhMensualModalShell
      open={open}
      onClose={handleClose}
      eyebrow="Finanzas — RH Mensual"
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
              id="rh-mensual-excel-periodo"
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
              id="rh-mensual-excel-mes"
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

          <div className="space-y-2">
            <Label htmlFor="rh-mensual-excel-cip">
              {esDelegados ? "CIP del Delegado" : "CIP del Inspector"}
            </Label>
            <div className="relative">
              <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
              <Input
                id="rh-mensual-excel-cip"
                placeholder={esDelegados ? "Ej. 118318" : "Ej. 123456"}
                maxLength={6}
                inputMode="numeric"
                value={cip}
                onChange={(e) => setCip(e.target.value)}
                className="pl-10 w-full"
              />
            </div>
          </div>

          {esDelegados && (
            <SearchableSelect
              id="rh-mensual-excel-municipalidad"
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
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/10 px-3 py-2">
            <span className="text-sm text-muted-foreground">Periodo</span>
            <span className="text-sm font-bold">
              {periodoNum} · {MESES[(mesNum ?? 1) - 1]?.label}
            </span>
          </div>

          {isLoading && (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <FileSpreadsheet className="h-4 w-4 animate-pulse" />
              Consultando los recibos del periodo...
            </div>
          )}

          {isError && (
            <p className="py-6 text-center text-sm text-destructive">
              No se pudieron consultar los recibos del periodo.
            </p>
          )}

          {!isLoading && !isError && (
            <>
              <p className="text-sm text-muted-foreground">
                Se encontraron{" "}
                <span className="font-bold text-foreground">{total}</span>{" "}
                {esDelegados ? "recibos" : "recibos"} con{" "}
                <span className="font-bold text-foreground">
                  {filasDetalle.length}
                </span>{" "}
                liquidaciones. El archivo Excel las incluye todas.
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

              {filasDetalle.length > vistaPrevia.length && (
                <p className="text-xs text-muted-foreground">
                  Se muestran {vistaPrevia.length} de {filasDetalle.length}{" "}
                  liquidaciones. El Excel contiene la totalidad.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </RhMensualModalShell>
  );
}
