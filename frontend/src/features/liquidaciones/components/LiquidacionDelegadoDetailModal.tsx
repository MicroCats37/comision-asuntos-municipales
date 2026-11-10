"use client";

import { Loader2, UserMinus, Users } from "lucide-react";
import { useState } from "react";
import { ModalShell } from "@/components-app/forms/ModalShell";
import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";
import { handleApiError } from "@/errors";
import { useLiquidacionDelegadosDetalle } from "../hooks/useLiquidacionDelegadosDetalle";
import { useQuitarDelegadoLiquidacion } from "../hooks/useQuitarDelegadoLiquidacion";
import type { LiquidacionGeneralOutput } from "../schemas/liquidacion-base.schema";
import type { LiquidacionDelegadoDetalle } from "../schemas/liquidacion-delegado-detalle.schema";
import { getLiquidacionTipoInfo } from "../utils/liquidacionTipoInfo";
import { LiquidacionCardShell } from "./cards/LiquidacionCardShell";
import { DelegadoAsignacionFila } from "./DelegadoAsignacionFila";

/**
 * LiquidacionDelegadoDetailModal — modal DEDICADO de detalle de las
 * asignaciones de delegado de UNA liquidación.
 *
 * Es un componente DISTINTO del modal genérico de gestión de delegados
 * (`GestionarDelegadosModal`), que sigue en su sitio y sirve a las 6 vistas
 * por tipo. Este modal existe porque el payload genérico
 * (`LiquidacionGeneralOutput.delegados[]`) NO expone el id de la asignación,
 * ni `numero_rh`, ni el detalle RH, ni el RH mensual enlazado.
 *
 * PRESENTACIÓN DE SOLO LECTURA: el cuerpo es una TABLA compacta con una fila
 * por asignación. No hay campos editables, ni acciones de guardado, ni UI de
 * edición de la asignación. La edición NO se ofrece desde aquí.
 *
 * Datos: `GET /liquidaciones/{id}/delegados-asignaciones` (hook existente).
 * Remoción: `PATCH /liquidaciones/{id}/delegados` rama `delete` (hook
 * EXISTENTE `useQuitarDelegadoLiquidacion`). NO hay un segundo camino de
 * remoción: se reutiliza el endpoint y la guarda existentes.
 *
 * Granularidad (DD7): la fila es la granularidad de la LECTURA; la remoción
  * es de alcance DELEGADO (la guarda agrupa todas las filas de
  * `(liquidacion, delegado)`). Por eso se renderiza EXACTAMENTE UNA acción de
  * remoción por delegado, en una columna propia combinada con `rowSpan`:
 * un botón por fila mentiría sobre el comportamiento real del backend.
 *
 * Confirmación: la remoción pide confirmación con el componente COMPARTIDO
 * `useConfirmationDialog` (el MISMO patrón que usa la eliminación del RH
 * mensual en `RecibosDelegadosView`). Cancelar no cambia nada; confirmar
 * ejecuta el hook de remoción existente.
 *
 * Cabecera (DD8): se reutiliza `LiquidacionCardShell` — el mismo componente
 * que usa el browse de RH — para no duplicar el lenguaje visual.
 */

/** Un grupo de asignaciones de UN MISMO delegado. */
type GrupoDelegado = {
  delegatedId: string;
  nombre: string;
  cip: string | null;
  asignaciones: LiquidacionDelegadoDetalle[];
};

/**
 * Agrupa las asignaciones por delegado.
 *
 * La clave es `delegado_id` (no el nombre): el mismo delegado puede tener
 * VARIAS asignaciones (una por `especialidad_revision`) y todas comparten
 * una única acción de remoción.
 */
function agruparPorDelegado(
  asignaciones: LiquidacionDelegadoDetalle[],
): GrupoDelegado[] {
  const grupos = new Map<string, GrupoDelegado>();

  for (const asignacion of asignaciones) {
    const existente = grupos.get(asignacion.delegado_id);
    if (existente) {
      existente.asignaciones.push(asignacion);
      continue;
    }
    grupos.set(asignacion.delegado_id, {
      delegatedId: asignacion.delegado_id,
      nombre: asignacion.delegado?.nombre_completo ?? "Delegado",
      cip: asignacion.delegado?.cip ?? null,
      asignaciones: [asignacion],
    });
  }

  return Array.from(grupos.values());
}

interface LiquidacionDelegadoDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** La liquidación cuyo detalle de delegados se muestra. */
  liquidacionGeneral: LiquidacionGeneralOutput;
  /** Identificador público calculado por la card padre del browse. */
  publicId: string;
  /**
   * Endpoint activo del browse de RH.
   *
   * Se propaga al hook de remoción (para invalidar el listado del browse
   * cuando se quita un delegado): la tarjeta del browse puede llevar el
   * dato quitado.
   */
  rhBrowseEndpoint?: string | null;
}

