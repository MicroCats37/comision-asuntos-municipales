/**
 * Tests for habilitacion-urbana-print adapter.
 *
 * Key contract for HU (area-based, NOT percentage-based):
 * - area_solicitada comes from tarifa.area_solicitada, NOT tarifa.area_m2
 * - HU uses area-based calculation (area * costo_por_m2), not percentage
 */
import { describe, it, expect } from 'vitest';
import { adaptHuToPrintData, HUToCardBase } from './habilitacion-urbana-print';
import type { LiquidacionHabilitacionUrbanaListItem } from '../types/liquidacion-habilitacion-urbana.types';
import type { LiquidacionCardBase } from '../types/liquidacion-general';

// ── Factory helpers ─────────────────────────────────────────────────────────

function makeHuResponse(overrides: Partial<LiquidacionHabilitacionUrbanaListItem> = {}): LiquidacionHabilitacionUrbanaListItem {
  return {
    id: 'hu-1',
    public_id: 'HU-2024-001',
    estado: 'completado',
    tipo_liquidacion: 'habilitacion-urbana',
    numero_revision: 1,
    fecha_registro: '2024-06-15T10:00:00Z',
    proyecto: {
      id: 'proj-1',
      public_id: 'PROJ-001',
      nombre: 'Habilitación Urbana Villa Sol',
      direccion: 'Av. Ramiro Prialé km 12, Lima',
      valor_proyecto: 0,  // HU uses area, not valor_proyecto
      entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Constructora Delta S.A.C.', ruc: '20123456789' },
    },
    entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Constructora Delta S.A.C.', ruc: '20123456789' },
    municipalidad: { id: 'mun-1', nombre: 'Municipalidad de Lima', codigo: 'LIMA001', provincia: null, distrito: null },
    valores: { subtotal: 11800, igv: 2124, total: 13924, total_a_pagar: 13924 },
    proyectistas: [],
    delegados: [],
    contactos: [],
    revisiones: [
      {
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 118,
          area_m2: 100,           // Different from user-requested area
          area_solicitada: 500,   // User-requested area should be used
          derecho_minimo: 500,
          derecho_maximo: null,
        },
      },
    ],
    ...overrides,
  };
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('adaptHuToPrintData', () => {
  it('extracts area_solicitada from tarifa.area_solicitada, NOT tarifa.area_m2', () => {
    const response = makeHuResponse();
    const printData = adaptHuToPrintData(response);

    // Critical contract: area_solicitada comes from tarifa.area_solicitada
    // In the factory, area_solicitada = 500, area_m2 = 100
    expect(printData.area_solicitada).toBe(500);
    // If it were using area_m2, it would be 100 (wrong)
    expect(printData.area_solicitada).not.toBe(100);
  });

  it('maps area_solicitada from tarifa even when area_m2 is different', () => {
    const response = makeHuResponse({
      revisiones: [{
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 50,
          area_m2: 250,        // Tariff's standard area
          area_solicitada: 1200, // User's actual requested area
          derecho_minimo: 0,
          derecho_maximo: null,
        },
      }],
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.area_solicitada).toBe(1200);
    expect(printData.area_solicitada).not.toBe(250);
  });

  it('extracts costo_por_m2 from tarifa', () => {
    const response = makeHuResponse({
      revisiones: [{
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 85.50,
          area_m2: 200,
          area_solicitada: 350,
          derecho_minimo: 0,
          derecho_maximo: null,
        },
      }],
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.costo_por_m2).toBeCloseTo(85.50, 2);
  });

  it('maps proyecto.nombre to proyecto_nombre', () => {
    const response = makeHuResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Residencial Las Flores', direccion: null, valor_proyecto: 0, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.proyecto_nombre).toBe('Residencial Las Flores');
  });

  it('maps entidad.nombre to proponente_nombre with em-dash fallback', () => {
    const response = makeHuResponse({
      entidad: { id: 'e1', tipo: 'ruc', nombre: 'Inmobiliaria Pacifico S.A.', ruc: '20111111111' },
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.proponente_nombre).toBe('Inmobiliaria Pacifico S.A.');
  });

  it('maps municipalidad.codigo and municipalidad.nombre', () => {
    const response = makeHuResponse({
      municipalidad: { id: 'm1', nombre: 'Municipalidad de Callao', codigo: 'CALL001', provincia: null, distrito: null },
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.municipalidad_codigo).toBe('CALL001');
    expect(printData.municipalidad_nombre).toBe('Municipalidad de Callao');
  });

  it('maps valores fields correctly', () => {
    const response = makeHuResponse({
      valores: { subtotal: 5000, igv: 900, total: 5900, total_a_pagar: 5900 },
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.subtotal).toBeCloseTo(5000, 2);
    expect(printData.igv).toBeCloseTo(900, 2);
    expect(printData.total).toBeCloseTo(5900, 2);
    expect(printData.liquidacion_total).toBeCloseTo(5900, 2);
    expect(printData.total_a_pagar).toBeCloseTo(5900, 2);
  });

  it('gracefully falls back to 0 when tarifa is missing', () => {
    const response = makeHuResponse({ revisiones: [] });
    const printData = adaptHuToPrintData(response);

    expect(printData.area_solicitada).toBe(0);
    expect(printData.costo_por_m2).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('gracefully falls back to 0 when tarifa has null fields', () => {
    const response = makeHuResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', costo_por_m2: null, area_m2: null, area_solicitada: null, derecho_minimo: null, derecho_maximo: null } }] });
    const printData = adaptHuToPrintData(response);

    expect(printData.area_solicitada).toBe(0);
    expect(printData.costo_por_m2).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('maps derecho_maximo correctly when present', () => {
    const response = makeHuResponse({
      revisiones: [{
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 100,
          area_m2: 500,
          area_solicitada: 1000,
          derecho_minimo: 500,
          derecho_maximo: 5000,
        },
      }],
    });
    const printData = adaptHuToPrintData(response);

    expect(printData.derecho_maximo).toBe(5000);
  });

  it('maps derecho_maximo as null when absent', () => {
    const response = makeHuResponse();
    const printData = adaptHuToPrintData(response);

    expect(printData.derecho_maximo).toBeNull();
  });

  it('does NOT use percentage-based fields (porcentaje_liquidacion not applicable for HU)', () => {
    // HU is area-based, not percentage-based
    // This test documents that HU print adapter does not use valor_proyecto * percentage
    const response = makeHuResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 1000000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptHuToPrintData(response);

    // HU does not have porcentaje_liquidacion field - the interface only has area-based fields
    expect(printData).not.toHaveProperty('porcentaje_liquidacion');
  });
});

describe('HUToCardBase', () => {
  it('returns the HU list item as LiquidacionCardBase (type cast)', () => {
    const response = makeHuResponse();
    const cardBase = HUToCardBase(response);

    // HU list item IS the LiquidacionCardBase shape - just a type cast
    expect(cardBase.id).toBe(response.id);
    expect(cardBase.public_id).toBe(response.public_id);
    expect(cardBase.tipo_liquidacion).toBe('habilitacion-urbana');
    expect(cardBase.estado).toBe(response.estado);
  });

  it('preserves revisions with tariff data for post-create PDF renderer', () => {
    const response = makeHuResponse();
    const cardBase = HUToCardBase(response) as LiquidacionCardBase;

    // The m² fields are preserved in revisiones[0].tarifa
    const firstRevision = cardBase.revisiones[0];
    expect(firstRevision).toBeDefined();
    // area_solicitada is HU-specific; cast to any to access it through the general LiquidacionCardBase type
    expect((firstRevision!.tarifa as any).area_solicitada).toBe(500);
    expect(firstRevision!.tarifa!.costo_por_m2).toBe(118);
  });

  it('preserves valores for PDF financial display', () => {
    const response = makeHuResponse({
      valores: { subtotal: 11800, igv: 2124, total: 13924, total_a_pagar: 13924 },
    });
    const cardBase = HUToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.valores.subtotal).toBeCloseTo(11800, 2);
    expect(cardBase.valores.total_a_pagar).toBeCloseTo(13924, 2);
  });

  it('preserves proyecto data for PDF display', () => {
    const response = makeHuResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Residencial Las Flores', direccion: 'Av. Principal 123', valor_proyecto: 0, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const cardBase = HUToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.proyecto.nombre).toBe('Residencial Las Flores');
    expect(cardBase.proyecto.direccion).toBe('Av. Principal 123');
  });
});
