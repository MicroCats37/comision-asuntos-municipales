"use client";

/**
 * EdificacionesFormModal — Form delgado para Edificaciones (motor PorcentajeObra).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields específicos del motor.
 */
import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { FileText } from "lucide-react";
import { useCrearEdificaciones } from "../../hooks/useCrearEdificaciones";
import { edificacionesFormSchema, type EdificacionesFormData } from "../../schemas/liquidacion-edificaciones-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { PrimeraRevisionTarifasSmartField } from "./PrimeraRevisionTarifasSmartField";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { ContactoFormModal } from "./ContactoFormModal";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";

interface EdificacionesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /** Recibe la liquidación creada (del backend) para abrir el PDF */
  onCreated?: (item: PdfLiquidacionItem) => void;
}

export function EdificacionesFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: EdificacionesFormModalProps) {
  const crearMutation = useCrearEdificaciones();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: EdificacionesFormData) => {
      try {
        const result = await crearMutation.mutateAsync({ ...data, contacto: contacto ?? undefined });
        notify.success("Liquidación creada correctamente");
        setContacto(null);
        // Desenvolver ApiResponse → data
        const created = (result as { data?: PdfLiquidacionItem })?.data as PdfLiquidacionItem | undefined;
        onCreated?.(created as PdfLiquidacionItem);
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, contacto, onSuccess, onCreated],
  );

  return (
    <>
      <AppFormModal<EdificacionesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Edificaciones"
        eyebrow="Edificaciones"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={edificacionesFormSchema}
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
                <PrimeraRevisionTarifasSmartField methods={methods} tipo="edificaciones" />
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
