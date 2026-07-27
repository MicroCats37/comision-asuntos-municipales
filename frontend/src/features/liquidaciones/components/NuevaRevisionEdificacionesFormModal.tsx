"use client";

import { FileText, MessageSquare, Search } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { z } from "zod";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { notify } from "@/errors";
import { useCotizacionNuevaRevision } from "../hooks/useCotizacion";
import { useLiquidacionesEdificacionesPorDocumento } from "../hooks/useLiquidacionesEdificaciones";
import { useCrearNuevaRevision, useNuevaRevisionFormulario } from "../hooks/useNuevaRevision";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import type { CotizacionQuote, LiquidacionEdificacionOut } from "../types/liquidacion-edificaciones";
import type { ContactoInline } from "../types/contacto";
import { ContactoFormModal } from "./ContactoFormModal";
import { ContactosSection } from "./ContactosSection";
import { CotizacionSection } from "./CotizacionSection";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";

const TIPO_TRAMITE_OPTIONS = [
  { value: "OBRA_NUEVA", label: "Revision" },
  { value: "MODIFICACION_LICENCIA", label: "Modificación de licencia" },
  { value: "VARIACION_PROYECTO_APROBADO", label: "Variación proyecto aprobado" },
] as const;
const DEFAULT_TIPO_TRAMITE = "OBRA_NUEVA";

const nuevaRevisionSchema = z.object({
  observacion: z.string().optional(),
});

type FormData = z.infer<typeof nuevaRevisionSchema>;

interface Props {
  liquidacionPreviaId?: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: (liquidacion: LiquidacionEdificacionOut) => void;
}

