"use client";

/**
 * RecibosDelegadosFiltroModal — Modal de filtros para Recibos Delegados.
 * Usa AppFormModal como shell.
 *
 * Filtros: delegado_cip (string), municipalidad_id (UUID), periodo (int), mes (int)
 * Al aplicar: onApply(filtros) → la vista muestra los filtros activos arriba.
 */
import { Filter } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppFormModal } from "@/components-app/forms/AppFormModal";

const filtroSchema = z.object({
  delegado_cip: z.string().optional(),
  municipalidad_id: z.string().optional(),
  periodo: z.string().optional(),
  mes: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface RecibosDelegadosFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: {
    delegado_cip?: string;
    municipalidad_id?: string;
    periodo?: string;
    mes?: string;
  };
  onApply: (filtros: {
    delegado_cip?: string;
    municipalidad_id?: string;
    periodo?: string;
    mes?: string;
  }) => void;
}

export function RecibosDelegadosFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RecibosDelegadosFiltroModalProps) {
  const initialData: FiltroFormData = {
    delegado_cip: initialFiltros?.delegado_cip ?? "",
    municipalidad_id: initialFiltros?.municipalidad_id ?? "",
    periodo: initialFiltros?.periodo ?? "",
    mes: initialFiltros?.mes ?? "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: {
        delegado_cip?: string;
        municipalidad_id?: string;
        periodo?: string;
        mes?: string;
      } = {};
      if (data.delegado_cip) filtros.delegado_cip = data.delegado_cip;
      if (data.municipalidad_id)
        filtros.municipalidad_id = data.municipalidad_id;
      if (data.periodo) filtros.periodo = data.periodo;
      if (data.mes) filtros.mes = data.mes;
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Recibos Delegados"
      description="Filtra por CIP del delegado, municipalidad, periodo y mes"
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
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* CIP del Delegado */}
          <div className="space-y-2">
            <Label htmlFor="recibos-delegado-filter-cip">
              CIP del Delegado
            </Label>
            <Input
              id="recibos-delegado-filter-cip"
              placeholder="Ej. 118318"
              className="w-full"
              {...methods.register("delegado_cip")}
            />
          </div>

          {/* Municipalidad ID */}
          <div className="space-y-2">
            <Label htmlFor="recibos-delegado-filter-municipalidad">
              Municipalidad ID
            </Label>
            <Input
              id="recibos-delegado-filter-municipalidad"
              placeholder="UUID de la municipalidad"
              className="w-full"
              {...methods.register("municipalidad_id")}
            />
          </div>

          {/* Periodo (Año) */}
          <div className="space-y-2">
            <Label htmlFor="recibos-delegado-filter-periodo">
              Periodo (Año)
            </Label>
            <Input
              id="recibos-delegado-filter-periodo"
              placeholder="Ej. 2026"
              type="number"
              min="2000"
              max="2100"
              className="w-full"
              {...methods.register("periodo")}
            />
          </div>

          {/* Mes */}
          <div className="space-y-2">
            <Label htmlFor="recibos-delegado-filter-mes">Mes (1-12)</Label>
            <Input
              id="recibos-delegado-filter-mes"
              placeholder="Ej. 6"
              type="number"
              min="1"
              max="12"
              className="w-full"
              {...methods.register("mes")}
            />
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
