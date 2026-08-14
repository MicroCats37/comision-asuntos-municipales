"use client";

/**
 * NuevaRevisionEdificacionesFormModal — Form LIVIANO para nueva revisión de Edificaciones.
 *
 * Schema propio reducido (NO usa el form general):
 *  - Se hereda de la previa: valor_declarado, municipalidad_id, proyecto (card "Datos Anteriores")
 *  - Se edita: expediente, observacion, retencion, contacto, tarifas (radio, una preseleccionada)
 *
 * Layout responsivo 2 columnas como el form de primera revisión.
 * Cotización usa CotizacionNuevaRevisionSmartField (valor fijo + tarifa seleccionada por props).
 * Endpoint: POST /liquidaciones/edificaciones/nueva-revision
 */
import { useCallback, useEffect, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Building2, FileText, IdCard, MapPin, Phone, RefreshCw, Users } from "lucide-react";
import { notify } from "@/errors";
import { useQuery } from "@tanstack/react-query";
import { useController } from "react-hook-form";
import api from "@/lib/api";
import { useCrearNuevaRevisionEdificaciones } from "../../hooks/useCrearNuevaRevisionEdificaciones";
import {
  nuevaRevisionEdificacionesFormSchema,
  type NuevaRevisionEdificacionesFormData,
} from "../../schemas/liquidacion-nueva-revision-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { CotizacionNuevaRevisionSmartField } from "./CotizacionNuevaRevisionSmartField";
import { ContactoFormModal } from "./ContactoFormModal";
import type { UltimaRevisionItem } from "../../hooks/useUltimaRevisionEdificaciones";

interface TarifaVigente {
  id: string;
  especialidad: string;
  porcentaje_liquidacion: number;
}

// Preseleccionar la primera tarifa vigente
function usePreselectTarifa(open: boolean): {
  selectedTarifaId: string | null;
  setSelectedTarifaId: (id: string) => void;
} {
  const [selectedTarifaId, setSelectedTarifaId] = useState<string | null>(null);
  const { data: tarifas } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", "edificaciones", "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/edificaciones/tarifas/vigentes");
      return data.data?.tarifas || [];
    },
  });

  useEffect(() => {
    if (open && tarifas && tarifas.length > 0 && !selectedTarifaId) {
      setSelectedTarifaId(tarifas[0].id);
    }
    if (!open) setSelectedTarifaId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tarifas]);

  return { selectedTarifaId, setSelectedTarifaId };
}

interface NuevaRevisionEdificacionesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Liquidación previa COMPLETA (base) — se hereda valor_declarado, municipalidad, proyecto, contacto */
  previa: UltimaRevisionItem | null;
  onSuccess?: () => void;
}

const formatPercent = (value: number | undefined | null): string =>
  value == null ? "—" : `${(Number(value) * 100).toFixed(2)}%`;
