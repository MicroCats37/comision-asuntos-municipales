"use client";

/**
 * RhBrowseLiquidacionesModal — browse de liquidaciones EXISTENTES del RH.
 *
 * Se abre desde el PASO 2 del wizard RH mensual (Delegado e Inspector) y es
 * SIEMPRE accesible, incluso cuando no hay ninguna candidata: es la salida
 * del usuario cuando el filtro del wizard no arroja resultados.
 *
 * Reglas del contrato (`rh-mensual-browse-edit` / `liquidaciones-browse-listado`):
 * - Es una vista DISTINTA al wizard de nueva revisión: NO importa ni invoca
 *   ninguna mutación de nueva revisión (`useCrearNuevaRevision*`).
 * - El browse NUNCA crea revisiones ni liquidaciones: las mutaciones que
 *   expone son sobre una liquidación CONCRETA y las decide el usuario.
 * - La tarjeta de cada liquidación se renderiza con el componente CENTRALIZADO
 *   `LiquidacionCardShell` (el mismo de las listas de Liquidaciones): el browse
 *   NO dibuja una segunda tarjeta.
 * - Acciones de la tarjeta:
 *   · "Delegados" → abre el `LiquidacionDelegadoDetailModal` DEDICADO (detalle
 *     y edición de las asignaciones de ESA liquidación, con su detalle RH y su
 *     RH mensual enlazado; rechazo 409 en línea). El browse NO implementa su
 *     propia lógica de borrado de delegados.
 *   · "Gestionar comprobante" → abre UN SOLO `ComprobanteFormModal` que
 *     resuelve alta, reemplazo y edición del comprobante vigente. El browse
 *     NO monta dos modales ni expone diálogos de alta y edición por separado.
 *   · "Ver detalle" → detalle de solo lectura (infraestructura existente).
 * - La invalidación del listado del browse es EXPLÍCITA: los hooks de mutación
 *   invalidan `["rh-browse","liquidaciones", endpoint]`. El browse NO se
 *   suscribe al `mutationCache`. Los flujos de COMPROBANTE, en cambio, terminan
 *   en un `refetch()` EXPLÍCITO del listado: su hook sólo parchea las caches
 *   de liquidaciones, no el query del browse.
 * - Usa el MISMO panel de filtros y el MISMO contrato que las listas de
 *   Liquidaciones: `LiquidacionFiltroModal` + `LiquidacionFiltros`. El browse
 *   NO tiene panel de filtros propio.
 * - Los filtros del wizard RH sólo SEMILLAN los filtros de Liquidaciones
 *   (valores compatibles). No limitan la búsqueda más allá de los filtros
 *   de Liquidaciones que el usuario tenga activos.
 * - NO hay filtro municipal IMPLÍCITO: la municipalidad de la operatividad es
 *   contexto informativo; sólo viaja `entidad_id` si el usuario lo elige en el
 *   panel de filtros.
 * - Los filtros que el endpoint activo no soporta se OMITEN de forma
 *   explícita (se avisa al usuario; nunca se envían vacíos).
 * - Reutiliza la infraestructura de detalle existente (`LiquidacionDetalleModal`
 *   + `useLiquidacionGeneralDetalle`).
 */
import { AlertCircle, Eye, Filter, List, Loader2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Pagination } from "@/components/genericPagination/Pagination";
import { ActiveFiltersPanel, type FilterEntry } from "@/components/ui/active-filters";
import { Button } from "@/components/ui/button";
import {
  buildRhBrowseSemillaFiltros,
  fusionarFiltrosLiquidacion,
  RH_BROWSE_ETIQUETA_FILTRO,
  type RhBrowseFiltrosSemilla,
  useRhBrowseLiquidaciones,
} from "@/features/finanzas/hooks/useRhBrowseLiquidaciones";
import { LiquidacionCardShell } from "@/features/liquidaciones/components/cards/LiquidacionCardShell";
import {
  composeDetalleSections,
  getTipoDetalleSection,
  LiquidacionDetalleModal,
} from "@/features/liquidaciones/components/detail";
import {
  ComprobanteFormModal,
  LiquidacionFiltroModal,
} from "@/features/liquidaciones/components/forms";
import { LiquidacionDelegadoDetailModal } from "@/features/liquidaciones/components/LiquidacionDelegadoDetailModal";
import { useDistritos } from "@/features/liquidaciones/hooks/useDistritos";
import { useLiquidacionGeneralDetalle } from "@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle";
import type { LiquidacionFiltros } from "@/features/liquidaciones/hooks/useLiquidacionList";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import {
  formatPublicId,
  getTipoSlugFromCodigo,
} from "@/features/liquidaciones/utils/formatPublicId";
import { getLiquidacionTipoInfo } from "@/features/liquidaciones/utils/liquidacionTipoInfo";

export interface RhBrowseLiquidacionesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Código de tipo conocido por el wizard (null/undefined → listado cross-tipo). */
  tipoCodigo?: string | null;
  /** Filtros del wizard RH: sólo SEMILLAN los filtros de Liquidaciones. */
  filtros?: RhBrowseFiltrosSemilla;
  /** Rango de fechas heredado del wizard (YYYY-MM-DD). */
  fechaDesde?: string;
  fechaHasta?: string;
  /** Nombre de la municipalidad del wizard (sólo informativo). */
  municipalidadNombre?: string | null;
}

/**
 * ID público de la liquidación — MISMO formato que las listas de Liquidaciones
 * (`formatPublicId` con el slug del tipo: EDIF-2026-000088).
 *
 * Se usa el slug y no el código para que la tarjeta del browse sea idéntica
 * a la de las vistas por tipo (homogeneidad de la jerarquía).
 */
function publicIdDeLiquidacion(
  tipoCodigo: string | null | undefined,
  fechaRegistro: string | null | undefined,
  numero: number | null | undefined,
): string {
  const slug = getTipoSlugFromCodigo(tipoCodigo) ?? "liquidacion";
  return formatPublicId(slug, fechaRegistro ?? null, numero ?? null);
}

export function RhBrowseLiquidacionesModal({
  open,
  onOpenChange,
  tipoCodigo,
  filtros: filtrosHeredados,
  fechaDesde: fechaDesdeHeredada,
  fechaHasta: fechaHastaHeredada,
  municipalidadNombre,
}: RhBrowseLiquidacionesModalProps) {
  /**
   * Filtros ACTIVOS del browse: contrato `LiquidacionFiltros` (el mismo de
   * las listas de Liquidaciones). Los del wizard sólo los siembran.
   */
  const [filtros, setFiltros] = useState<LiquidacionFiltros>(() =>
    buildRhBrowseSemillaFiltros({
      filtros: filtrosHeredados,
      fechaDesde: fechaDesdeHeredada,
      fechaHasta: fechaHastaHeredada,
    }),
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [detalleId, setDetalleId] = useState<string | null>(null);

  /**
   * Id de la liquidación OBJETIVO de la acción "Gestionar comprobante".
   *
   * La acción apunta siempre a una `LiquidacionGeneral` concreta (la de la
   * tarjeta donde el usuario la dispara): no hay ambigüedad de destino y NUNCA
   * se crea una revisión.
   *
   * Es el ÚNICO estado de selección del flujo de comprobante: el browse monta
   * UN SOLO `ComprobanteFormModal`, que resuelve el alta, el reemplazo y la
   * edición del comprobante vigente.
   */
  const [comprobanteId, setComprobanteId] = useState<string | null>(null);

  /**
   * Id de la liquidación OBJETIVO de la acción "Delegados".
   *
   * El browse NO implementa la lógica de borrado: abre el
   * `LiquidacionDelegadoDetailModal` DEDICADO con el contexto crudo de la fila
   * (`raw.liquidacion_general`) y con el endpoint activo del browse (para que
   * el hook de mutación pueda invalidar este listado).
   */
  const [delegadosId, setDelegadosId] = useState<string | null>(null);

  const { data: municipalidades } = useMunicipalidades();
  const { data: distritos } = useDistritos();

  /**
   * Al (re)abrir el browse se adoptan los filtros heredados del wizard.
   * El guard evita que un re-render del wizard (mientras el browse está
   * abierto) pise lo que el usuario ya ajustó dentro del modal.
   */
  const wasOpenRef = useRef(false);
  useEffect(() => {
    if (!open) {
      // Prevent reopening with a stale out-of-range page after filters change.
      setPage(1);
      wasOpenRef.current = false;
      return;
    }
    if (open && !wasOpenRef.current) {
      setFiltros(
        buildRhBrowseSemillaFiltros({
          filtros: filtrosHeredados,
          fechaDesde: fechaDesdeHeredada,
          fechaHasta: fechaHastaHeredada,
        }),
      );
      setPage(1);
    }
    wasOpenRef.current = open;
  }, [open, filtrosHeredados, fechaDesdeHeredada, fechaHastaHeredada]);

  const {
    items,
    total,
    totalPages,
    isLoading,
    isError,
    omitidos,
    refetch,
    endpoint,
  } = useRhBrowseLiquidaciones({
    tipoCodigo,
    filtros,
    page,
    pageSize,
    enabled: open,
  });

  const { data: detalleData, isLoading: isLoadingDetalle } =
    useLiquidacionGeneralDetalle({ id: detalleId });

  /**
   * Detalle de la liquidación objetivo del flujo de comprobante.
   *
   * Es la fuente de verdad del historial (`comprobantes[]`) y del comprobante
   * vigente: el listado se usa como fallback inmediato mientras la petición
   * viaja.
   */
  const { data: comprobanteData } = useLiquidacionGeneralDetalle({
    id: comprobanteId,
  });

  /*
   * El browse NO se suscribe al `mutationCache`.
   *
   * Antes tenía que hacerlo porque el modal GENÉRICO de gestión de delegados
   * que abría no expone `onSuccess` y el browse se alimentaba de SU payload
   * (`delegados[]`), de modo que el delegado quitado seguía vivo en la caché
   * del browse.
   *
   * Ahora el browse abre el `LiquidacionDelegadoDetailModal` DEDICADO, que
   * lee SUS PROPIAS asignaciones (`GET /{id}/delegados-asignaciones`) y usa el
   * hook de remoción EXISTENTE: la invalidación del listado del browse es
   * ahora EXPLÍCITA (`["rh-browse","liquidaciones", endpoint]`) y determinista.
   */

  const detalleTipoCodigo =
    detalleData?.liquidacion_general.tipo_liquidacion?.codigo ?? null;

  /** Aplica los filtros del panel de Liquidaciones y vuelve a la página 1. */
  const handleApplyFiltros = (next: LiquidacionFiltros) => {
    setFiltros((prev) => fusionarFiltrosLiquidacion(prev, next));
    setPage(1);
    setFilterModalOpen(false);
  };

  /** Limpia TODOS los filtros activos y vuelve a la página 1. */
  const handleClearFiltros = () => {
    setFiltros({});
    setPage(1);
  };

  /** Quita un único filtro activo y vuelve a la página 1. */
  const handleRemoveFiltro = (key: keyof LiquidacionFiltros) => {
    setFiltros((prev) => {
      const next = { ...(prev ?? {}) };
      delete next[key];
      return next;
    });
    setPage(1);
  };

  /**
   * Chips de filtros activos (mismo panel que las listas de Liquidaciones).
   *
   * `entidad_id` y `distrito_id` se muestran con su nombre: sin el, el chip
   * mostraría un UUID.
   */
  const activeFilterEntries: FilterEntry<keyof LiquidacionFiltros>[] =
    useMemo(() => {
      const entries: FilterEntry<keyof LiquidacionFiltros>[] = [];

      if (filtros.entidad_id) {
        entries.push({
          key: "entidad_id",
          label: RH_BROWSE_ETIQUETA_FILTRO.entidad_id,
          value:
            municipalidades?.find((m) => m.id === filtros.entidad_id)?.nombre ??
            filtros.entidad_id,
        });
      }
      if (filtros.distrito_id) {
        entries.push({
          key: "distrito_id",
          label: RH_BROWSE_ETIQUETA_FILTRO.distrito_id,
          value:
            distritos?.find((d) => d.id === filtros.distrito_id)?.nombre ??
            filtros.distrito_id,
        });
      }
      if (filtros.propietario) {
        entries.push({
          key: "propietario",
          label: RH_BROWSE_ETIQUETA_FILTRO.propietario,
          value: filtros.propietario,
        });
      }
      if (filtros.razon_social) {
        entries.push({
          key: "razon_social",
          label: RH_BROWSE_ETIQUETA_FILTRO.razon_social,
          value: filtros.razon_social,
        });
      }
      if (filtros.direccion) {
        entries.push({
          key: "direccion",
          label: RH_BROWSE_ETIQUETA_FILTRO.direccion,
          value: filtros.direccion,
        });
      }
      if (filtros.documento) {
        entries.push({
          key: "documento",
          label: RH_BROWSE_ETIQUETA_FILTRO.documento,
          value: filtros.documento,
        });
      }
      if (filtros.expediente) {
        entries.push({
          key: "expediente",
          label: RH_BROWSE_ETIQUETA_FILTRO.expediente,
          value: filtros.expediente,
        });
      }
      if (filtros.fecha_desde) {
        entries.push({
          key: "fecha_desde",
          label: RH_BROWSE_ETIQUETA_FILTRO.fecha_desde,
          value: filtros.fecha_desde,
        });
      }
      if (filtros.fecha_hasta) {
        entries.push({
          key: "fecha_hasta",
          label: RH_BROWSE_ETIQUETA_FILTRO.fecha_hasta,
          value: filtros.fecha_hasta,
        });
      }
      if (filtros.numero != null) {
        entries.push({
          key: "numero",
          label: RH_BROWSE_ETIQUETA_FILTRO.numero,
          value: String(filtros.numero),
        });
      }
      if (filtros.comprobante_serie) {
        entries.push({
          key: "comprobante_serie",
          label: RH_BROWSE_ETIQUETA_FILTRO.comprobante_serie,
          value: filtros.comprobante_serie,
        });
      }
      if (filtros.comprobante_numero) {
        entries.push({
          key: "comprobante_numero",
          label: RH_BROWSE_ETIQUETA_FILTRO.comprobante_numero,
          value: filtros.comprobante_numero,
        });
      }

      return entries;
    }, [filtros, municipalidades, distritos]);

  const detalleItem = items.find((item) => item.id === detalleId) ?? null;

  /** Item del listado que es objetivo de la acción de comprobante. */
  const comprobanteItem =
    items.find((item) => item.id === comprobanteId) ?? null;

  /** Item del listado que es objetivo de la acción de delegados. */
  const delegadosItem =
    items.find((item) => item.id === delegadosId) ?? null;

  /**
   * Liquidación sobre la que se abre el flujo de comprobante.
   *
   * Prioriza el detalle (historial completo de comprobantes y comprobante
   * vigente) y cae al payload del listado mientras el detalle está en vuelo.
   */
  const comprobanteLiquidacion =
    comprobanteData?.liquidacion_general ??
    comprobanteItem?.raw.liquidacion_general ??
    null;

  return (
    <>
      <GenericModal open={open} onOpenChange={onOpenChange}>
        <GenericModal.Content size="xl" className="max-w-6xl">
          {/* ── Header (mismo chrome que el flujo de nueva revisión) ── */}
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <List className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Recibos de Honorario
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                  Liquidaciones existentes
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  Consulta las liquidaciones ya registradas con los filtros de
                  Liquidaciones. Desde aquí puedes gestionar los delegados y
                  registrar, reemplazar o editar el comprobante vigente. El
                  browse nunca crea revisiones.
                </p>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-warning">
                  <Eye className="h-3.5 w-3.5" />
                  Existentes
                </span>
              </div>
            </div>
          </GenericModal.Header>

          {/* ── Body ── */}
          <GenericModal.Body className="px-6 py-5 sm:px-8">
            <div className="space-y-4">
              {/* Filtros de Liquidaciones: limpiables y editables */}
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setFilterModalOpen(true)}
                  className="h-8 px-3 text-xs rounded-lg gap-1.5 border-primary/30 text-primary hover:bg-primary/5"
                >
                  <Filter className="h-3.5 w-3.5" />
                  Filtros
                  {activeFilterEntries.length > 0 && (
                    <span className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                      {activeFilterEntries.length}
                    </span>
                  )}
                </Button>
              </div>

              <ActiveFiltersPanel
                entries={activeFilterEntries}
                onRemove={handleRemoveFiltro}
                onClearAll={handleClearFiltros}
              />

              {municipalidadNombre && (
                <p className="text-xs text-muted-foreground">
                  Municipalidad de la operatividad (contexto, no aplica filtro):{" "}
                  <span className="font-bold text-foreground">
                    {municipalidadNombre}
                  </span>
                </p>
              )}

              {/* Omisión explícita de filtros no soportados por el endpoint */}
              {omitidos.length > 0 && (
                <div
                  role="note"
                  className="flex items-start gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-xs text-amber-700 dark:text-amber-300"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>
                    Este listado no admite{" "}
                    <span className="font-bold">
                      {omitidos
                        .map((omitido) => RH_BROWSE_ETIQUETA_FILTRO[omitido.filtro])
                        .join(", ")}
                    </span>
                    . Se han omitido para no alterar el resultado.
                  </span>
                </div>
              )}

              {/* Listado */}
              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : isError ? (
                <div className="flex flex-col items-center justify-center p-8 text-destructive text-sm">
                  Error al cargar las liquidaciones existentes
                </div>
              ) : items.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-10 text-center text-sm text-muted-foreground">
                  No hay liquidaciones que coincidan con los filtros aplicados.
                </div>
              ) : (
                <div className="space-y-3">
                  {items.map((item) => {
                    const lg = item.raw.liquidacion_general;
                    const tipoInfo = getLiquidacionTipoInfo(item.tipoCodigo);
                    const comprobanteActivo =
                      lg.comprobantes.find((comprobante) => comprobante.activo) ??
                      null;
                    const entidad = lg.proyecto?.entidad ?? null;
                    const distritoNombre =
                      lg.proyecto?.distrito?.nombre ?? null;

                    return (
                      <LiquidacionCardShell
                        key={item.id}
                        kindIcon={tipoInfo.icon}
                        kindLabel={tipoInfo.label}
                        publicId={publicIdDeLiquidacion(
                          item.tipoCodigo,
                          item.fechaRegistro,
                          item.numero,
                        )}
                        estado={item.estado}
                        entidadNombre={
                          entidad?.razon_social ??
                          lg.proyecto?.nombre_propietario ??
                          "—"
                        }
                        entidadDocumento={
                          entidad
                            ? `${entidad.tipo_documento} ${entidad.numero_documento}`
                            : null
                        }
                        proyectoNombre={
                          lg.denominacion_de_proyecto ??
                          lg.proyecto?.nombre_propietario ??
                          null
                        }
                        proyectoUbicacion={
                          distritoNombre ?? lg.proyecto?.urbanizacion ?? null
                        }
                        municipalidadLabel={lg.municipalidad?.nombre ?? "—"}
                        distritoLabel={distritoNombre ?? undefined}
                        expediente={lg.expediente ?? null}
                        direccion={lg.proyecto?.direccion ?? null}
                        comprobanteActivo={comprobanteActivo}
                        total={item.total}
                        subTotal={item.subTotal}
                        igvMonto={
                          item.total != null && item.subTotal != null
                            ? item.total - item.subTotal
                            : null
                        }
                        fechaRegistro={item.fechaRegistro}
                        numeroRevision={item.numeroRevision}
                        showDelegados
                        onDelegados={() => setDelegadosId(item.id)}
                        onComprobante={() => setComprobanteId(item.id)}
                        etiquetaComprobante="Gestionar comprobante"
                        onVerDetalle={() => setDetalleId(item.id)}
                      />
                    );
                  })}
                </div>
              )}

              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setPage(1);
                }}
                totalItems={total}
                pageSize={pageSize}
              />
            </div>
          </GenericModal.Body>

          {/* ── Footer ── */}
          <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="h-10 sm:h-11 rounded-xl font-semibold border-border/60 hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
            >
              Cerrar
            </Button>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      {/* Editor de filtros (panel de Liquidaciones, reutilizado literalmente) */}
      <LiquidacionFiltroModal
        open={filterModalOpen}
        onOpenChange={setFilterModalOpen}
        initialFiltros={filtros}
        onApply={handleApplyFiltros}
      />

      {/* Detalle de solo lectura (infraestructura existente) */}
      {detalleId && (
        <LiquidacionDetalleModal
          open
          onOpenChange={(nextOpen) => {
            if (!nextOpen) setDetalleId(null);
          }}
          kindBadge={
            getLiquidacionTipoInfo(
              detalleItem?.tipoCodigo ?? detalleTipoCodigo,
            ).label
          }
          publicId={
            detalleData
              ? publicIdDeLiquidacion(
                  detalleItem?.tipoCodigo ?? detalleTipoCodigo,
                  detalleData.liquidacion_general.fecha_registro,
                  detalleData.liquidacion_especifica?.numero ?? null,
                )
              : (detalleItem?.expediente ?? "—")
          }
          estado={detalleData?.liquidacion_general.estado}
          kindIcon={getLiquidacionTipoInfo(detalleItem?.tipoCodigo ?? null).icon}
        >
          {isLoadingDetalle ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : detalleData ? (
            composeDetalleSections({
              lg: detalleData.liquidacion_general,
              lt:
                detalleTipoCodigo === "EDIFICACION" ||
                detalleTipoCodigo === "TALUDES" ||
                detalleTipoCodigo === "IMPACTO_VIAL"
                  ? (detalleData.liquidacion_tipo as PorcentajeObraDatosOut)
                  : null,
              tipoSection: getTipoDetalleSection(
                detalleTipoCodigo,
                detalleData.liquidacion_tipo,
                detalleData.liquidacion_general.uit?.valor,
              ),
              showDelegados: detalleTipoCodigo !== "INSPECCION_OBRA",
            })
          ) : (
            <div className="p-4 text-sm text-muted-foreground">
              No se pudo cargar el detalle
            </div>
          )}
        </LiquidacionDetalleModal>
      )}

      {/* ── Flujo ÚNICO de comprobante (alta, reemplazo o edición) ── */}
      {comprobanteId && comprobanteLiquidacion && (
        <ComprobanteFormModal
          open
          onOpenChange={(nextOpen) => {
            if (!nextOpen) setComprobanteId(null);
          }}
          liquidacionGeneral={comprobanteLiquidacion}
          onSuccess={() => {
            setComprobanteId(null);
            // Refetch EXPLÍCITO del listado: el browse NO se parchea con la
            // caché de liquidaciones (su clave `["rh-browse", …]` queda fuera
            // del prefijo `["liquidaciones"]`), así que el listado tiene que
            // releerse. Sin esto, el comprobante vigente de la fila no se
            // actualiza.
            void refetch();
          }}
        />
      )}

      {/* ── Detalle DEDICADO de asignaciones de delegado ── */}
      {delegadosItem && (
        <LiquidacionDelegadoDetailModal
          open
          onOpenChange={(nextOpen) => {
            if (!nextOpen) setDelegadosId(null);
          }}
          liquidacionGeneral={delegadosItem.raw.liquidacion_general}
          publicId={publicIdDeLiquidacion(
            delegadosItem.tipoCodigo,
            delegadosItem.fechaRegistro,
            delegadosItem.numero,
          )}
          rhBrowseEndpoint={endpoint}
        />
      )}
    </>
  );
}
