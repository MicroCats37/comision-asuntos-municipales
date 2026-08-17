"use client";

import { FileText } from "lucide-react";
/**
 * MecanicaSuelosFormModal — Form delgado para Mecánica de Suelos (motor M2).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields M2.
 */
import { useCallback, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useCrearMecanicaSuelos } from "../../hooks/useCrearMecanicaSuelos";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import {
  type MecanicaSuelosFormData,
  mecanicaSuelosFormSchema,
} from "../../schemas/liquidacion-mecanica-suelos-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionM2SmartField } from "./CotizacionM2SmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { TarifasM2SmartField } from "./TarifasM2SmartField";

interface MecanicaSuelosFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function MecanicaSuelosFormModal({
  open,
  onOpenChange,
  onSuccess,
}: MecanicaSuelosFormModalProps) {
  const crearMutation = useCrearMecanicaSuelos();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: MecanicaSuelosFormData) => {
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
          printLiquidacion(created, "mecanica-suelos");
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
      <AppFormModal<MecanicaSuelosFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Mecánica de Suelos"
        eyebrow="Mecánica de Suelos"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={mecanicaSuelosFormSchema}
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
              <MoneyInput
                name="area_solicitada"
                label="Área Solicitada (m²)"
                required
                control={methods.control}
                min={0}
                defaultValue={0}
                className="w-full"
              />
            }
            motorSection={
              <div className="space-y-3">
                <TarifasM2SmartField methods={methods} tipo="mecanica-suelos" />
                <CotizacionM2SmartField
                  methods={methods}
                  tipo="mecanica-suelos"
                />
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
