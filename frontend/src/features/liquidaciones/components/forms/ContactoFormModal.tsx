"use client";

import { Briefcase, Mail, Phone, User } from "lucide-react";
/**
 * ContactoFormModal — Modal para agregar/editar el CONTACTO PRINCIPAL.
 *
 * Backend: ContactoInlineSchema — UN solo contacto (singular), con campos:
 *   nombres (req), apellidos?, dni?, cargo?, telefono?, celular?, email?
 * NO existen: direccion, descripcion, principal, localId.
 */
import { useCallback } from "react";
import type { Control } from "react-hook-form";
import { useController } from "react-hook-form";
import type { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import {
  type ContactoInline,
  contactoInlineSchema,
} from "../../schemas/liquidacion-form-base.schema";

export type ContactoFormData = z.infer<typeof contactoInlineSchema>;

interface ContactoFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (contacto: ContactoInline) => void;
  initialData?: ContactoInline;
}

const defaultInitialData: ContactoFormData = {
  nombres: "",
  apellidos: "",
  dni: "",
  cargo: "",
  telefono: "",
  celular: "",
  email: "",
};

function CampoTexto({
  control,
  name,
  label,
  placeholder,
  required,
  icon: Icon,
}: {
  control: Control<ContactoFormData>;
  name:
    | "nombres"
    | "apellidos"
    | "dni"
    | "telefono"
    | "celular"
    | "email"
    | "cargo";
  label: string;
  placeholder?: string;
  required?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  const { field, fieldState } = useController({
    name,
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        )}
        <Input
          id={name}
          placeholder={placeholder}
          className={Icon ? "pl-10 w-full" : "w-full"}
          {...field}
        />
      </div>
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

export function ContactoFormModal({
  open,
  onOpenChange,
  onSaved,
  initialData,
}: ContactoFormModalProps) {
  const isEditing = !!initialData;

  const formInitialData: ContactoFormData = initialData
    ? {
        nombres: initialData.nombres ?? "",
        apellidos: initialData.apellidos ?? "",
        dni: initialData.dni ?? "",
        cargo: initialData.cargo ?? "",
        telefono: initialData.telefono ?? "",
        celular: initialData.celular ?? "",
        email: initialData.email ?? "",
      }
    : defaultInitialData;

  const handleSubmit = useCallback(
    async (data: ContactoFormData) => {
      const contactoInline: ContactoInline = {
        nombres: data.nombres,
        apellidos: data.apellidos || undefined,
        dni: data.dni || undefined,
        cargo: data.cargo || undefined,
        telefono: data.telefono || undefined,
        celular: data.celular || undefined,
        email: data.email || undefined,
      };
      onSaved(contactoInline);
    },
    [onSaved],
  );

  return (
    <AppFormModal<ContactoFormData>
      open={open}
      onOpenChange={onOpenChange}
      title={isEditing ? "Editar Contacto" : "Agregar Contacto"}
      description={
        isEditing
          ? "Modifica los datos del contacto principal"
          : "Ingresa los datos del contacto principal"
      }
      eyebrow="Liquidación"
      icon={<Phone className="h-5 w-5 text-primary" />}
      primaryLabel={isEditing ? "Guardar" : "Agregar"}
      primaryLoadingLabel={isEditing ? "Guardando..." : "Agregando..."}
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={contactoInlineSchema}
      initialData={formInitialData}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Datos Personales */}
          <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
            <div className="flex items-center gap-2 border-b border-border/40 pb-2">
              <User className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold uppercase tracking-wide">
                Datos Personales
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CampoTexto
                control={methods.control}
                name="nombres"
                label="Nombres"
                placeholder="Nombres"
                required
                icon={User}
              />
              <CampoTexto
                control={methods.control}
                name="apellidos"
                label="Apellidos"
                placeholder="Apellidos"
              />
              <CampoTexto
                control={methods.control}
                name="dni"
                label="DNI"
                placeholder="DNI"
              />
              <CampoTexto
                control={methods.control}
                name="cargo"
                label="Cargo"
                placeholder="Cargo u ocupación"
                icon={Briefcase}
              />
            </div>
          </div>

          {/* Información de Contacto */}
          <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
            <div className="flex items-center gap-2 border-b border-border/40 pb-2">
              <Phone className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold uppercase tracking-wide">
                Información de Contacto
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CampoTexto
                control={methods.control}
                name="telefono"
                label="Teléfono"
                placeholder="Teléfono fijo"
                icon={Phone}
              />
              <CampoTexto
                control={methods.control}
                name="celular"
                label="Celular"
                placeholder="Celular"
                icon={Phone}
              />
              <div className="sm:col-span-2">
                <CampoTexto
                  control={methods.control}
                  name="email"
                  label="Email"
                  placeholder="email@ejemplo.com"
                  icon={Mail}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
