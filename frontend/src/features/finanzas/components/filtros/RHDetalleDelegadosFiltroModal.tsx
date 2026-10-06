"use client";

/**
 * RHDetalleDelegadosFiltroModal — Modal de filtros para Detalle RH Delegados.
 * Usa AppFormModal como shell.
 *
 * Filtros: delegado_cip (CIP), periodo (año), mes (1-12), municipalidad_id (UUID),
 * tipo_liquidacion_id (UUID, requerido), numero_liquidacion (int, opcional).
 */
import { Building2, Calendar, Filter, Hash, UserRound } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import { useTiposLiquidacion } from "@/features/liquidaciones/hooks/useTiposLiquidacion";

const filtroSchema = z.object({
  delegado_cip: z.string().optional(),
  periodo: z.string().min(1, "Año es requerido"),
  mes: z.string().optional(),
  municipalidad_id: z.string().optional(),
  tipo_liquidacion_id: z.string().min(1, "Tipo de liquidación es requerido"),
  numero_liquidacion: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface RHDetalleDelegadosFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: {
    delegado_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    tipo_liquidacion_id?: string;
    numero_liquidacion?: number;
  };
  onApply: (filtros: {
    delegado_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    tipo_liquidacion_id?: string;
    numero_liquidacion?: number;
  }) => void;
}

export function RHDetalleDelegadosFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RHDetalleDelegadosFiltroModalProps) {
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();
  const { data: tipos = [], isLoading: isLoadingTipos } = useTiposLiquidacion();

  const initialData: FiltroFormData = {
    delegado_cip: initialFiltros?.delegado_cip ?? "",
    periodo: initialFiltros?.periodo ? String(initialFiltros.periodo) : "",
    mes: initialFiltros?.mes ? String(initialFiltros.mes) : "",
    municipalidad_id: initialFiltros?.municipalidad_id ?? "",
    tipo_liquidacion_id: initialFiltros?.tipo_liquidacion_id ?? "",
    numero_liquidacion: initialFiltros?.numero_liquidacion
      ? String(initialFiltros.numero_liquidacion)
      : "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: {
        delegado_cip?: string;
        periodo?: number;
        mes?: number;
        municipalidad_id?: string;
        tipo_liquidacion_id?: string;
        numero_liquidacion?: number;
      } = {};
      if (data.delegado_cip) filtros.delegado_cip = data.delegado_cip;
      if (data.periodo) filtros.periodo = Number(data.periodo);
      if (data.mes) filtros.mes = Number(data.mes);
      if (data.municipalidad_id)
        filtros.municipalidad_id = data.municipalidad_id;
      if (data.tipo_liquidacion_id)
        filtros.tipo_liquidacion_id = data.tipo_liquidacion_id;
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
      title="Filtrar Detalle Delegados"
      description="Filtra por año, mes, municipalidad y tipo de liquidación"
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
      size="lg"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Fila 1: Año + Mes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Periodo (Año) */}
            <div className="space-y-2">
              <Label htmlFor="rh-delegado-detalle-filter-periodo">
                Año <span className="text-destructive">*</span>
              </Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-delegado-detalle-filter-periodo"
                  type="number"
                  placeholder="Ej. 2026"
                  min={2000}
                  max={2100}
                  className="pl-10 w-full"
                  {...methods.register("periodo")}
                />
              </div>
            </div>

            {/* Mes */}
            <div className="space-y-2">
              <Label htmlFor="rh-delegado-detalle-filter-mes">Mes</Label>
              <div className="relative">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-delegado-detalle-filter-mes"
                  type="number"
                  placeholder="1-12"
                  min={1}
                  max={12}
                  className="pl-10 w-full"
                  {...methods.register("mes")}
                />
              </div>
            </div>
          </div>

          {/* Fila 2: CIP + Número de Liquidación */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* CIP */}
            <div className="space-y-2">
              <Label htmlFor="rh-delegado-detalle-filter-cip">
                CIP del Delegado
              </Label>
              <div className="relative">
                <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-delegado-detalle-filter-cip"
                  placeholder="Ej. 118318"
                  className="pl-10 w-full"
                  {...methods.register("delegado_cip")}
                />
              </div>
            </div>

            {/* Número de Liquidación */}
            <div className="space-y-2">
              <Label htmlFor="rh-delegado-detalle-filter-numero-liquidacion">
                N° Liquidación
              </Label>
              <div className="relative">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
                <Input
                  id="rh-delegado-detalle-filter-numero-liquidacion"
                  type="number"
                  placeholder="Opcional"
                  min={1}
                  className="pl-10 w-full"
                  {...methods.register("numero_liquidacion")}
                />
              </div>
            </div>
          </div>

          {/* Fila 3: Municipalidad */}
          <div className="space-y-2">
            <Label htmlFor="rh-delegado-detalle-filter-municipalidad">
              Municipalidad
            </Label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
              <Select
                value={methods.watch("municipalidad_id") || ""}
                onValueChange={(v) => methods.setValue("municipalidad_id", v)}
              >
                <SelectTrigger
                  id="rh-delegado-detalle-filter-municipalidad"
                  className="pl-10 w-full h-10"
                >
                  <SelectValue
                    placeholder={
                      isLoadingMunicipalidades
                        ? "Cargando..."
                        : "Seleccionar municipalidad"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {(municipalidades || []).map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.codigo ? `${m.codigo} - ` : ""}
                      {m.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Fila 4: Tipo de Liquidación */}
          <div className="space-y-2">
            <Label htmlFor="rh-delegado-detalle-filter-tipo-liquidacion">
              Tipo de Liquidación <span className="text-destructive">*</span>
            </Label>
            <Select
              value={methods.watch("tipo_liquidacion_id") || ""}
              onValueChange={(v) => methods.setValue("tipo_liquidacion_id", v)}
            >
              <SelectTrigger
                id="rh-delegado-detalle-filter-tipo-liquidacion"
                className="w-full h-10"
              >
                <SelectValue
                  placeholder={
                    isLoadingTipos
                      ? "Cargando tipos..."
                      : "Seleccionar tipo de liquidación"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {tipos.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.codigo} · {t.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
