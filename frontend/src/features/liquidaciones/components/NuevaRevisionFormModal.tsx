"use client";

import {
  FileText,
  MessageSquare,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { notify } from "@/errors";
import api from "@/lib/api";
import { useCotizacionNuevaRevision } from "../hooks/useCotizacion";
import { useCrearNuevaRevision, useNuevaRevisionFormulario } from "../hooks/useNuevaRevision";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";
import type { ProyectistaInline, ProyectistaResult } from "../types/proyectista";
import { CotizacionSection } from "./CotizacionSection";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { ProyectistasSection } from "./ProyectistasSection";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function formatEnumLabel(value: string | undefined | null): string {
  if (!value) return "—";
  return value.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(" ");
}

const nuevaRevisionSchema = z.object({
  observacion: z.string().optional(),
});

type FormData = z.infer<typeof nuevaRevisionSchema>;

interface Props {
  liquidacionPreviaId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function NuevaRevisionFormModal({ liquidacionPreviaId: initialId, open, onOpenChange, onSuccess }: Props) {
  const [liquidacionPreviaId, setLiquidacionPreviaId] = useState<string | null>(initialId);
  const [searchInput, setSearchInput] = useState("");
  const [searching, setSearching] = useState(false);
  const searchAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setLiquidacionPreviaId(initialId);
    setSearchInput("");
  }, [initialId, open]);

  const handleSearch = useCallback(async () => {
    const q = searchInput.trim();
    if (!q) return;

    if (UUID_RE.test(q)) {
      setLiquidacionPreviaId(q);
      return;
    }

    setSearching(true);
    if (searchAbortRef.current) searchAbortRef.current.abort();
    const controller = new AbortController();
    searchAbortRef.current = controller;

    try {
      const res = await api.get("/liquidaciones/edificaciones", {
        params: { page: 1, page_size: 50 },
        signal: controller.signal,
      });
      const items = res.data?.data?.items ?? [];
      const found = items.find((item: any) => item.public_id === q);
      if (found) {
        setLiquidacionPreviaId(found.id);
      } else {
        notify.error("No se encontró una liquidación con ese código");
      }
    } catch (err: any) {
      if (err?.name !== "AbortError" && err?.code !== "ERR_CANCELED") {
        notify.error("Error al buscar la liquidación");
      }
    } finally {
      setSearching(false);
    }
  }, [searchInput]);

  useEffect(() => {
    return () => { if (searchAbortRef.current) searchAbortRef.current.abort(); };
  }, []);

  const [showProyectistaModal, setShowProyectistaModal] = useState(false);
  const [selectedProyectistas, setSelectedProyectistas] = useState<ProyectistaResult[]>([]);
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<string[]>([]);
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionQuote | null>(null);

  const { data: formulario, isLoading: isLoadingFormulario } = useNuevaRevisionFormulario(liquidacionPreviaId, open && !!liquidacionPreviaId);

  useEffect(() => {
    if (!formulario?.proyectistas_actuales) {
      setSelectedProyectistas([]);
      return;
    }
    setSelectedProyectistas(
      formulario.proyectistas_actuales.map((p) => ({
        id: p.id ?? "",
        nombres: p.perfil_ingeniero_nombres ?? p.nombres ?? "",
        apellidos: p.perfil_ingeniero_apellidos ?? p.apellidos ?? "",
        cip: p.perfil_ingeniero_cip ?? p.cip ?? undefined,
        dni: undefined,
        cap: undefined,
        creado: false,
      })),
    );
  }, [formulario]);

  const handleProyectistaSaved = useCallback((proyectista: ProyectistaInline) => {
    setSelectedProyectistas((prev) => {
      if (prev.some((p) => p.cip === proyectista.cip)) return prev;
      return [...prev, { id: proyectista.cip, nombres: proyectista.nombres ?? "", apellidos: proyectista.apellidos ?? "", cip: proyectista.cip, dni: "", cap: proyectista.capitulo ?? undefined, creado: false }];
    });
    setShowProyectistaModal(false);
  }, []);

  const handleRemoveProyectista = useCallback((id: string) => {
    setSelectedProyectistas((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleRevisionToggle = useCallback((id: string) => {
    setSelectedRevisionIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  }, []);

  useEffect(() => { setCotizacionQuote(null); }, [selectedRevisionIds]);

  const { data: variablesFinancieras, isLoading: isLoadingVariables } = useVariablesFinancieras();
  const crearMutation = useCrearNuevaRevision();
  const cotizacionMutation = useCotizacionNuevaRevision();

  const revisionesVigentes = formulario?.revisiones_vigentes ?? [];

  const handleCotizar = useCallback(async () => {
    if (!liquidacionPreviaId || selectedRevisionIds.length === 0) return;
    try {
      const result = await cotizacionMutation.mutateAsync({
        liquidacion_previa_id: liquidacionPreviaId,
        revisiones_ids: selectedRevisionIds,
      });
      setCotizacionQuote(result);
    } catch { /* handled */ }
  }, [cotizacionMutation, liquidacionPreviaId, selectedRevisionIds]);

  const handleSubmit = async (data: FormData) => {
    if (!liquidacionPreviaId) { notify.error("Seleccione una liquidación previa"); return; }
    if (selectedRevisionIds.length === 0) { notify.error("Debe seleccionar al menos una revisión"); return; }
    if (selectedProyectistas.length === 0) { notify.error("Debe seleccionar al menos un proyectista"); return; }

    await crearMutation.mutateAsync({
      liquidacion_previa_id: liquidacionPreviaId,
      revisiones_ids: selectedRevisionIds,
      proyectistas_ids: selectedProyectistas.map((p) => p.id),
      observacion: data.observacion || undefined,
    });
    notify.success("Nueva revisión creada correctamente");
    setSelectedRevisionIds([]);
    setCotizacionQuote(null);
    onSuccess?.();
  };

  const hasProject = !!liquidacionPreviaId;
  const numeroRevision = formulario?.numero_revision ?? 0;
  const nuevoNumeroRevision = numeroRevision + 1;
  const isLoading = !liquidacionPreviaId ? false : isLoadingFormulario;

  return (
    <>
      <AppFormModal
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Revisión"
        description={formulario ? `Rev ${numeroRevision} → ${nuevoNumeroRevision}${formulario.cobra ? " · Cobra" : " · No cobra"}` : "Busque la liquidación previa para continuar"}
        eyebrow="Edificaciones"
        icon={<FileText className="h-5 w-5" />}
        primaryLabel="Crear Revisión"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        primaryDisabled={selectedRevisionIds.length === 0 || !hasProject || !formulario}
        onPrimary={() => {}}
        schema={nuevaRevisionSchema}
        initialData={{ observacion: "" }}
        fields={[{
          name: "observacion",
          label: "Observación (opcional)",
          type: "textarea",
          placeholder: "Observaciones adicionales...",
          icon: MessageSquare,
          labelClassName: "text-primary font-semibold",
        }]}
        onSubmit={handleSubmit}
        size="lg"
        isLoading={isLoading}
        bodyClassName="overflow-y-auto"
      >
        {() => (
          <>
            {!liquidacionPreviaId ? (
              <div className="flex flex-col items-center justify-center py-12 gap-4">
                <FileText className="h-12 w-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground text-center max-w-xs">
                  Ingrese el código o ID de la liquidación previa
                </p>
                <div className="flex items-center gap-2 w-full max-w-sm">
                  <Input
                    placeholder="Ej. LIQ-2026-00001 o UUID"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSearch();
                    }}
                    className="h-9"
                  />
                  <Button
                    variant="default" size="sm"
                    onClick={handleSearch}
                    disabled={searching || !searchInput.trim()}
                    className="h-9 px-3 gap-1"
                  >
                    <Search className="h-4 w-4" />
                    {searching ? "..." : "Buscar"}
                  </Button>
                </div>
              </div>
            ) : !formulario && !isLoadingFormulario ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <p className="text-sm text-destructive">No se encontró la liquidación</p>
                <Button variant="outline" size="sm" onClick={() => setLiquidacionPreviaId(null)}>Intentar con otro código</Button>
              </div>
            ) : formulario ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2 flex items-center justify-between px-3 py-2 rounded-lg bg-muted/40 border border-border/50">
                  <span className="text-xs font-medium text-muted-foreground">
                    Liquidación previa: <span className="font-mono text-primary font-semibold">{formulario.liquidacion_previa_id.slice(0, 8)}...</span>
                  </span>
                  <Button variant="ghost" size="sm" onClick={() => { setLiquidacionPreviaId(null); setSearchInput(""); }} className="h-7 text-xs">Cambiar</Button>
                </div>

                <div className="md:col-span-2 rounded-xl border bg-card p-4 space-y-4">
                  <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-2.5 bg-muted/40 border-b rounded-t-xl">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Datos de Liquidación Previa</h4>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <LabelValue label="Tipo de Trámite" value={formatEnumLabel(formulario.tipo_tramite)} />
                    <LabelValue label="Revisión actual" value={`N° ${numeroRevision}`} />
                    <LabelValue label="Nueva revisión" value={`N° ${nuevoNumeroRevision}`} />
                    <LabelValue label="¿Cobra?" value={formulario.cobra ? "Sí" : "No"} valueClassName={formulario.cobra ? "text-emerald-600" : ""} />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <LabelValue label="Proyecto" value={formulario.proyecto_public_id} mono />
                    <LabelValue label="Nombre" value={formulario.proyecto_nombre} />
                    <LabelValue label="Valor (S/)" value={formulario.valor_proyecto?.toLocaleString("es-PE", { minimumFractionDigits: 2 })} />
                    <LabelValue label="Base de cálculo" value={formulario.valor_base_calculo?.toLocaleString("es-PE", { minimumFractionDigits: 2 })} />
                  </div>
                </div>

                <div className="rounded-xl border bg-card p-4 space-y-3">
                  <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-2.5 bg-muted/40 border-b rounded-t-xl">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Revisiones</h4>
                    <span className="ml-auto text-[10px] text-muted-foreground/60">(seleccionar 1)</span>
                  </div>
                  <RevisionesVigentesTable
                    revisiones={revisionesVigentes as any[]}
                    selectedId={selectedRevisionIds[0] ?? null}
                    onSelectRevision={handleRevisionToggle}
                    isLoading={isLoadingFormulario}
                  />
                </div>

                <div className="rounded-xl border bg-card p-4 space-y-3">
                  <ProyectistasSection
                    selectedProyectistas={selectedProyectistas}
                    onAddProyectista={() => setShowProyectistaModal(true)}
                    onRemoveProyectista={handleRemoveProyectista}
                  />
                </div>

                <div className="md:col-span-2">
                  <CotizacionSection
                    quote={cotizacionQuote}
                    isLoading={cotizacionMutation.isPending}
                    onCotizar={handleCotizar}
                    hasErrors={false}
                    hasValidValorBase={hasProject}
                    hasTarifa={selectedRevisionIds.length > 0}
                    variablesFinancieras={variablesFinancieras}
                    isLoadingVariables={isLoadingVariables}
                  />
                </div>
              </div>
            ) : null}
          </>
        )}
      </AppFormModal>

      <ProyectistaFormModal open={showProyectistaModal} onOpenChange={setShowProyectistaModal} onSaved={handleProyectistaSaved} />
    </>
  );
}

function LabelValue({ label, value, mono, valueClassName }: { label: string; value: React.ReactNode; mono?: boolean; valueClassName?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className={`text-sm font-medium ${mono ? "font-mono" : ""} ${valueClassName ?? "text-foreground"}`}>{value || "—"}</span>
    </div>
  );
}
