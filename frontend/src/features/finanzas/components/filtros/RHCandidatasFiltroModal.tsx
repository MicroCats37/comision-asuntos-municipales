"use client";

/**
 * RHCandidatasFiltroModal — Reusable filter modal for RH Candidatas (Inspector & Delegado).
 * Uses AppFormModal as shell.
 *
 * Fields: expediente (text), numero (text), propietario (text), direccion (text),
 * documento (text), comprobante_serie (text), comprobante_numero (text).
 *
 * "Comprobante" = comprobante VIGENTE (activo=True) de la liquidación; el
 * backend lo resuelve con `Exists` para no duplicar filas por historial.
 *
 * On apply: passes filter values to onApply callback; parent resets page to 1 and refetches.
 */
import { Filter } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppFormModal } from "@/components-app/forms/AppFormModal";

const filtroSchema = z.object({
  expediente: z.string().optional(),
  numero: z.string().optional(),
  propietario: z.string().optional(),
  direccion: z.string().optional(),
  documento: z.string().optional(),
  comprobante_serie: z.string().optional(),
  comprobante_numero: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

export interface RHCandidatasFiltroValues {
  expediente?: string;
  numero?: string;
  propietario?: string;
  direccion?: string;
  /** N.º de documento de la entidad (snapshot del proyecto). */
  documento?: string;
  /** Serie del comprobante VIGENTE de la liquidación. */
  comprobante_serie?: string;
  /** Número del comprobante VIGENTE de la liquidación. */
  comprobante_numero?: string;
}

interface RHCandidatasFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: RHCandidatasFiltroValues;
  onApply: (filtros: RHCandidatasFiltroValues) => void;
}

export function RHCandidatasFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RHCandidatasFiltroModalProps) {
  const initialData: FiltroFormData = {
    expediente: initialFiltros?.expediente ?? "",
    numero: initialFiltros?.numero ?? "",
    propietario: initialFiltros?.propietario ?? "",
    direccion: initialFiltros?.direccion ?? "",
    documento: initialFiltros?.documento ?? "",
    comprobante_serie: initialFiltros?.comprobante_serie ?? "",
    comprobante_numero: initialFiltros?.comprobante_numero ?? "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: RHCandidatasFiltroValues = {};
      if (data.expediente?.trim()) filtros.expediente = data.expediente.trim();
      if (data.numero?.toString().trim())
        filtros.numero = data.numero.toString().trim();
      if (data.propietario?.trim())
        filtros.propietario = data.propietario.trim();
      if (data.direccion?.trim()) filtros.direccion = data.direccion.trim();
      if (data.documento?.trim()) filtros.documento = data.documento.trim();
      if (data.comprobante_serie?.trim())
        filtros.comprobante_serie = data.comprobante_serie.trim();
      if (data.comprobante_numero?.trim())
        filtros.comprobante_numero = data.comprobante_numero.trim();
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Candidatas"
      description="Filtra por expediente, número, propietario, dirección, documento o comprobante"
      eyebrow="Finanzas"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar Filtros"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      secondaryLabel="Cancelar"
      onSecondary={() => onOpenChange(false)}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Expediente */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-expediente">Expediente</Label>
            <Input
              id="rh-candidatas-filter-expediente"
              placeholder="Ej. EXP-2026-001"
              className="w-full"
              {...methods.register("expediente")}
            />
          </div>

          {/* Número */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-numero">Número</Label>
            <Input
              id="rh-candidatas-filter-numero"
              type="text"
              inputMode="numeric"
              placeholder="Número de revisión"
              className="w-40"
              {...methods.register("numero")}
            />
          </div>

          {/* Propietario */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-propietario">
              Propietario
            </Label>
            <Input
              id="rh-candidatas-filter-propietario"
              placeholder="Nombre del propietario"
              className="w-full"
              {...methods.register("propietario")}
            />
          </div>

          {/* Dirección */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-direccion">Dirección</Label>
            <Input
              id="rh-candidatas-filter-direccion"
              placeholder="Dirección de la habilitación"
              className="w-full"
              {...methods.register("direccion")}
            />
          </div>

          {/* N° Documento Entidad */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-documento">
              N° Documento Entidad
            </Label>
            <Input
              id="rh-candidatas-filter-documento"
              placeholder="RUC / DNI de la entidad"
              className="w-full"
              {...methods.register("documento")}
            />
          </div>

          {/* Comprobante vigente — serie */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-comprobante-serie">
              Comprobante — Serie
            </Label>
            <Input
              id="rh-candidatas-filter-comprobante-serie"
              placeholder="Serie del comprobante vigente"
              className="w-full"
              {...methods.register("comprobante_serie")}
            />
          </div>

          {/* Comprobante vigente — número */}
          <div className="space-y-2">
            <Label htmlFor="rh-candidatas-filter-comprobante-numero">
              Comprobante — Número
            </Label>
            <Input
              id="rh-candidatas-filter-comprobante-numero"
              placeholder="Número del comprobante vigente"
              className="w-full"
              {...methods.register("comprobante_numero")}
            />
          </div>
        </div>
      )}
    </AppFormModal>
  );
}

/** Count how many filter values are active */
export function countActiveFiltros(filtros: RHCandidatasFiltroValues): number {
  return [
    filtros.expediente,
    filtros.numero,
    filtros.propietario,
    filtros.direccion,
    filtros.documento,
    filtros.comprobante_serie,
    filtros.comprobante_numero,
  ].filter(Boolean).length;
}
