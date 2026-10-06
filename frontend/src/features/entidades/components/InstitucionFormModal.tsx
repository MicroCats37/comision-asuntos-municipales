"use client";

import { Building2, MapPin, Search } from "lucide-react";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useDistritos } from "@/features/entidades/hooks/useDistritos";
import { useInstitucionUpsert } from "@/features/entidades/hooks/useEntidad";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import type { InstitucionFormModalProps } from "@/features/liquidaciones/types/liquidacion-edificaciones-form.types";
import { useDocumentoLookup } from "../hooks/useConsultaExterna";

const schema = z.object({
  numero_documento: z
    .string()
    .length(11, "El RUC debe tener exactamente 11 dígitos")
    .regex(/^\d+$/, "El RUC solo debe contener números"),
  razon_social: z.string().min(1, "La razón social es requerida"),
  nombre_comercial: z.string().optional(),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function InstitucionFormModal({
  open,
  onOpenChange,
  onSaved,
}: InstitucionFormModalProps) {
  const mutation = useInstitucionUpsert();
  const documentoLookup = useDocumentoLookup();
  const { data: distritosData, isLoading: isLoadingDistritos } = useDistritos();

  const distritoOptions = distritosData
    ? distritosData.map((d) => ({
        label: `${d.nombre} (${d.departamento.nombre} - ${d.provincia.nombre})`,
        value: d.id,
      }))
    : [];

  const handleSubmit = async (data: FormData) => {
    const payload = {
      tipo_documento: "RUC" as const,
      numero_documento: data.numero_documento,
      razon_social: data.razon_social,
      nombre_comercial: data.nombre_comercial,
      direccion: data.direccion,
      distrito_id: data.distrito_id,
    };

    const result = await mutation.mutateAsync(payload);

    if (result.data) {
      const entidadResult: EntidadResult = {
        id: result.data.id,
        tipo_documento: result.data.tipo_documento,
        numero_documento: result.data.numero_documento,
        razon_social: result.data.razon_social ?? undefined,
        nombres: result.data.nombres ?? undefined,
        apellidos: result.data.apellidos ?? undefined,
        nombre_completo: result.data.nombre_completo,
        direccion: result.data.direccion ?? undefined,
        distrito_id: result.data.distrito_id ?? undefined,
        activo: result.data.activo,
        creado: result.data.creado,
      };
      notify.success("Institución guardada correctamente");
      onSaved(entidadResult);
    }
  };

  return (
    <AppFormModal<FormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Nueva Institución"
      description="Registra una institución (RUC)"
      eyebrow="Entidad"
      icon={<Building2 className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar Institución"
      primaryLoadingLabel="Guardando..."
      primaryLoading={mutation.isPending}
      onPrimary={() => {}}
      schema={schema}
      initialData={{
        numero_documento: "",
        razon_social: "",
        nombre_comercial: "",
        direccion: "",
        distrito_id: undefined,
      }}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => {
        const {
          register,
          control,
          setValue,
          watch,
          formState: { errors },
        } = methods;
        const rucValue = watch("numero_documento") || "";

        const handleDocumentoLookup = async () => {
          if (rucValue.length !== 11) {
            return;
          }

          try {
            const result = await documentoLookup.mutateAsync(rucValue);
            if (result) {
              setValue("razon_social", result.razon_social, {
                shouldValidate: true,
              });
            }
          } catch {
            // Error is handled by the hook
          }
        };

        return (
          <div className="space-y-4">
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <Building2 className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Identificación
                </h3>
              </div>
              {/* RUC field with SUNAT lookup button */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <GenericInput
                    field={{
                      name: "numero_documento",
                      label: "RUC",
                      type: "text",
                      required: true,
                      placeholder: "11 dígitos",
                      icon: Building2,
                    }}
                    register={register as any}
                    control={control as any}
                    errors={errors}
                  />
                </div>
                <div className="flex flex-col justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-10 w-10 rounded-lg"
                    onClick={handleDocumentoLookup}
                    disabled={
                      documentoLookup.isPending || rucValue.length !== 11
                    }
                    title="Buscar en SUNAT"
                    aria-label="Buscar en SUNAT"
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <GenericInput
                field={{
                  name: "razon_social",
                  label: "Razón Social",
                  type: "text",
                  required: true,
                  placeholder: "Razón social",
                  icon: Building2,
                }}
                register={register as any}
                control={control as any}
                errors={errors}
              />
              <GenericInput
                field={{
                  name: "nombre_comercial",
                  label: "Nombre Comercial",
                  type: "text",
                  placeholder: "Nombre comercial",
                  icon: Building2,
                }}
                register={register as any}
                control={control as any}
                errors={errors}
              />
            </div>
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <MapPin className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Ubicación
                </h3>
              </div>
              <GenericInput
                field={{
                  name: "direccion",
                  label: "Dirección",
                  type: "text",
                  placeholder: "Dirección",
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
            </div>
          </div>
        );
      }}
    </AppFormModal>
  );
}
