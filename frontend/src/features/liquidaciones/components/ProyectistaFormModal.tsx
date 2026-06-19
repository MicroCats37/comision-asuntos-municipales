"use client";

import { User, CreditCard, Award } from "lucide-react";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useProyectistaUpsert } from "../hooks/useProyectista";
import { notify } from "@/errors";
import type { ProyectistaFormModalProps } from "../types/liquidacion-edificaciones-form.types";
import type { ProyectistaResult } from "../types/proyectista";

const proyectistaSchema = z.object({
  nombres: z.string().min(1, "Los nombres son requeridos"),
  apellidos: z.string().min(1, "Los apellidos son requeridos"),
  cip: z.string().optional(),
  dni: z.string().optional(),
  cap: z.string().optional(),
});

type ProyectistaFormData = z.infer<typeof proyectistaSchema>;

export function ProyectistaFormModal({
  open,
  onOpenChange,
  onSaved,
}: ProyectistaFormModalProps) {
  const mutation = useProyectistaUpsert();

  const handleSubmit = async (data: ProyectistaFormData) => {
    const result = await mutation.mutateAsync({
      nombres: data.nombres,
      apellidos: data.apellidos,
      cip: data.cip || undefined,
      dni: data.dni || undefined,
      cap: data.cap || undefined,
    });

    if (result.data) {
      const proyectistaResult: ProyectistaResult = {
        id: result.data.id,
        nombres: result.data.nombres,
        apellidos: result.data.apellidos,
        cip: result.data.cip ?? undefined,
        dni: result.data.dni ?? undefined,
        cap: result.data.cap ?? undefined,
        creado: result.data.creado,
      };
      notify.success("Proyectista guardado correctamente");
      onSaved(proyectistaResult);
    }
  };

  return (
    <AppFormModal<ProyectistaFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Proyectista"
      description="Crea o busca un proyectista para el proyecto"
      eyebrow="Proyecto"
      icon={<User className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar"
      primaryLoadingLabel="Guardando..."
      primaryLoading={mutation.isPending}
      onPrimary={() => {}}
      schema={proyectistaSchema}
      initialData={{
        nombres: "",
        apellidos: "",
        cip: "",
        dni: "",
        cap: "",
      }}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods, isSubmitting }) => {
        const {
          register,
          control,
          formState: { errors },
        } = methods;

        return (
          <div className="space-y-4">
            {/* Datos Personales */}
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <User className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Datos Personales
                </h3>
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

            {/* Números de Identificación */}
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <Award className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Números de Identificación
                </h3>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <GenericInput
                  field={{
                    name: "cip",
                    label: "CIP",
                    type: "text",
                    placeholder: "CIP",
                    icon: Award,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
                <GenericInput
                  field={{
                    name: "dni",
                    label: "DNI",
                    type: "text",
                    placeholder: "DNI",
                    icon: CreditCard,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
                <GenericInput
                  field={{
                    name: "cap",
                    label: "CAP",
                    type: "text",
                    placeholder: "CAP",
                    icon: Award,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
              </div>
            </div>
          </div>
        );
      }}
    </AppFormModal>
  );
}
