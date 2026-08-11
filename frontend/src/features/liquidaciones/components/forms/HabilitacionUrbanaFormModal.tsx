"use client";

/**
 * HabilitacionUrbanaFormModal — Form delgado para Habilitación Urbana (motor M2).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields M2.
 */
import { useCallback, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { notify } from "@/errors";
import { FileText } from "lucide-react";
import { useCrearHabilitacionUrbana } from "../../hooks/useCrearHabilitacionUrbana";
import { habilitacionUrbanaFormSchema, type HabilitacionUrbanaFormData } from "../../schemas/liquidacion-habilitacion-urbana-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { TarifasM2SmartField } from "./TarifasM2SmartField";
import { CotizacionM2SmartField } from "./CotizacionM2SmartField";
import { ContactoFormModal } from "./ContactoFormModal";

interface HabilitacionUrbanaFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function HabilitacionUrbanaFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: HabilitacionUrbanaFormModalProps) {
  const crearMutation = useCrearHabilitacionUrbana();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: HabilitacionUrbanaFormData) => {
      try {
        await crearMutation.mutateAsync({ ...data, contacto: contacto ?? undefined });
        notify.success("Liquidación creada correctamente");
        setContacto(null);
        onSuccess?.();
        onCreated?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, contacto, onSuccess, onCreated],
  );

  return (
    <>
      <AppFormModal<HabilitacionUrbanaFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Habilitación Urbana"
        eyebrow="Habilitación Urbana"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={habilitacionUrbanaFormSchema}
        initialData={{ area_solicitada: 0 }}
        onSubmit={handleSubmit}
      >
        {({ methods }) => (
          <LiquidacionFormBodyBase
            control={methods.control as never}
            methods={methods}
            contacto={contacto}
            onAddContacto={() => setContactoModalOpen(true)}
            onRemoveContacto={() => setContacto(null)}
            tramiteField={
              <div className="space-y-2">
                <Label htmlFor="area_solicitada">Área Solicitada (m²) <span className="text-destructive">*</span></Label>
                <Input
                  id="area_solicitada"
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  className="w-full"
                  {...methods.register("area_solicitada", { valueAsNumber: true })}
                />
              </div>
            }
            motorSection={
              <div className="space-y-3">
                <TarifasM2SmartField methods={methods} tipo="habilitacion-urbana" />
                <CotizacionM2SmartField methods={methods} tipo="habilitacion-urbana" />
              </div>
            }
          />
        )}
      </AppFormModal>

      <ContactoFormModal
        open={contactoModalOpen}
        onOpenChange={setContactoModalOpen}
        onSaved={handleContactoSaved}
        initialData={contacto ?? undefined}
      />
    </>
  );
}
