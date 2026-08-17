"use client";

import { FileText } from "lucide-react";
/**
 * TaludesFormModal — Form delgado para Taludes (motor PorcentajeObra).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields específicos del motor.
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useCrearTaludes } from "../../hooks/useCrearTaludes";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import {
  type TaludesFormData,
  taludesFormSchema,
} from "../../schemas/liquidacion-taludes-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { PrimeraRevisionTarifasSmartField } from "./PrimeraRevisionTarifasSmartField";

interface TaludesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function TaludesFormModal({
  open,
  onOpenChange,
  onSuccess,
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
        const result = await crearMutation.mutateAsync({
          ...data,
          contacto: contacto ?? undefined,
        });
        notify.success("Liquidación creada correctamente");
        setContacto(null);
        // Mismo window de impresión que el botón PDF de las cards
        const created = (result as { data?: PdfLiquidacionItem })?.data as
          | PdfLiquidacionItem
          | undefined;
        if (created) {
          printLiquidacion(created, "taludes");
        }
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, contacto, onSuccess],
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
                <PrimeraRevisionTarifasSmartField
                  methods={methods}
                  tipo="taludes"
                />
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
