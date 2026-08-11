"use client";

/**
 * TaludesFormModal — Form delgado para Taludes (motor PorcentajeObra).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields específicos del motor.
 */
import { useCallback, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { FileText } from "lucide-react";
import { useCrearTaludes } from "../../hooks/useCrearTaludes";
import { taludesFormSchema, type TaludesFormData } from "../../schemas/liquidacion-taludes-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { PrimeraRevisionTarifasSmartField } from "./PrimeraRevisionTarifasSmartField";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { ContactoFormModal } from "./ContactoFormModal";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";

interface TaludesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function TaludesFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: TaludesFormModalProps) {
  const crearMutation = useCrearTaludes();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: TaludesFormData) => {
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
      <AppFormModal<TaludesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Taludes"
        eyebrow="Taludes"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={taludesFormSchema}
        initialData={{ valor_declarado: 0 }}
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
              <MoneyInput
                name="valor_declarado"
                label="Valor Declarado (S/)"
                placeholder="S/ 0.00"
                control={methods.control}
                required
                defaultValue={0}
              />
            }
            motorSection={
              <div className="space-y-3">
                <PrimeraRevisionTarifasSmartField methods={methods} tipo="taludes" />
                <CotizacionPorcentajeSmartField methods={methods} />
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
