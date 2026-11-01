/**
 * Utilidades del modo EDICIÓN de los RH mensuales (delegado e inspector).
 *
 * Estas funciones son puras: reciben el item del listado de RH (o el detalle
 * flat ya resuelto) y devuelven la selección inicial del wizard. Viven fuera
 * de los modales para poder verificarlas sin renderizar el wizard completo.
 */

import type {
  DetalleDelegadoRow,
  ReciboHonorarioDelegadoMensual,
  ReciboHonorarioInspectorMensual,
} from "../schemas/recibo-honorario.schema";
import type {
  DelegadoSelectionEntry,
  InspectorSelectionEntry,
} from "../stores/rh-selection.store";

/**
 * Operatividad vigente del RH reconstruida desde el contexto del listado.
 * Permite que el modo edición consulte candidatas y cotizar sin que el usuario
 * vuelva a elegir el periodo vigente del delegado.
 */
export function buildDelegadoEditOperacionSelection(
  rh: ReciboHonorarioDelegadoMensual,
): {
  id: string;
  municipalidad_id: string;
  municipalidad_nombre: string;
  tipo_liquidacion_id: string | null;
  tipo_liquidacion_codigo: string | null;
  tipo_liquidacion_nombre: string | null;
  especialidad_id: string;
  especialidad_nombre: string;
  tipo: string;
} | null {
  const ctx = rh.delegado_operacion_context;
  if (!ctx) return null;
  return {
    id: ctx.id,
    municipalidad_id: ctx.municipalidad_id,
    municipalidad_nombre: ctx.municipalidad_nombre,
    tipo_liquidacion_id: ctx.tipo_liquidacion_id ?? null,
    tipo_liquidacion_codigo: ctx.tipo_liquidacion_codigo ?? null,
    tipo_liquidacion_nombre: ctx.tipo_liquidacion_nombre ?? null,
    especialidad_id: ctx.especialidad_id,
    especialidad_nombre: ctx.especialidad_nombre,
    tipo: ctx.tipo,
  };
}

/**
 * Detalle persistido que NO se pudo resolver (o que no se puede conserving).
 *
 * Se devuelve para poder MOSTRARLO en el wizard (no se descartan en
 * silencio): el guardado queda bloqueado mientras existan filas sin resolver,
 * porque el conjunto final del payload ES el conjunto de filas del recibo.
 */
export interface RHUnresolvedDetail {
  detalle_id: string | null;
  expediente: string | null;
  numero_rh: string | null;
}

/**
 * Construye la selección inicial del modo edición (delegado) a partir de los
 * detalles persistidos del RH.
 *
 * Cada detalle persistido se resuelve contra el listado flat de detalle para
 * obtener los identificadores que el PATCH necesita para CONSERVAR la fila
 * (`liquidacion_general_id` + `especialidad_revision_id`). La metadata por item
 * (n° RH, periodo, mes, dictamen y fechas) se toma del detalle persistido: es
 * metadata compartida de la asignación y el PATCH la rechaza con 409 si se
 * intenta modificar.
 *
 * Los detalles que no se pueden resolver se cuentan como `unresolved` y se
 * devuelven en `unresolvedDetails` para poder mostrarlos: en ese caso el
 * PATCH NO se debe enviar, porque el conjunto final del payload es el
 * conjunto de filas del recibo y un detalle no incluido sería retirado.
 */
