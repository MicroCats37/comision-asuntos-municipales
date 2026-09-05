"use client";

import { FilePenLine } from "lucide-react";
/**
 * TaludesEditFormModal — Edit form for Taludes (motor PorcentajeObra).
 * Reuses LiquidacionFormBodyBase (general) + Smart Fields in edit mode.
 */
import { useCallback, useMemo, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useEditarTaludes } from "../../hooks/useEditarTaludes";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import type { LiquidacionTaludesListItem } from "../../schemas/liquidacion-taludes.schema";
import { ValoresActualesCard } from "../../components/liquidacion-ui";
import {
  type TaludesFormData,
  taludesFormSchema,
} from "../../schemas/liquidacion-taludes-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { PrimeraRevisionTarifasSmartField } from "./PrimeraRevisionTarifasSmartField";

interface TaludesEditFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionTaludesListItem;
  onSuccess?: () => void;
}

const toContactoInline = (
  contacto: LiquidacionTaludesListItem["liquidacion_general"]["contacto"],
): ContactoInline | null => {
  if (!contacto?.nombres) return null;
  return {
    nombres: contacto.nombres,
    apellidos: contacto.apellidos ?? undefined,
    dni: contacto.dni ?? undefined,
    cargo: contacto.cargo ?? undefined,
    telefono: contacto.telefono ?? undefined,
    celular: contacto.celular ?? undefined,
    email: contacto.email ?? undefined,
  };
};

function buildInitialData(item: LiquidacionTaludesListItem): TaludesFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  return {
    denominacion: lg.denominacion_de_proyecto ?? "",
    municipalidad_id: lg.municipalidad?.id ?? "",
    expediente: lg.expediente ?? "",
    observacion: lg.observacion ?? "",
    retencion: lg.retencion ?? false,
    nombre_propietario: lg.proyecto.nombre_propietario,
    direccion: lg.proyecto.direccion,
    distrito_id: lg.proyecto.distrito?.id ?? "",
    urbanizacion: lg.proyecto.urbanizacion ?? undefined,
    entidad_tipo_documento:
      lg.proyecto.entidad?.tipo_documento === "DNI" ? "DNI" : "RUC",
    entidad_numero_documento: lg.proyecto.entidad?.numero_documento ?? "",
    entidad_razon_social: lg.proyecto.entidad?.razon_social ?? "",
    valor_declarado: lt.valor_declarado,
    tarifa_unica_id: lt.detalles[0]?.tarifa_aplicada_id,
    especialidades_seleccionadas: lt.detalles.map((d) => d.especialidad_id),
  };
}

export function TaludesEditFormModal({
  open,
  onOpenChange,
  item,
  onSuccess,
}: TaludesEditFormModalProps) {
  const liquidacionId = item.liquidacion_general.id;
  const editarMutation = useEditarTaludes(liquidacionId);
  const [contacto, setContacto] = useState<ContactoInline | null>(() =>
    toContactoInline(item.liquidacion_general.contacto),
  );
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const initialData = useMemo(() => buildInitialData(item), [item]);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: TaludesFormData) => {
      try {
        await editarMutation.mutateAsync({
          ...data,
          contacto: contacto ?? undefined,
        });
        notify.success("Liquidación editada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [editarMutation, contacto, onSuccess],
  );

  return (
    <>
      <AppFormModal<TaludesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Editar Liquidación — Taludes"
        eyebrow="Taludes"
        icon={<FilePenLine className="h-5 w-5 text-primary" />}
        primaryLabel="Guardar cambios"
        primaryLoadingLabel="Guardando..."
        primaryLoading={editarMutation.isPending}
        onPrimary={() => undefined}
        schema={taludesFormSchema}
        initialData={initialData}
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
                defaultValue={initialData.valor_declarado}
              />
            }
            valoresActualesSection={
              <ValoresActualesCard
                subTotal={item.liquidacion_general.sub_total}
                total={item.liquidacion_general.total}
              />
            }
            motorSection={
              <div className="space-y-3">
                <PrimeraRevisionTarifasSmartField
                  methods={methods}
                  tipo="taludes"
                />
                <CotizacionPorcentajeSmartField
                  methods={methods}
                  mode="edit"
                  tipo="taludes"
                  liquidacionId={liquidacionId}
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
