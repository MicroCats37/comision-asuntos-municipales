"use client";

import { Building2, MapPin, Search } from "lucide-react";
import { useState } from "react";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { InstitucionFormModal } from "@/features/entidades/components/InstitucionFormModal";
import { PersonaNaturalFormModal } from "@/features/entidades/components/PersonaNaturalFormModal";
import { useDistritos } from "@/features/entidades/hooks/useDistritos";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import { useProyectoBuscar, useProyectoCrear } from "../hooks/useProyecto";
import type {
  ProyectoFormModalProps,
  ProyectoResumen,
} from "../types/liquidacion-edificaciones-form.types";

const proyectoSchema = z.object({
  denominacion: z.string().min(1, "La denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
});

type ProyectoFormData = z.infer<typeof proyectoSchema>;

export function ProyectoFormModal({
  open,
  onOpenChange,
  onSaved,
}: ProyectoFormModalProps) {
  const [publicIdSearch, setPublicIdSearch] = useState("");
  const [entidad, setEntidad] = useState<EntidadResult | undefined>();

  const [showInstitucionModal, setShowInstitucionModal] = useState(false);
  const [showPersonaNaturalModal, setShowPersonaNaturalModal] = useState(false);

  // Cargar distritos para el select
  const { data: distritosData, isLoading: isLoadingDistritos } = useDistritos();

  // Transformar distritos a opciones para el select
  const distritoOptions = distritosData
    ? distritosData.map((d) => ({
        label: `${d.nombre} (${d.provincia.departamento.nombre} - ${d.provincia.nombre})`,
        value: d.id,
      }))
    : [];

  const crearMutation = useProyectoCrear();
  const buscarMutation = useProyectoBuscar();

  const handleSearch = async () => {
    if (!publicIdSearch.trim()) return;

    try {
      const result = await buscarMutation.mutateAsync(publicIdSearch);
      if (result.data) {
        const proyecto: ProyectoResumen = {
          id: result.data.id,
          public_id: result.data.public_id,
          denominacion: result.data.denominacion,
          direccion: result.data.direccion || "",
          distrito: result.data.distrito || undefined,
          entidad: result.data.entidad || undefined,
        };
        onSaved(proyecto);
        onOpenChange(false);
      } else {
        alert("No se encontró un proyecto con ese ID");
      }
    } catch {
      alert("Error al buscar el proyecto");
    }
  };

  const handleSubmit = async (data: ProyectoFormData) => {
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
      onSaved(proyecto);
      onOpenChange(false);
    }
  };

  const handleEntidadSaved = (newEntidad: EntidadResult) => {
    setEntidad(newEntidad);
    setShowInstitucionModal(false);
    setShowPersonaNaturalModal(false);
  };

  return (
    <>
      <AppFormModal<ProyectoFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Proyecto"
        description="Busca o crea un proyecto para la liquidación"
        eyebrow="Edificaciones"
        icon={<Search className="h-5 w-5 text-primary" />}
        primaryLabel="Guardar Proyecto"
        primaryLoadingLabel="Guardando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => {}}
        schema={proyectoSchema}
        initialData={{
          denominacion: "",
          direccion: "",
          distrito_id: undefined,
        }}
        onSubmit={handleSubmit}
        size="lg"
      >
        {({ methods, isSubmitting }) => {
          const {
            register,
            control,
            formState: { errors },
          } = methods;

          return (
            <div className="space-y-6">
              {/* Buscar por Public ID */}
              <div className="space-y-2">
                <Label htmlFor="public_id_search">Buscar por Public ID</Label>
                <div className="flex gap-2">
                  <Input
                    id="public_id_search"
                    placeholder="Ej: PROY-2026-00001"
                    className="h-11 rounded-xl"
                    value={publicIdSearch}
                    onChange={(e) => setPublicIdSearch(e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="default"
                    className="h-11 rounded-xl"
                    onClick={handleSearch}
                    disabled={buscarMutation.isPending}
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Si ya existe un proyecto, busca por su ID público
                </p>
              </div>

              {/* Crear nuevo proyecto */}
              <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <Building2 className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    O crear nuevo proyecto
                  </h3>
                </div>

                <GenericInput
                  field={{
                    name: "denominacion",
                    label: "Denominación",
                    type: "text",
                    required: true,
                    placeholder: "Nombre del proyecto",
                    icon: Building2,
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
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />

                {/* Entidad */}
                <div className="space-y-2">
                  <Label>Entidad</Label>
                  {entidad ? (
                    <div className="space-y-2">
                      <div className="p-3 rounded-lg border border-border bg-muted/30">
                        <p className="font-medium">{entidad.nombre_completo}</p>
                        <p className="text-xs text-muted-foreground">
                          {entidad.tipo_documento}: {entidad.numero_documento}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowInstitucionModal(true)}
                          className="h-8 text-xs"
                        >
                          Cambiar Institución
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowPersonaNaturalModal(true)}
                          className="h-8 text-xs"
                        >
                          Cambiar Persona
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground italic">
                        No hay entidad seleccionada
                      </p>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowInstitucionModal(true)}
                          className="h-8 text-xs"
                        >
                          Crear Institución
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowPersonaNaturalModal(true)}
                          className="h-8 text-xs"
                        >
                          Crear Persona Natural
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }}
      </AppFormModal>

      {/* Child Modal: Entidad */}
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
