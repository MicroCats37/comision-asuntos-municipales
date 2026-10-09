"use client";

/**
 * RHDetalleInspectoresFiltroModal — Modal de filtros para Detalle RH Inspectores.
 * Usa AppFormModal como shell.
 *
 * Patrón limpio alineado con RHDetalleDelegadosFiltroModal:
 *   - SearchableSelect para año / mes / municipalidad.
 *   - Input con icono (UserRound / Hash) para cip y n° liquidación.
 *
 * Filtros opcionales: inspector_cip (CIP), periodo (año), mes (1-12), municipalidad_id,
 * numero_liquidacion (int).
 */
import { Building2, Calendar, Filter, Hash, UserRound } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  SearchableSelect,
  type SearchableSelectOption,
} from "@/components/ui/searchable-select";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";

const MIN_YEAR = 2010;
const MAX_YEAR = new Date().getFullYear();

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

const ANIOS: SearchableSelectOption[] = Array.from(
  { length: MAX_YEAR - MIN_YEAR + 1 },
  (_, i) => ({
    value: String(MIN_YEAR + i),
    label: String(MIN_YEAR + i),
  }),
);

const filtroSchema = z.object({
  inspector_cip: z
    .string()
    .trim()
    .optional()
    .refine(
      (v) => !v || /^\d{1,6}$/.test(v),
      "CIP debe tener entre 1 y 6 dígitos",
    ),
  periodo: z
    .string()
    .optional()
    .refine((v) => {
      if (!v) return true;
      const n = Number(v);
      return Number.isInteger(n) && n >= MIN_YEAR && n <= MAX_YEAR;
    }, `Año debe estar entre ${MIN_YEAR} y ${MAX_YEAR}`),
  mes: z
    .string()
    .optional()
    .refine((v) => {
      if (!v) return true;
      const n = Number(v);
      return Number.isInteger(n) && n >= 1 && n <= 12;
    }, "Mes debe estar entre 1 y 12"),
  municipalidad_id: z.string().optional(),
  numero_liquidacion: z
    .string()
    .optional()
    .refine((v) => {
      if (!v) return true;
      const n = Number(v);
      return Number.isInteger(n) && n >= 1;
    }, "N° Liquidación debe ser entero positivo"),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface RHDetalleInspectoresFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    numero_liquidacion?: number;
  };
  onApply: (filtros: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    numero_liquidacion?: number;
  }) => void;
}

export function RHDetalleInspectoresFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RHDetalleInspectoresFiltroModalProps) {
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  const initialData: FiltroFormData = {
    inspector_cip: initialFiltros?.inspector_cip ?? "",
    periodo: initialFiltros?.periodo ? String(initialFiltros.periodo) : "",
    mes: initialFiltros?.mes ? String(initialFiltros.mes) : "",
    municipalidad_id: initialFiltros?.municipalidad_id ?? "",
    numero_liquidacion: initialFiltros?.numero_liquidacion
      ? String(initialFiltros.numero_liquidacion)
      : "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: {
        inspector_cip?: string;
        periodo?: number;
        mes?: number;
        municipalidad_id?: string;
        numero_liquidacion?: number;
      } = {};
      if (data.inspector_cip) filtros.inspector_cip = data.inspector_cip.trim();
      if (data.periodo) filtros.periodo = Number(data.periodo);
      if (data.mes) filtros.mes = Number(data.mes);
      if (data.municipalidad_id)
        filtros.municipalidad_id = data.municipalidad_id;
      if (data.numero_liquidacion)
        filtros.numero_liquidacion = Number(data.numero_liquidacion);
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Detalle Inspectores"
      description="Filtra por CIP, año, mes, municipalidad y número de liquidación"
      eyebrow="Finanzas"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar Filtros"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      showErrorsAsToasts
      disableBuildUpdatePayload
      preventClose={false}
      size="lg"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Fila 1: Año + Mes (ambos opcionales) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SearchableSelect
              id="rh-inspector-detalle-filter-periodo"
              label="Año"
              value={methods.watch("periodo") || null}
              onValueChange={(v) => methods.setValue("periodo", v ?? "")}
              options={ANIOS}
              placeholder="Buscar año..."
              icon={Calendar}
              showLabel
              className="[--input-height:40px] [&_button]:rounded-xl [&_button]:font-semibold"
            />

            <SearchableSelect
              id="rh-inspector-detalle-filter-mes"
              label="Mes"
              value={methods.watch("mes") || null}
              onValueChange={(v) => methods.setValue("mes", v ?? "")}
              options={MESES}
              placeholder="Buscar mes..."
              icon={Hash}
              showLabel
              className="[--input-height:40px] [&_button]:rounded-xl [&_button]:font-semibold"
            />
          </div>

          {/* Fila 2: CIP + Número de Liquidación */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="rh-inspector-detalle-filter-cip">
                CIP del Inspector
              </Label>
              <div className="relative">
                <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-inspector-detalle-filter-cip"
                  placeholder="Ej. 118318"
                  maxLength={6}
                  inputMode="numeric"
                  className="pl-10 w-full"
                  {...methods.register("inspector_cip")}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rh-inspector-detalle-filter-numero-liquidacion">
                N° Liquidación
              </Label>
              <div className="relative">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-inspector-detalle-filter-numero-liquidacion"
                  type="number"
                  placeholder="Opcional"
                  min={1}
                  className="pl-10 w-full"
                  {...methods.register("numero_liquidacion")}
                />
              </div>
            </div>
          </div>

          {/* Fila 3: Municipalidad (SearchableSelect) */}
          <SearchableSelect
            id="rh-inspector-detalle-filter-municipalidad"
            label="Municipalidad"
            value={methods.watch("municipalidad_id") || null}
            onValueChange={(v) => methods.setValue("municipalidad_id", v ?? "")}
            options={(municipalidades || []).map((m) => ({
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
      )}
    </AppFormModal>
  );
}
