"use client";

import { FileText } from "lucide-react";
/**
 * ImpactoVialFormModal — Form delgado para Impacto Vial (motor PorcentajeObra).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields específicos del motor.
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useCrearImpactoVial } from "../../hooks/useCrearImpactoVial";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import {
  type ImpactoVialFormData,
  impactoVialFormSchema,
} from "../../schemas/liquidacion-impacto-vial-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { PrimeraRevisionTarifasSmartField } from "./PrimeraRevisionTarifasSmartField";

interface ImpactoVialFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ImpactoVialFormModal({
  open,
  onOpenChange,
  onSuccess,
}: ImpactoVialFormModalProps) {
  const crearMutation = useCrearImpactoVial();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: ImpactoVialFormData) => {
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
          printLiquidacion(created, "impacto-vial");
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
      <AppFormModal<ImpactoVialFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Impacto Vial"
        eyebrow="Impacto Vial"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={impactoVialFormSchema}
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
                  tipo="impacto-vial"
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