export function buildDelegadoEditSelection(
  rh: ReciboHonorarioDelegadoMensual,
  rowsByDetalleId: Map<string, DetalleDelegadoRow>,
): {
  entries: DelegadoSelectionEntry[];
  unresolved: number;
  unresolvedDetails: RHUnresolvedDetail[];
} {
  const entries: DelegadoSelectionEntry[] = [];
  const unresolvedDetails: RHUnresolvedDetail[] = [];

  for (const det of rh.detalles ?? []) {
    const row = det.detalle_id
      ? rowsByDetalleId.get(det.detalle_id)
      : undefined;
    const liquidacion = row?.delegado_liquidacion?.liquidacion;
    const liquidacionGeneralId = liquidacion?.id;
    const especialidadId = row?.delegado_liquidacion?.especialidad?.id;

    if (!det.detalle_id || !row || !liquidacionGeneralId || !especialidadId) {
      unresolvedDetails.push({
        detalle_id: det.detalle_id ?? null,
        expediente: det.expediente,
        numero_rh: det.numero_rh ?? null,
      });
      continue;
    }

    const tipo = liquidacion?.tipo_liquidacion;
    entries.push({
      cotizarItem: {
        numero_rh: det.numero_rh ?? "",
        periodo: det.periodo ?? undefined,
        mes: det.mes ?? undefined,
        dictamen_revision: det.dictamen_revision ?? "",
        fecha_presentacion: det.fecha_presentacion ?? "",
        fecha_revision: det.fecha_revision ?? "",
        detalle_id: det.detalle_id,
        liquidacion_general_id: liquidacionGeneralId,
        especialidad_revision_id: especialidadId,
      },
      candidate: {
        id: liquidacionGeneralId,
        expediente: liquidacion.expediente ?? det.expediente,
        numero_revision:
          liquidacion.numero_revision ?? det.numero_revision ?? 0,
        sub_total: det.sub_total_liquidacion ?? null,
        total: det.total_liquidacion ?? null,
        municipalidad_nombre: liquidacion.municipalidad?.nombre ?? null,
        proyecto_denominacion: null,
        tipo_liquidacion: tipo
          ? { codigo: tipo.codigo ?? "", nombre: tipo.nombre ?? "" }
          : null,
        especialidad_candidata: {
          id: especialidadId,
          nombre: row.delegado_liquidacion.especialidad?.nombre ?? "",
        },
        tipo_delegado: rh.delegado_operacion_context?.tipo ?? "",
        delegado_operacion_id: rh.delegado_operacion_id ?? "",
        liquidacion_especifica_numero:
          liquidacion.numero ?? det.liquidacion_especifica_numero ?? null,
        comprobante_activo: det.comprobante_activo ?? null,
      },
    });
  }

  return { entries, unresolved: unresolvedDetails.length, unresolvedDetails };
}

/**
 * Construye la selección inicial del modo edición (inspector) a partir de los
 * detalles persistidos del RH.
 *
 * Una fila ya guardada no tiene `liquidacion_categoria_visitas_id` (el PATCH la
 * reconoce por `detalle_id` + `exp_liqui`), así que en el store se indexa con
 * la clave `detalle:<detalle_id>`.
 */
export function buildInspectorEditSelection(
  rh: ReciboHonorarioInspectorMensual,
): InspectorSelectionEntry[] {
  const entries: InspectorSelectionEntry[] = [];

  for (const det of rh.detalles ?? []) {
    if (!det.detalle_id) continue;

    const saldoDisponible = Math.max(
      0,
      det.inspecciones_programadas -
        det.inspecciones_pagadas_hasta_mes_anterior,
    );

    entries.push({
      cotizarItem: {
        cantidad_visitas: det.inspecciones_liquidadas,
        periodo: rh.periodo ?? undefined,
        mes: rh.mes ?? undefined,
        detalle_id: det.detalle_id,
      },
      candidate: {
        liquidacion_inspector_id: "",
        liquidacion_categoria_visitas_id: `detalle:${det.detalle_id}`,
        liquidacion_general_id: "",
        expediente: det.expediente,
        numero_revision: det.numero_revision ?? 0,
        fecha_registro: "",
        inspector_nombre: rh.inspector?.nombre_completo ?? "",
        inspector_cip: rh.inspector?.cip ?? "",
        inspector_dni: rh.inspector?.dni ?? "",
        especialidad_nombre: "",
        nombre_propietario: det.nombre_propietario,
        cantidad_visitas: det.inspecciones_programadas,
        inspecciones_pagadas: det.inspecciones_pagadas_hasta_mes_anterior,
        saldo_disponible: saldoDisponible,
        costo_por_inspeccion: det.costo_por_inspeccion,
        total_liquidacion: det.importe_bruto,
        sub_total_liquidacion: det.sub_total ?? det.importe_bruto,
        liquidacion_especifica_numero:
          det.liquidacion_especifica_numero ?? null,
        comprobante_activo: det.comprobante_activo ?? null,
      },
    });
  }

  return entries;
}

/**
 * Detalles persistidos del RH de inspector que NO se pueden conservar.
 *
 * Una fila persistida se identifica por `detalle_id` (el PATCH la conserva en
 * vez de re-agregarla): si el detalle no lo tiene, la fila no se puede
 * representar en el payload y el PATCH la RETIRARÍA. Se devuelven para
 * mostrarlas en el wizard y bloquear el guardado en vez de descartarlas en
 * silencio.
 */
export function collectInspectorUnresolvedDetails(
  rh: ReciboHonorarioInspectorMensual,
): RHUnresolvedDetail[] {
  const unresolved: RHUnresolvedDetail[] = [];

  for (const det of rh.detalles ?? []) {
    if (det.detalle_id) continue;
    unresolved.push({
      detalle_id: null,
      expediente: det.expediente,
      numero_rh: null,
    });
  }

  return unresolved;
}