const formatSoles = (value: number | undefined | null): string =>
  value == null ? "—" : `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatDate = (value?: string | null): string => {
  if (!value) return "—";
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleDateString("es-PE", { year: "numeric", month: "short", day: "numeric" });
};

/** Selector de tarifas — RADIO (selección única) con la primera preseleccionada */
function TarifasNuevaRevisionSelector({
  methods,
  selectedId,
  onSelect,
}: {
  methods: any;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { data: tarifas, isLoading } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", "edificaciones", "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/edificaciones/tarifas/vigentes");
      return data.data?.tarifas || [];
    },
  });

  if (isLoading) {
    return <div className="h-24 rounded-xl border bg-card animate-pulse" />;
  }

  if (!tarifas || tarifas.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay tarifas vigentes</p>;
  }

  return (
    <div className="space-y-2">
      <Label>Tarifa Vigente <span className="text-destructive">*</span></Label>
      <div className="flex flex-row flex-wrap gap-2" role="radiogroup" aria-label="Tarifas">
        {tarifas.map((tarifa) => {
          const isSelected = selectedId === tarifa.id;
          return (
            <label
              key={tarifa.id}
              role="radio"
              aria-checked={isSelected}
              className={[
                "rounded-lg border bg-background px-3 py-2.5 transition-all duration-200 text-left flex-1 min-w-[160px] flex flex-col gap-1.5 cursor-pointer",
                isSelected
                  ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                  : "border-border hover:border-primary/40",
              ].join(" ")}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={[
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                    isSelected ? "border-primary" : "border-border",
                  ].join(" ")}
                >
                  {isSelected && <span className="h-2 w-2 rounded-full bg-primary" />}
                </span>
                <span className="text-sm font-medium truncate">{tarifa.especialidad}</span>
              </div>
              <span className="text-xs font-semibold text-primary pl-6">
                {formatPercent(tarifa.porcentaje_liquidacion)}
              </span>
              <input
                type="radio"
                name="tarifa_vigente"
                className="sr-only"
                checked={isSelected}
                onChange={() => onSelect(tarifa.id)}
              />
            </label>
          );
        })}
      </div>
    </div>
  );
}

export function NuevaRevisionEdificacionesFormModal({
  open,
  onOpenChange,
  previa,
  onSuccess,
}: NuevaRevisionEdificacionesFormModalProps) {
  const crearMutation = useCrearNuevaRevisionEdificaciones();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);
  const { selectedTarifaId, setSelectedTarifaId } = usePreselectTarifa(open);

  // Prellenar contacto desde la previa cuando se abre
  useEffect(() => {
    if (open && previa?.liquidacion_general?.contacto) {
      const c = previa.liquidacion_general.contacto;
      setContacto({
        nombres: c.nombres ?? "",
        apellidos: c.apellidos ?? undefined,
        dni: c.dni ?? undefined,
        cargo: c.cargo ?? undefined,
        telefono: c.telefono ?? undefined,
        celular: c.celular ?? undefined,
        email: c.email ?? undefined,
      });
    }
  }, [open, previa]);

  const lg = previa?.liquidacion_general;
  const lt = previa?.liquidacion_tipo;
  const valorDeclaradoFijo = lt ? Number(lt.valor_declarado) : undefined;

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: NuevaRevisionEdificacionesFormData) => {
      if (!previa) return;
      try {
        await crearMutation.mutateAsync({
          ...data,
          liquidacion_previa_id: previa.liquidacion_general.id,
          contacto: contacto ?? undefined,
        });
        notify.success("Nueva revisión creada correctamente");
        setContacto(null);
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, previa, contacto, onSuccess],
  );

  // initialData — prellenar campos editables desde la previa
  const initialData: Partial<NuevaRevisionEdificacionesFormData> = {
    liquidacion_previa_id: previa?.liquidacion_general.id ?? "",
    expediente: previa?.liquidacion_general.expediente ?? "",
    observacion: previa?.liquidacion_general.observacion ?? "",
    retencion: previa?.liquidacion_general.retencion ?? false,
    tarifas_ids: [],
  };

  return (
    <>
      <AppFormModal<NuevaRevisionEdificacionesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Revisión"
        description={lg ? `Sobre: ${lg.proyecto.denominacion}` : "Crea una nueva revisión"}
        eyebrow="Edificaciones"
        icon={<RefreshCw className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Revisión"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={nuevaRevisionEdificacionesFormSchema}
        initialData={initialData as never}
        onSubmit={handleSubmit}
        size="lg"
      >
        {({ methods }) => (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* ── Columna Izquierda: SOLO card de Datos Anteriores ── */}
            <div className="space-y-4">
              {lg && (
                <div className="rounded-xl border border-border/50 bg-muted/20 p-5 space-y-4 h-full">
                  <div className="flex items-center gap-2 border-b border-border/40 pb-3">
                    <FileText className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">Datos Anteriores</h3>
                  </div>

                  {/* Header: proyecto + revision */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
                        <Building2 className="h-6 w-6 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-base font-bold text-foreground truncate">{lg.proyecto.denominacion}</p>
                        <p className="text-xs text-muted-foreground">
                          {lg.municipalidad?.codigo ? `${lg.municipalidad.codigo} - ` : ""}{lg.municipalidad?.nombre ?? "—"}
                        </p>
                      </div>
                    </div>
                    <span className="shrink-0 inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-sm font-bold text-primary">
                      Rev. {lg.numero_revision}
                    </span>
                  </div>

                  {/* Grid de datos heredados — 2 columnas, más espaciado */}
                  <div className="grid grid-cols-2 gap-x-5 gap-y-3 text-sm">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Expediente</span>
                      <span className="font-medium truncate">{lg.expediente || "—"}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Fecha Registro</span>
                      <span className="font-medium">{formatDate(lg.fecha_registro)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Propietario</span>
                      <span className="font-medium truncate">{lg.proyecto.nombre_propietario || "—"}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Valor Declarado</span>
                      <span className="font-medium">{formatSoles(lt?.valor_declarado)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">% Liquidación</span>
                      <span className="font-medium">{formatPercent(lt?.porcentaje_liquidacion)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Subtotal</span>
                      <span className="font-medium">{formatSoles(lg.sub_total)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Total</span>
                      <span className="font-medium">{formatSoles(lg.total)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Derecho Mín.</span>
                      <span className="font-medium">{formatSoles(lt?.derecho_minimo)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Derecho Máx.</span>
                      <span className="font-medium">{formatSoles(lt?.derecho_maximo)}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Creado Por</span>
                      <span className="font-medium truncate">
                        {lg.usuario_creador
                          ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos].filter(Boolean).join(" ") || lg.usuario_creador.username || "—"
                          : "—"}
                      </span>
                    </div>
                  </div>

                  {/* Entidad */}
                  {lg.proyecto.entidad && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground border-t border-border/40 pt-3">
                      <IdCard className="h-3 w-3 text-primary/60 shrink-0" />
                      <span className="truncate">
                        {lg.proyecto.entidad.razon_social} · {lg.proyecto.entidad.tipo_documento} {lg.proyecto.entidad.numero_documento}
                      </span>
                    </div>
                  )}
                  {lg.proyecto.direccion && (
                    <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{lg.proyecto.direccion}</span>
                    </div>
                  )}

                  {/* Observación previa */}
                  {lg.observacion && (
                    <div className="rounded-lg bg-amber-500/5 border border-amber-500/15 p-3">
                      <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Observación previa</span>
                      <p className="text-xs text-amber-700/90 font-medium leading-relaxed mt-1">{lg.observacion}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ── Columna Derecha: Editable + Tarifas + Cotización + Contacto ── */}
            <div className="space-y-4">
              {/* Datos editables de la revisión */}
              <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                  <FileText className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">Datos de la Revisión</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="expediente">Expediente <span className="text-destructive">*</span></Label>
                    <Input id="expediente" placeholder="Número de expediente" className="w-full" {...methods.register("expediente")} />
                  </div>
                  <div className="space-y-2">
                    <Label>Retención</Label>
                    <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-background px-3 py-2.5">
                      <Checkbox
                        id="retencion"
                        checked={!!methods.watch("retencion")}
                        onCheckedChange={(checked) => methods.setValue("retencion", !!checked)}
                      />
                      <Label htmlFor="retencion" className="text-sm font-medium cursor-pointer">¿Tiene retención?</Label>
                    </div>
                  </div>
                  <div className="sm:col-span-2 space-y-2">
                    <Label htmlFor="observacion">Observación</Label>
                    <Textarea id="observacion" placeholder="Observaciones (opcional)" rows={2} {...methods.register("observacion")} />
                  </div>
                </div>
              </div>

              {/* Tarifas — radio */}
              <div className="rounded-xl border border-border/50 bg-card p-4 space-y-3">
                <TarifasNuevaRevisionSelector
                  methods={methods}
                  selectedId={selectedTarifaId}
                  onSelect={(id) => {
                    setSelectedTarifaId(id);
                    methods.setValue("tarifas_ids", [id], { shouldValidate: true });
                  }}
                />
              </div>

              {/* Cotización con valor FIJO + tarifa seleccionada (props, sin useWatch) */}
              <CotizacionNuevaRevisionSmartField
                valorDeclarado={valorDeclaradoFijo}
                tarifaId={selectedTarifaId}
              />

              {/* Contacto — prellenado desde la previa */}
              <div className="rounded-xl border border-border/50 bg-card p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    <Phone className="h-3.5 w-3.5 text-primary/70" />
                    <span>Contacto Principal</span>
                    {contacto && (
                      <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[9px] font-bold text-primary">
                        Heredado
                      </span>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setContactoModalOpen(true)}
                    className="h-8 gap-1 text-xs"
                  >
                    {contacto ? "Editar" : "Agregar"}
                  </Button>
                </div>
                {contacto ? (
                  <div className="flex items-center gap-2 mt-3 rounded-lg border border-border/60 bg-background px-3 py-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {contacto.nombres} {contacto.apellidos}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {[contacto.cargo, contacto.email, contacto.celular].filter(Boolean).join(" · ") || "Sin datos"}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground/70 italic mt-2">Sin contacto registrado</p>
                )}
              </div>
            </div>
          </div>
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
