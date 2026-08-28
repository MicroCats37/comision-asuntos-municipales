"use client";

import { CreditCard, MapPin, Search, User } from "lucide-react";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useDocumentoLookup } from "@/features/entidades/hooks/useConsultaExterna";
import { useDistritos } from "@/features/entidades/hooks/useDistritos";
import { usePersonaNaturalUpsert } from "@/features/entidades/hooks/useEntidad";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import type { PersonaNaturalFormModalProps } from "@/features/liquidaciones/types/liquidacion-edificaciones-form.types";

const schema = z.object({
  numero_documento: z
    .string()
    .length(8, "El DNI debe tener exactamente 8 dígitos")
    .regex(/^\d+$/, "El DNI solo debe contener números"),
  nombres: z.string().min(1, "Los nombres son requeridos"),
  apellidos: z.string().min(1, "Los apellidos son requeridos"),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function PersonaNaturalFormModal({
  open,
  onOpenChange,
  onSaved,
}: PersonaNaturalFormModalProps) {
  const mutation = usePersonaNaturalUpsert();
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
      tipo_documento: "DNI" as const,
      numero_documento: data.numero_documento,
      nombres: data.nombres,
      apellidos: data.apellidos,
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
      notify.success("Persona natural guardada correctamente");
      onSaved(entidadResult);
    }
  };

  return (
    <AppFormModal<FormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Nueva Persona Natural"
      description="Registra una persona natural (DNI)"
      eyebrow="Entidad"
      icon={<User className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar Persona"
      primaryLoadingLabel="Guardando..."
      primaryLoading={mutation.isPending}
      onPrimary={() => {}}
      schema={schema}
      initialData={{
        numero_documento: "",
        nombres: "",
        apellidos: "",
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
        const dniValue = watch("numero_documento") || "";

        const handleDocumentoLookup = async () => {
          if (dniValue.length !== 8) {
            return;
          }

          try {
            const result = await documentoLookup.mutateAsync(dniValue);
            if (result) {
              // razon_social = "APELLIDOS, NOMBRES" para DNI
              const parts = result.razon_social.split(", ");
              if (parts.length === 2) {
                setValue("apellidos", parts[0], { shouldValidate: true });
                setValue("nombres", parts[1], { shouldValidate: true });
              }
            }
          } catch {
            // Error is handled by the hook
          }
        };

        return (
          <div className="space-y-4">
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <CreditCard className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Identificación
                </h3>
              </div>
              {/* DNI field with RENIEC lookup button */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <GenericInput
                    field={{
                      name: "numero_documento",
                      label: "DNI",
                      type: "text",
                      required: true,
                      placeholder: "8 dígitos",
                      icon: CreditCard,
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
                      documentoLookup.isPending || dniValue.length !== 8
                    }
                    title="Buscar en RENIEC"
                    aria-label="Buscar en RENIEC"
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <GenericInput
                  field={{
                    name: "nombres",
                    label: "Nombres",
                    type: "text",
                    required: true,
                    placeholder: "Nombres",
                    icon: User,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
                <GenericInput
                  field={{
                    name: "apellidos",
                    label: "Apellidos",
                    type: "text",
                    required: true,
                    placeholder: "Apellidos",
                    icon: User,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
              </div>
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
