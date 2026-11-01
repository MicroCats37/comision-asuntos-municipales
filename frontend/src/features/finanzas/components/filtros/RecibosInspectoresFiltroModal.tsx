"use client";

/**
 * RecibosInspectoresFiltroModal — Modal de filtros para Recibos Inspectores.
 * Usa AppFormModal como shell.
 *
 * Filtros: inspector_cip (CIP), año, mes.
 * Mismo conjunto y mismo patrón que RecibosDelegadosFiltroModal, para que
 * ambos listados de RH mensual se comporten igual.
 */
import { Calendar, Filter, Hash, UserRound } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  SearchableSelect,
  type SearchableSelectOption,
} from "@/components/ui/searchable-select";
import { AppFormModal } from "@/components-app/forms/AppFormModal";

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

/**
 * Schema refinado (Zod):
 * - Todos los campos son opcionales.
 * - inspector_cip: 1-6 dígitos numéricos.
 * - periodo: entero entre 2010 y año actual.
 * - mes: entero entre 1 y 12.
 */
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
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface RecibosInspectoresFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: {
    inspector_cip?: string;
    periodo?: string | number;
    mes?: string | number;
  };
  onApply: (filtros: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
  }) => void;
}

export function RecibosInspectoresFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RecibosInspectoresFiltroModalProps) {
  const initialData: FiltroFormData = {
    inspector_cip: initialFiltros?.inspector_cip ?? "",
    periodo: initialFiltros?.periodo ? String(initialFiltros.periodo) : "",
    mes: initialFiltros?.mes ? String(initialFiltros.mes) : "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: {
        inspector_cip?: string;
        periodo?: number;
        mes?: number;
      } = {};
      if (data.inspector_cip) filtros.inspector_cip = data.inspector_cip.trim();
      if (data.periodo) filtros.periodo = Number(data.periodo);
      if (data.mes) filtros.mes = Number(data.mes);
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Recibos Inspectores"
      description="Filtra por CIP, año y mes"
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
          {/* Fila 1: Año + Mes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SearchableSelect
              id="recibos-inspector-filter-periodo"
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
              id="recibos-inspector-filter-mes"
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

          {/* Fila 2: CIP del Inspector */}
          <div className="space-y-2">
            <Label htmlFor="recibos-inspector-filter-inspector">
              CIP del Inspector
            </Label>
            <div className="relative">
              <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
              <Input
                id="recibos-inspector-filter-inspector"
                placeholder="Ej. 123456"
                inputMode="numeric"
                maxLength={6}
                className="pl-10 w-full"
                {...methods.register("inspector_cip")}
              />
            </div>
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
