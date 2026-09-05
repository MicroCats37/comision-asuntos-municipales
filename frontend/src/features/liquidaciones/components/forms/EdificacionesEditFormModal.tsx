"use client";

import { FilePenLine, FileText } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useEditarEdificaciones } from "../../hooks/useEditarEdificaciones";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";
import { ValoresActualesCard } from "../../components/liquidacion-ui";
import {
  type EdificacionesFormData,
  edificacionesFormSchema,
} from "../../schemas/liquidacion-edificaciones-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { EspecialidadesPorTipoTramiteSmartField } from "./EspecialidadesPorTipoTramiteSmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { TipoTramiteSmartField } from "./TipoTramiteSmartField";

interface EdificacionesEditFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionEdificacionesListItem;
  onSuccess?: () => void;
}

const toContactoInline = (
  contacto: LiquidacionEdificacionesListItem["liquidacion_general"]["contacto"],
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

function buildInitialData(
  item: LiquidacionEdificacionesListItem,
): EdificacionesFormData {
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
    tipo_tramite: lt.tipo_tramite as EdificacionesFormData["tipo_tramite"],
    tarifa_unica_id: lt.detalles[0]?.tarifa_aplicada_id,
    especialidades_seleccionadas: lt.detalles.map((d) => d.especialidad_id),
  };
}

export function EdificacionesEditFormModal({
  open,
  onOpenChange,
  item,
  onSuccess,
}: EdificacionesEditFormModalProps) {
  const liquidacionId = item.liquidacion_general.id;
  const editarMutation = useEditarEdificaciones(liquidacionId);
  const [contacto, setContacto] = useState<ContactoInline | null>(() =>
    toContactoInline(item.liquidacion_general.contacto),
  );
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  // canEditProyecto: false for revisions > 1 (project fields locked)
  const canEditProyecto = useMemo(
    () => canEditLiquidacion(item.liquidacion_general).canEditProyecto,
    [item.liquidacion_general],
  );

  const initialData = useMemo(() => buildInitialData(item), [item]);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: EdificacionesFormData) => {
      try {
        // canEditProyecto=false strips proyecto from PATCH payload to avoid backend errors
        await editarMutation.mutateAsync(
          { ...data, contacto: contacto ?? undefined },
          canEditProyecto,
        );
        notify.success("Liquidación editada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [editarMutation, contacto, onSuccess, canEditProyecto],
  );

  return (
    <>
      <AppFormModal<EdificacionesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Editar Liquidación — Edificaciones"
        eyebrow="Edificaciones"
        icon={<FilePenLine className="h-5 w-5 text-primary" />}
        primaryLabel="Guardar cambios"
        primaryLoadingLabel="Guardando..."
        primaryLoading={editarMutation.isPending}
        onPrimary={() => undefined}
        schema={edificacionesFormSchema}
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
            proyectoFieldsExtra={<TipoTramiteSmartField methods={methods} />}
            valoresActualesSection={
              <ValoresActualesCard
                subTotal={item.liquidacion_general.sub_total}
                total={item.liquidacion_general.total}
              />
            }
            motorSection={
              <div className="space-y-3">
                <EspecialidadesPorTipoTramiteSmartField
                  methods={methods}
                  mode="edit"
                  fecha={item.liquidacion_general.fecha_registro}
                  autoSelectAllForGroupA={false}
                />
                <CotizacionPorcentajeSmartField
                  methods={methods}
                  mode="edit"
                  tipo="edificaciones"
                  liquidacionId={liquidacionId}
                />
              </div>
            }
            canEditProyecto={canEditProyecto}
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