function formatSoles(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function NuevaRevisionEdificacionesFormModal({
  liquidacionPreviaId,
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: Props) {
  const [selectedLiquidacionPreviaId, setSelectedLiquidacionPreviaId] = useState<string | null>(liquidacionPreviaId ?? null);
  const [searchInput, setSearchInput] = useState("");
  const [submittedDocumento, setSubmittedDocumento] = useState<string | null>(null);

  const [selectedTipoTramite, setSelectedTipoTramite] = useState(DEFAULT_TIPO_TRAMITE);
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<string[]>([]);
  const selectedRevisionIdsRef = useRef<string[]>([]);
  const [selectedContactos, setSelectedContactos] = useState<ContactoInline[]>([]);
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionQuote | null>(null);

  const { data: formulario, isLoading: isLoadingFormulario } = useNuevaRevisionFormulario(
    selectedLiquidacionPreviaId,
    open && !!selectedLiquidacionPreviaId,
  );
  const {
    items: documentoResults,
    total: documentoResultsTotal,
    isLoading: isSearchingDocumento,
    isError: isSearchDocumentoError,
  } = useLiquidacionesEdificacionesPorDocumento({
    numeroDocumento: open && !selectedLiquidacionPreviaId ? submittedDocumento : null,
    page: 1,
    pageSize: 10,
  });
  const { data: variablesFinancieras, isLoading: isLoadingVariables } = useVariablesFinancieras();
  const crearMutation = useCrearNuevaRevision();
  const cotizacionMutation = useCotizacionNuevaRevision();
  const cotizarNuevaRevisionRef = useRef(cotizacionMutation.mutateAsync);

  useEffect(() => {
    cotizarNuevaRevisionRef.current = cotizacionMutation.mutateAsync;
  }, [cotizacionMutation.mutateAsync]);

  const revisionesVigentes = formulario?.revisiones_vigentes ?? [];
  const effectiveTipoTramite = DEFAULT_TIPO_TRAMITE;
  const selectedRevision = revisionesVigentes.find((revision) => revision.id === selectedRevisionIds[0]) ?? null;
  const selectedTarifa = selectedRevision
    ? {
        porcentaje_liquidacion: selectedRevision.porcentaje_liquidacion,
        derecho_minimo: selectedRevision.derecho_minimo,
        derecho_maximo: selectedRevision.derecho_maximo,
        porcentaje_minimo_uit: selectedRevision.porcentaje_minimo_uit,
        especialidades: selectedRevision.especialidades,
      }
    : null;

  useEffect(() => {
    if (!open) return;
    setSelectedLiquidacionPreviaId(liquidacionPreviaId ?? null);
    setSearchInput("");
    setSubmittedDocumento(null);
    setSelectedRevisionIds([]);
    setSelectedTipoTramite(DEFAULT_TIPO_TRAMITE);
    setSelectedContactos([]);
    setEditingContactoIndex(null);
    setCotizacionQuote(null);
  }, [open, liquidacionPreviaId]);

  useEffect(() => {
    selectedRevisionIdsRef.current = selectedRevisionIds;
  }, [selectedRevisionIds]);

  const runCotizacion = useCallback(async (tipoTramite: string, revisionIds: string[]) => {
    if (!selectedLiquidacionPreviaId || revisionIds.length !== 1) {
      setCotizacionQuote(null);
      return;
    }
    setCotizacionQuote(null);
    try {
      const result = await cotizarNuevaRevisionRef.current({
        liquidacion_previa_id: selectedLiquidacionPreviaId,
        revisiones_ids: revisionIds,
        tipo_tramite: tipoTramite || DEFAULT_TIPO_TRAMITE,
      });
      setCotizacionQuote(result);
    } catch (error) {
      setCotizacionQuote(null);
      notify.error("No se pudo calcular la cotización");
      console.error("Nueva revisión: error al cotizar", error);
    }
  }, [selectedLiquidacionPreviaId]);

  const handleTipoTramiteChange = useCallback((tipoTramite: string) => {
    setSelectedTipoTramite(tipoTramite);
    void runCotizacion(tipoTramite || DEFAULT_TIPO_TRAMITE, selectedRevisionIds);
  }, [runCotizacion, selectedRevisionIds]);

  const handleRevisionSelect = useCallback((revisionId: string) => {
    const nextRevisionIds = selectedRevisionIds.includes(revisionId) ? [] : [revisionId];
    setSelectedRevisionIds(nextRevisionIds);
    void runCotizacion(effectiveTipoTramite, nextRevisionIds);
  }, [effectiveTipoTramite, runCotizacion, selectedRevisionIds]);

  useEffect(() => {
    if (!formulario) return;
    const nextTipoTramite = formulario.tipo_tramite || DEFAULT_TIPO_TRAMITE;
    setSelectedTipoTramite((current) => (current === nextTipoTramite ? current : nextTipoTramite));
  }, [formulario, runCotizacion]);

  useEffect(() => {
    if (!open || !formulario || selectedRevisionIds.length !== 1) return;
    void runCotizacion(effectiveTipoTramite, selectedRevisionIds);
  }, [effectiveTipoTramite, formulario, open, runCotizacion, selectedRevisionIds]);

  const handleSearch = useCallback(async () => {
    const q = searchInput.trim();
    if (!q) return;

    if (q.length !== 8 && q.length !== 11) {
      notify.error("Ingrese un DNI de 8 dígitos o RUC de 11 dígitos");
      return;
    }

    setSubmittedDocumento(q);
  }, [searchInput]);

  const handleCotizar = useCallback(() => {
    void runCotizacion(effectiveTipoTramite, selectedRevisionIds);
  }, [effectiveTipoTramite, runCotizacion, selectedRevisionIds]);

  const handleContactoSaved = useCallback((contacto: ContactoInline) => {
    if (editingContactoIndex !== null) {
      setSelectedContactos((prev) => {
        const next = [...prev];
        next[editingContactoIndex] = contacto;
        return next;
      });
    } else {
      setSelectedContactos((prev) => [...prev, contacto]);
    }
    setShowContactoModal(false);
    setEditingContactoIndex(null);
  }, [editingContactoIndex]);

  const handleSubmit = async (data: FormData) => {
    if (!selectedLiquidacionPreviaId) {
      notify.error("Seleccione una liquidación previa");
      return;
    }
    if (selectedRevisionIds.length !== 1) {
      notify.error("Debe seleccionar una revisión");
      return;
    }

    const created = await crearMutation.mutateAsync({
      liquidacion_previa_id: selectedLiquidacionPreviaId,
      revisiones_ids: selectedRevisionIds,
      proyectistas_ids: [],
      contactos: selectedContactos.map(({ localId: _localId, ...contacto }) => contacto),
      observacion: data.observacion || undefined,
      tipo_tramite: effectiveTipoTramite,
    });
    notify.success("Nueva revisión creada correctamente");
    onSuccess?.();
    onCreated?.(created);
    onOpenChange(false);
  };

  const numeroRevision = formulario?.numero_revision ?? 0;
  const nuevoNumeroRevision = numeroRevision + 1;
  const hasFormulario = !!selectedLiquidacionPreviaId && !!formulario;
  const isLoading = !!selectedLiquidacionPreviaId && isLoadingFormulario;

  return (
    <>
      <AppFormModal
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Revisión"
        description={formulario ? `Rev ${numeroRevision} → ${nuevoNumeroRevision}` : "Busque la liquidación previa para continuar"}
        eyebrow="Edificaciones"
        icon={<FileText className="h-5 w-5" />}
        primaryLabel="Crear Revisión"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        primaryDisabled={!hasFormulario || selectedRevisionIds.length !== 1}
        onPrimary={() => {}}
        schema={nuevaRevisionSchema}
        initialData={{ observacion: "" }}
        fields={[
          {
            name: "observacion",
            label: "Observación",
            type: "textarea",
            placeholder: "Observaciones adicionales (opcional)",
            icon: MessageSquare,
            labelClassName: "text-primary font-semibold",
          },
        ]}
        onSubmit={handleSubmit}
        size="lg"
        isLoading={isLoading}
        bodyClassName="overflow-y-auto"
      >
        {() => (
          <div className="space-y-4">
            {!selectedLiquidacionPreviaId ? (
              <SearchPreviousLiquidacion
                searchInput={searchInput}
                searching={isSearchingDocumento}
                searched={!!submittedDocumento}
                results={documentoResults}
                total={documentoResultsTotal}
                isError={isSearchDocumentoError}
                onSearchInputChange={setSearchInput}
                onSearch={handleSearch}
                onSelect={(liquidacionId) => setSelectedLiquidacionPreviaId(liquidacionId)}
              />
            ) : !formulario && !isLoadingFormulario ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 space-y-3">
                <p className="text-sm font-medium text-destructive">No se encontró la liquidación previa.</p>
                <Button type="button" variant="outline" size="sm" onClick={() => setSelectedLiquidacionPreviaId(null)}>
                  Intentar con otro código
                </Button>
              </div>
            ) : formulario ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
                <section className="md:col-span-2 rounded-xl border bg-card p-4 space-y-4">
                  <SectionTitle>Datos de liquidación previa</SectionTitle>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Info label="Liquidación previa" value={`${formulario.liquidacion_previa_id.slice(0, 8)}...`} mono />
                    <Info label="Revisión" value={`N° ${numeroRevision}`} />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <Info label="Proyecto" value={formulario.proyecto_public_id} mono />
                    <Info label="Nombre" value={formulario.proyecto_nombre} />
                    <Info label="Valor proyecto" value={formatSoles(formulario.valor_proyecto)} />
                    <Info label="Base de cálculo" value={formatSoles(formulario.valor_base_calculo)} />
                  </div>
                </section>

                <div className="space-y-4 min-w-0">
                  <section className="rounded-xl border bg-card p-4 space-y-4">
                    <SectionTitle>Datos de la nueva revisión</SectionTitle>
                    {/* Hidden tipo_tramite — always OBRA_NUEVA */}
                    <input type="hidden" value={DEFAULT_TIPO_TRAMITE} />
                  </section>

                  <section className="rounded-xl border bg-card p-4 space-y-3">
                    <SectionTitle>Revisión / Tarifa</SectionTitle>
                    <RevisionesVigentesTable
                      revisiones={revisionesVigentes as never[]}
                      selectedId={selectedRevisionIds[0] ?? null}
	                      onSelectRevision={handleRevisionSelect}
                      isLoading={isLoadingFormulario}
                    />
                  </section>

                  <section className="rounded-xl border bg-card p-4 space-y-3">
                    <ContactosSection
                      selectedContactos={selectedContactos}
                      onAddContacto={() => {
                        setEditingContactoIndex(null);
                        setShowContactoModal(true);
                      }}
                      onEditContacto={(index) => {
                        setEditingContactoIndex(index);
                        setShowContactoModal(true);
                      }}
                      onRemoveContacto={(index) => setSelectedContactos((prev) => prev.filter((_, i) => i !== index))}
                    />
                  </section>
                </div>

                <section className="rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm xl:sticky xl:top-4 min-h-[360px]">
                  <CotizacionSection
                    quote={cotizacionQuote}
                    isLoading={cotizacionMutation.isPending}
                    onCotizar={handleCotizar}
                    hasErrors={false}
                    isLoadingData={isLoadingFormulario || isLoadingVariables}
                    variablesFinancieras={variablesFinancieras}
                    isLoadingVariables={isLoadingVariables}
                    valorBaseActual={formulario.valor_base_calculo ?? formulario.valor_proyecto}
                    tarifaSeleccionada={selectedTarifa}
                    revisionLabel={`Revisión #${numeroRevision}`}
                    hideButton
                    compact
                  />
                </section>
              </div>
            ) : null}
          </div>
        )}
      </AppFormModal>

      <ContactoFormModal
        open={showContactoModal}
        onOpenChange={setShowContactoModal}
        onSaved={handleContactoSaved}
        initialData={editingContactoIndex !== null ? selectedContactos[editingContactoIndex] : undefined}
      />

    </>
  );
}