export function LiquidacionDelegadoDetailModal({
  open,
  onOpenChange,
  liquidacionGeneral,
  publicId,
  rhBrowseEndpoint,
}: LiquidacionDelegadoDetailModalProps) {
  const liquidacionId = liquidacionGeneral.id;

  // Sólo se consulta mientras el modal está abierto.
  const { data, isLoading, isError } = useLiquidacionDelegadosDetalle(
    liquidacionId,
    { enabled: open },
  );

  /**
   * Confirmación COMPARTIDA — el mismo componente que usa el borrado del RH
   * mensual (`useConfirmationDialog`): no hay un diseño de confirmación
   * propio en este modal.
   */
  const { confirm, Dialog } = useConfirmationDialog();

  // Estado POR GRUPO de la acción "Quitar delegado".
  const [quitarPendientes, setQuitarPendientes] = useState<string[]>([]);
  const [quitarErrores, setQuitarErrores] = useState<Record<string, string>>(
    {},
  );
  // Delegados ya quitados con éxito: se ocultan aunque el snapshot que
  // llega por la query todavía los contenga (el refetch es asíncrono).
  const [delegadosRemovidos, setDelegadosRemovidos] = useState<string[]>([]);

  /**
   * Remoción: el hook EXISTENTE de remoción (mismo endpoint, misma guarda).
   *
   * `rhBrowseEndpoint` se propaga para que la remoción también invalide el
   * listado del browse: sin esto, la tarjeta del browse conservaría el
   * delegado quitado.
   */
  const quitarDelegado = useQuitarDelegadoLiquidacion(liquidacionId, {
    rhBrowseEndpoint,
  });

  const asignaciones = (data?.asignaciones ?? []).filter(
    (asignacion) => !delegadosRemovidos.includes(asignacion.delegado_id),
  );
  const grupos = agruparPorDelegado(asignaciones);

  /**
   * Quita UN delegado — de alcance DELEGADO.
   *
   * 1. Primero se pide CONFIRMACIÓN (componente compartido). Cancelar no
   *    lanza ninguna petición y no cambia nada.
   * 2. Confirmado, emite exactamente un PATCH con un único item en `delete`
   *    (la guarda existente decide si puede: con RH mensual enlazado responde
   *    409). Sólo tras un 2xx el grupo se considera quitado; un rechazo se
   *    muestra EN el grupo y el grupo permanece visible con todas sus filas.
   */
  const handleQuitarDelegado = async (grupo: GrupoDelegado) => {
    const confirmado = await confirm({
      title: "Quitar delegado de la liquidación",
      description: `¿Estás seguro de que deseas quitar al delegado ${grupo.nombre}? Se quitarán TODAS sus asignaciones (${grupo.asignaciones.length}). Esta acción no se puede deshacer.`,
      confirmLabel: "Quitar delegado",
      cancelLabel: "Cancelar",
      variant: "danger",
    });

    // Cancelar → NO se emite ninguna petición y NO cambia nada.
    if (!confirmado) return;

    setQuitarPendientes((prev) => [...prev, grupo.delegatedId]);
    setQuitarErrores((prev) => {
      const next = { ...prev };
      delete next[grupo.delegatedId];
      return next;
    });

    try {
      await quitarDelegado.quitar({ delegado_id: grupo.delegatedId });
      setDelegadosRemovidos((prev) =>
        prev.includes(grupo.delegatedId) ? prev : [...prev, grupo.delegatedId],
      );
    } catch (error) {
      // El rechazo (409) NO cambia el estado: las filas siguen visibles.
      setQuitarErrores((prev) => ({
        ...prev,
        [grupo.delegatedId]: handleApiError(error).message,
      }));
    } finally {
      setQuitarPendientes((prev) => prev.filter((id) => id !== grupo.delegatedId));
    }
  };

  // ── Cabecera: la MISMA tarjeta del browse (DD8) ──
  const tipoInfo = getLiquidacionTipoInfo(
    liquidacionGeneral.tipo_liquidacion?.codigo,
  );
  const proyecto = liquidacionGeneral.proyecto;
  const entidad = proyecto?.entidad ?? null;
  const distritoNombre = proyecto?.distrito?.nombre ?? null;
  const comprobanteActivo =
    liquidacionGeneral.comprobantes.find((comprobante) => comprobante.activo) ??
    null;
  const total = liquidacionGeneral.total;
  const subTotal = liquidacionGeneral.sub_total;

  return (
    <>
      <ModalShell
        open={open}
        onOpenChange={onOpenChange}
        title="Asignaciones de delegados"
        description="Consulta las asignaciones y su detalle RH. La información se muestra solo para lectura."
        eyebrow="Liquidación"
        icon={<Users className="h-5 w-5 text-primary" />}
        primaryLabel="Cerrar"
        primaryLoadingLabel="Cerrando..."
        primaryLoading={false}
        onPrimary={() => onOpenChange(false)}
        preventClose
        size="xl"
      >
        <div className="space-y-4">
          <LiquidacionCardShell
            kindIcon={tipoInfo.icon}
            kindLabel={tipoInfo.label}
            publicId={publicId}
            estado={liquidacionGeneral.estado}
            entidadNombre={
              entidad?.razon_social ?? proyecto?.nombre_propietario ?? "—"
            }
            entidadDocumento={
              entidad
                ? `${entidad.tipo_documento} ${entidad.numero_documento}`
                : null
            }
            proyectoNombre={
              liquidacionGeneral.denominacion_de_proyecto ??
              proyecto?.nombre_propietario ??
              null
            }
            proyectoUbicacion={
              distritoNombre ?? proyecto?.urbanizacion ?? null
            }
            municipalidadLabel={liquidacionGeneral.municipalidad?.nombre ?? "—"}
            distritoLabel={distritoNombre ?? undefined}
            expediente={liquidacionGeneral.expediente ?? null}
            direccion={proyecto?.direccion ?? null}
            comprobanteActivo={comprobanteActivo}
            total={total}
            subTotal={subTotal}
            igvMonto={
              liquidacionGeneral.igv?.valor ??
              (total != null && subTotal != null ? total - subTotal : null)
            }
            fechaRegistro={liquidacionGeneral.fecha_registro}
            numeroRevision={liquidacionGeneral.numero_revision}
            showDelegados={false}
          />

          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                Cargando asignaciones de delegados...
              </p>
            </div>
          ) : isError ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-center text-sm text-destructive">
              Error al cargar las asignaciones de delegados.
            </div>
          ) : grupos.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-10 text-center text-sm text-muted-foreground">
              Esta liquidación no tiene delegados asignados.
            </div>
          ) : (
            <div className="max-w-full overflow-x-auto rounded-xl border border-border/60">
              <table className="min-w-[1540px] w-full border-collapse text-left">
                <caption className="sr-only">
                  Asignaciones de delegados de la liquidación, con su detalle RH
                  y el RH mensual enlazado.
                </caption>
                <thead>
                  <tr className="border-b border-border/60 bg-muted/30 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                    <th scope="col" className="px-3 py-2.5">
                      Delegado
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Especialidad
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Tipo
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Período
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Mes
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Dictamen
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      N.º RH
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      F. presentación
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      F. revisión
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Importe bruto
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Neto honorario
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Renta CIP
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Aporte CODEMU
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Fondo común
                    </th>
                    <th scope="col" className="px-3 py-2.5">
                      Tipo de registro
                    </th>
                    <th scope="col" className="px-3 py-2.5 text-right">
                      Acciones
                    </th>
                  </tr>
                </thead>
                {grupos.map((grupo) => {
                  const quitando = quitarPendientes.includes(grupo.delegatedId);
                  const errorQuitar = quitarErrores[grupo.delegatedId];

                  return (
                    <tbody key={grupo.delegatedId}>
                      {grupo.asignaciones.map((asignacion, indice) => (
                        <DelegadoAsignacionFila
                          key={asignacion.id}
                          asignacion={asignacion}
                          esPrimeraFilaDelGrupo={indice === 0}
                          delegado={{
                            nombre: grupo.nombre,
                            cip: grupo.cip,
                            totalAsignaciones: grupo.asignaciones.length,
                          }}
                          accion={
                            indice === 0 ? (
                              <div className="flex flex-col items-start gap-1.5">
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="sm"
                                  disabled={quitando}
                                  aria-label={`Quitar delegado: ${grupo.nombre}`}
                                  onClick={() => handleQuitarDelegado(grupo)}
                                >
                                  {quitando ? (
                                    <>
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                      Quitando...
                                    </>
                                  ) : (
                                    <>
                                      <UserMinus className="h-3.5 w-3.5" />
                                      Quitar delegado
                                    </>
                                  )}
                                </Button>
                                {errorQuitar && (
                                  <p
                                    role="alert"
                                    className="text-[11px] text-destructive"
                                  >
                                    {errorQuitar}
                                  </p>
                                )}
                              </div>
                            ) : undefined
                          }
                        />
                      ))}
                    </tbody>
                  );
                })}
              </table>
            </div>
          )}
        </div>
      </ModalShell>

      {/* Confirmación compartida (mismo patrón que el borrado del RH mensual). */}
      {Dialog}
    </>
  );
}
