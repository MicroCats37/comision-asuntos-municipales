"use client";

import { Phone, User, Mail, MapPin, Briefcase } from "lucide-react";
import { z } from "zod";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import type { ContactoFormModalProps } from "../types/liquidacion-edificaciones-form.types";
import type { ContactoInline } from "../types/contacto";
import { contactoInlineSchema } from "../schemas/liquidacion-edificaciones-form.schema";

type ContactoFormData = z.infer<typeof contactoInlineSchema>;

const defaultInitialData = {
  nombres: "",
  apellidos: "",
  dni: "",
  telefono: "",
  celular: "",
  email: "",
  cargo: "",
  direccion: "",
  descripcion: "",
  principal: false,
};

export function ContactoFormModal({
  open,
  onOpenChange,
  onSaved,
  initialData,
}: ContactoFormModalProps) {
  const isEditing = !!initialData;
  const modalTitle = isEditing ? "Editar Contacto" : "Agregar Contacto";
  const modalDescription = isEditing
    ? "Modifica los datos del contacto de referencia"
    : "Ingresa los datos del contacto de referencia";
  const primaryLabel = isEditing ? "Guardar" : "Agregar";
  const primaryLoadingLabel = isEditing ? "Guardando..." : "Agregando...";

  // Build initial form data — merge defaults with provided initialData
  const formInitialData = initialData
    ? {
        nombres: initialData.nombres ?? "",
        apellidos: initialData.apellidos ?? "",
        dni: initialData.dni ?? "",
        telefono: initialData.telefono ?? "",
        celular: initialData.celular ?? "",
        email: initialData.email ?? "",
        cargo: initialData.cargo ?? "",
        direccion: initialData.direccion ?? "",
        descripcion: initialData.descripcion ?? "",
        principal: initialData.principal ?? false,
      }
    : defaultInitialData;

  const handleSubmit = async (data: ContactoFormData) => {
    const contactoInline: ContactoInline = {
      ...(initialData?.localId ? { localId: initialData.localId } : {}),
      nombres: data.nombres,
      apellidos: data.apellidos,
      dni: data.dni || undefined,
      telefono: data.telefono || undefined,
      celular: data.celular || undefined,
      email: data.email || undefined,
      cargo: data.cargo || undefined,
      direccion: data.direccion || undefined,
      descripcion: data.descripcion || undefined,
      principal: data.principal || false,
    };

    onSaved(contactoInline);
  };

  return (
    <AppFormModal<ContactoFormData>
      open={open}
      onOpenChange={onOpenChange}
      title={modalTitle}
      description={modalDescription}
      eyebrow="Liquidación"
      icon={<Phone className="h-5 w-5 text-primary" />}
      primaryLabel={primaryLabel}
      primaryLoadingLabel={primaryLoadingLabel}
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={contactoInlineSchema}
      initialData={formInitialData}
      onSubmit={handleSubmit}
      onFieldChange={() => {}}
      size="md"
    >
      {({ methods }) => (
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
              <div>
                <label className="text-sm font-medium text-primary">
                  Nombres <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  {...methods.register("nombres")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="Nombres"
                />
                {methods.formState.errors.nombres && (
                  <p className="text-xs text-destructive mt-1">
                    {methods.formState.errors.nombres.message as string}
                  </p>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-primary">
                  Apellidos <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  {...methods.register("apellidos")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="Apellidos"
                />
                {methods.formState.errors.apellidos && (
                  <p className="text-xs text-destructive mt-1">
                    {methods.formState.errors.apellidos.message as string}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-primary">DNI</label>
                <input
                  type="text"
                  {...methods.register("dni")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="DNI"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-primary">Cargo</label>
                <input
                  type="text"
                  {...methods.register("cargo")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="Cargo u ocupación"
                />
              </div>
            </div>
          </div>

          {/* Información de Contacto */}
          <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
            <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
              <Phone className="h-4 w-4" />
              <h3 className="text-sm font-semibold uppercase tracking-wide">
                Información de Contacto
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-primary">Teléfono</label>
                <input
                  type="text"
                  {...methods.register("telefono")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="Teléfono fijo"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-primary">Celular</label>
                <input
                  type="text"
                  {...methods.register("celular")}
                  className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                  placeholder="Celular"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-primary">Email</label>
              <input
                type="email"
                {...methods.register("email")}
                className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                placeholder="email@ejemplo.com"
              />
              {methods.formState.errors.email && (
                <p className="text-xs text-destructive mt-1">
                  {methods.formState.errors.email.message as string}
                </p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-primary">Dirección</label>
              <input
                type="text"
                {...methods.register("direccion")}
                className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5"
                placeholder="Dirección del contacto"
              />
            </div>
          </div>

          {/* Opciones Adicionales */}
          <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
            <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
              <Briefcase className="h-4 w-4" />
              <h3 className="text-sm font-semibold uppercase tracking-wide">
                Opciones Adicionales
              </h3>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="principal"
                {...methods.register("principal")}
                className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
              />
              <label htmlFor="principal" className="text-sm font-medium cursor-pointer">
                Contacto principal
              </label>
            </div>

            <div>
              <label className="text-sm font-medium text-primary">Descripción / Nota</label>
              <textarea
                {...methods.register("descripcion")}
                className="flex w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1.5 resize-none"
                placeholder="Descripción o nota adicional..."
                rows={3}
              />
            </div>
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