function SearchPreviousLiquidacion({
  searchInput,
  searching,
  searched,
  results,
  total,
  isError,
  onSearchInputChange,
  onSearch,
  onSelect,
}: {
  searchInput: string;
  searching: boolean;
  searched: boolean;
  results: LiquidacionEdificacionOut[];
  total: number;
  isError: boolean;
  onSearchInputChange: (value: string) => void;
  onSearch: () => void;
  onSelect: (liquidacionId: string) => void;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/20 p-6 space-y-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Liquidación previa</p>
        <p className="text-xs text-muted-foreground mt-1">Busca por DNI o RUC de la entidad y selecciona la última revisión del proyecto.</p>
      </div>
      <div className="flex flex-col sm:flex-row gap-2 max-w-md">
        <Input
          placeholder="DNI o RUC"
          value={searchInput}
          onChange={(e) => onSearchInputChange(e.target.value.replace(/\D/g, "").slice(0, 11))}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSearch();
          }}
          inputMode="numeric"
          className="h-10 sm:max-w-[220px]"
        />
        <Button
          type="button"
          onClick={onSearch}
          disabled={searching || (searchInput.trim().length !== 8 && searchInput.trim().length !== 11)}
          className="h-10 gap-2"
        >
          <Search className="h-4 w-4" />
          {searching ? "Buscando..." : "Buscar"}
        </Button>
      </div>
      {isError && (
        <p className="text-sm text-destructive">No se pudo buscar liquidaciones para este documento.</p>
      )}
      {searched && !searching && !isError && results.length === 0 && (
        <p className="text-sm text-muted-foreground">No se encontraron liquidaciones de edificaciones para este documento.</p>
      )}
      {results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Resultados ({total})
          </p>
          <div className="grid gap-2">
            {results.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item.id)}
                className="w-full rounded-lg border border-border bg-card p-3 text-left transition-colors hover:border-primary/50 hover:bg-primary/5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{item.public_id ?? item.proyecto.public_id}</p>
                    <p className="text-xs text-muted-foreground">{item.proyecto.nombre}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-primary">Revisión N° {item.numero_revision}</p>
                    <p className="text-xs text-muted-foreground">{formatSoles(Number(item.proyecto.valor_proyecto))}</p>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>{item.proyecto.public_id}</span>
                  {item.municipalidad.nombre && <span>• {item.municipalidad.nombre}</span>}
                  {item.tipo_tramite && <span>• {item.tipo_tramite.replaceAll("_", " ")}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-2.5 bg-muted/40 border-b rounded-t-xl">
      <FileText className="h-3.5 w-3.5 text-muted-foreground" />
      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{children}</h4>
    </div>
  );
}

function Info({ label, value, mono, accent }: { label: string; value?: ReactNode; mono?: boolean; accent?: boolean }) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className={`text-sm font-medium truncate ${mono ? "font-mono" : ""} ${accent ? "text-emerald-600" : "text-foreground"}`}>
        {value || "—"}
      </span>
    </div>
  );
}
