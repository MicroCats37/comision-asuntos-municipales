"use client";

import { Building2, MapPin, User } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import { useDistritos } from "@/features/entidades/hooks/useDistritos";
import { useProyectoCrear } from "../hooks/useProyecto";

import type { ProyectoResumen } from "../types/liquidacion-edificaciones-form.types";
import { InstitucionFormModal } from "@/features/entidades/components/InstitucionFormModal";
import { PersonaNaturalFormModal } from "@/features/entidades/components/PersonaNaturalFormModal";

const proyectoSchema = z.object({
  denominacion: z.string().min(1, "La denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
});

type ProyectoFormData = z.infer<typeof proyectoSchema>;

export interface ProyectoFormBodyProps {
  onSuccess?: (proyecto: ProyectoResumen) => void;
  onCancel?: () => void;
}

/**
 * Reusable project form body (without modal wrapper).
 * Used inline in LiquidacionEdificacionFormModal tabs.
 * Uses its own react-hook-form instance.
 */
export function ProyectoFormBody({ onSuccess, onCancel }: ProyectoFormBodyProps) {
  const [entidad, setEntidad] = useState<EntidadResult | undefined>();
  const [showInstitucionModal, setShowInstitucionModal] = useState(false);
  const [showPersonaNaturalModal, setShowPersonaNaturalModal] = useState(false);

  // Load distritos for the select
  const { data: distritosData, isLoading: isLoadingDistritos } = useDistritos();

  // Transform distritos to options
  const distritoOptions = distritosData
    ? distritosData.map((d) => ({
        label: `${d.nombre} (${d.provincia.departamento.nombre} - ${d.provincia.nombre})`,
        value: d.id,
      }))
    : [];

  const crearMutation = useProyectoCrear();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ProyectoFormData>({
    resolver: zodResolver(proyectoSchema),
    defaultValues: {
      denominacion: "",
      direccion: "",
      distrito_id: undefined,
    },
  });

  const onSubmit = async (data: ProyectoFormData) => {
    const result = await crearMutation.mutateAsync({
      denominacion: data.denominacion,
      direccion: data.direccion || undefined,
      distrito_id: data.distrito_id,
      entidad_id: entidad?.id,
    });

    if (result.data) {
      const proyecto: ProyectoResumen = {
        id: result.data.id,
        public_id: result.data.public_id,
        denominacion: result.data.denominacion,
        direccion: result.data.direccion || "",
        distrito: result.data.distrito || undefined,
        entidad: result.data.entidad || undefined,
      };
      onSuccess?.(proyecto);
    }
  };

  const handleEntidadSaved = (newEntidad: EntidadResult) => {
    setEntidad(newEntidad);
    setShowInstitucionModal(false);
    setShowPersonaNaturalModal(false);
  };



  return (
    <>
      <div className="space-y-4">
        <GenericInput
          field={{
            name: "denominacion",
            label: "Denominación",
            type: "text",
            required: true,
            placeholder: "Nombre del proyecto",
            icon: Building2,
            labelClassName: "text-primary font-semibold",
          }}
          register={register as any}
          control={control as any}
          errors={errors}
        />

        <GenericInput
          field={{
            name: "direccion",
            label: "Dirección",
            type: "text",
            placeholder: "Dirección del proyecto",
            icon: MapPin,
            labelClassName: "text-primary font-semibold",
          }}
          register={register as any}
          control={control as any}
          errors={errors}
        />

        <GenericInput
          field={{
            name: "distrito_id",
            label: "Distrito",
            type: "searchable-select",
            placeholder: "Buscar distrito...",
            options: distritoOptions,
            isLoading: isLoadingDistritos,
            icon: MapPin,
            labelClassName: "text-primary font-semibold",
          }}
          register={register as any}
          control={control as any}
          errors={errors}
        />

        {/* Entidad */}
        <div className="space-y-2">
          <span className="text-sm font-medium">Entidad</span>
          {entidad ? (
            <div className="space-y-2">
              <div className="p-3 rounded-lg border border-border bg-muted/30">
                <p className="font-medium">{entidad.nombre_completo}</p>
                <p className="text-xs text-muted-foreground">
                  {entidad.tipo_documento}: {entidad.numero_documento}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowInstitucionModal(true)}
                  className="h-8 rounded-lg gap-1.5"
                >
                  Editar en Modal
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEntidad(undefined)}
                  className="h-8 rounded-lg gap-1.5"
                >
                  Quitar
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground italic">
                No hay entidad seleccionada
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  onClick={() => setShowInstitucionModal(true)}
                  className="h-8 rounded-lg gap-1.5"
                >
                  <Building2 className="h-3.5 w-3.5" />
                  Crear Institución
                </Button>
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  onClick={() => setShowPersonaNaturalModal(true)}
                  className="h-8 rounded-lg gap-1.5"
                >
                  <User className="h-3.5 w-3.5" />
                  Crear Persona Natural
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          {onCancel && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCancel}
              className="rounded-lg"
            >
              Cancelar
            </Button>
          )}
          <Button
            type="button"
            variant="default"
            size="sm"
            disabled={crearMutation.isPending}
            onClick={() => handleSubmit(onSubmit)()}
            className="rounded-lg gap-1.5"
          >
            {crearMutation.isPending ? "Guardando..." : "Guardar Proyecto"}
          </Button>
        </div>
      </div>

      {/* Child Modals for Entidad */}
      <InstitucionFormModal
        open={showInstitucionModal}
        onOpenChange={setShowInstitucionModal}
        onSaved={handleEntidadSaved}
      />

      <PersonaNaturalFormModal
        open={showPersonaNaturalModal}
        onOpenChange={setShowPersonaNaturalModal}
        onSaved={handleEntidadSaved}
      />
    </>
  );
}
