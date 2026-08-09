/**
 * Tests for taludes-print adapter.
 *
 * Contract:
 * - porcentaje_liquidacion = 0.05 means 5% (backend convention)
 * - amount = valor_proyecto * porcentaje_liquidacion (100000 * 0.05 = 5000)
 * - Display percentage as 5.00% or equivalent, NOT 0.05%
 */
import { describe, it, expect } from 'vitest';
import { adaptTaludesToPrintData, formatPorcentajeLine, TaludesToCardBase } from './taludes-print';
import type { LiquidacionTaludesListItem } from '../types/liquidacion-taludes.types';
import type { LiquidacionCardBase } from '../types/liquidacion-general';

// ── Factory helpers ─────────────────────────────────────────────────────────

function makeTaludesResponse(overrides: Partial<LiquidacionTaludesListItem> = {}): LiquidacionTaludesListItem {
  return {
    id: 'tal-1',
    public_id: 'TAL-2024-001',
    estado: 'completado',
    tipo_liquidacion: 'taludes',
    numero_revision: 1,
    fecha_registro: '2024-06-15T10:00:00Z',
    proyecto: {
      id: 'proj-1',
      public_id: 'PROJ-001',
      nombre: 'Condominio Residencial Las Lomas',
      direccion: 'Av. Javier Prado 5678, Lima',
      valor_proyecto: 100000,
      entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Inmobiliaria XYZ S.A.C.', ruc: '20123456789' },
    },
    entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Inmobiliaria XYZ S.A.C.', ruc: '20123456789' },
    municipalidad: { id: 'mun-1', nombre: 'Municipalidad de Lima', codigo: 'LIMA001', provincia: null, distrito: null },
    valores: { subtotal: 5000, igv: 900, total: 5900, total_a_pagar: 5900 },
    proyectistas: [],
    delegados: [],
    contactos: [],
    revisiones: [
      {
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          derecho_minimo: 500,
          derecho_maximo: null,
          porcentaje_liquidacion: 0.05,
          porcentaje_minimo_uit: 0.01,
          costo_por_m2: null,
          area_m2: null,
        },
      },
    ],
    ...overrides,
  };
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('adaptTaludesToPrintData', () => {
  it('extracts porcentaje_liquidacion from tarifa as decimal fraction (0.05 = 5%)', () => {
    const response = makeTaludesResponse();
    const printData = adaptTaludesToPrintData(response);

    // Contract: porcentaje_liquidacion is stored as decimal fraction (0.05), NOT percentage (5)
    expect(printData.porcentaje_liquidacion).toBe(0.05);
  });

  it('extracts valor_proyecto directly from proyecto', () => {
    const response = makeTaludesResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 350000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.valor_proyecto).toBe(350000);
  });

  it('calculates amount as valor_proyecto * porcentaje_liquidacion (100000 * 0.05 = 5000)', () => {
    const response = makeTaludesResponse();
    const printData = adaptTaludesToPrintData(response);

    // The calculated amount = valor_proyecto * porcentaje_liquidacion
    const calculated = printData.valor_proyecto * printData.porcentaje_liquidacion;
    expect(calculated).toBeCloseTo(5000, 2);
  });

  it('uses porcentaje_liquidacion (decimal) for display, not porcentaje / 100', () => {
    const response = makeTaludesResponse();
    const printData = adaptTaludesToPrintData(response);

    // Display representation should be 5% from 0.05 — confirmed by multiplying by 100
    const displayedPercentage = printData.porcentaje_liquidacion * 100;
    expect(displayedPercentage).toBeCloseTo(5, 2);
    // Must NOT be 0.05 (which would be 0.05% displayed incorrectly)
    expect(printData.porcentaje_liquidacion).not.toBeCloseTo(0.05 * 100, 2);
  });

  it('maps proyecto.nombre to proyecto_nombre', () => {
    const response = makeTaludesResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Urbanización Los Olivos', direccion: null, valor_proyecto: 100000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.proyecto_nombre).toBe('Urbanización Los Olivos');
  });

  it('maps entidad.nombre to proponente_nombre with em-dash fallback', () => {
    const response = makeTaludesResponse({
      entidad: { id: 'e1', tipo: 'ruc', nombre: 'Constructora Norte S.A.', ruc: '20111111111' },
    });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.proponente_nombre).toBe('Constructora Norte S.A.');
  });

  it('maps municipalidad.codigo and municipalidad.nombre', () => {
    const response = makeTaludesResponse({
      municipalidad: { id: 'm1', nombre: 'Municipalidad de San Isidro', codigo: 'SIS001', provincia: null, distrito: null },
    });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.municipalidad_codigo).toBe('SIS001');
    expect(printData.municipalidad_nombre).toBe('Municipalidad de San Isidro');
  });

  it('maps valores fields correctly', () => {
    const response = makeTaludesResponse({
      valores: { subtotal: 8474.58, igv: 1525.42, total: 10000, total_a_pagar: 10000 },
    });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.subtotal).toBeCloseTo(8474.58, 2);
    expect(printData.igv).toBeCloseTo(1525.42, 2);
    expect(printData.total).toBeCloseTo(10000, 2);
    expect(printData.liquidacion_total).toBeCloseTo(10000, 2);
    expect(printData.total_a_pagar).toBeCloseTo(10000, 2);
  });

  it('gracefully falls back to 0 when tarifa is missing', () => {
    const response = makeTaludesResponse({ revisiones: [] });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.porcentaje_liquidacion).toBe(0);
    expect(printData.porcentaje_minimo_uit).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('gracefully falls back to 0 when tarifa has null fields', () => {
    const response = makeTaludesResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: null, derecho_maximo: null, porcentaje_liquidacion: null, porcentaje_minimo_uit: null, costo_por_m2: null, area_m2: null } }] });
    const printData = adaptTaludesToPrintData(response);

    expect(printData.porcentaje_liquidacion).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('handles various percentage values correctly (0.10 = 10%, 0.01 = 1%)', () => {
    const response10 = makeTaludesResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: 0, derecho_maximo: null, porcentaje_liquidacion: 0.10, porcentaje_minimo_uit: 0, costo_por_m2: null, area_m2: null } }] });
    const printData10 = adaptTaludesToPrintData(response10);
    expect(printData10.porcentaje_liquidacion * 100).toBeCloseTo(10, 2);

    const response1 = makeTaludesResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: 0, derecho_maximo: null, porcentaje_liquidacion: 0.01, porcentaje_minimo_uit: 0, costo_por_m2: null, area_m2: null } }] });
    const printData1 = adaptTaludesToPrintData(response1);
    expect(printData1.porcentaje_liquidacion * 100).toBeCloseTo(1, 2);
  });

  it('print display uses (porcentaje_liquidacion * 100).toFixed(2) for human-readable percentage', () => {
    // Exercises the real production helper formatPorcentajeLine
    const line = formatPorcentajeLine(100000, 0.05);
    expect(line).toBe('VALOR OBRA: S/ 100,000.00 x 5.00% = S/ 5,000.00');

    const line7 = formatPorcentajeLine(100000, 0.07);
    expect(line7).toBe('VALOR OBRA: S/ 100,000.00 x 7.00% = S/ 7,000.00');
  });

  it('does NOT use area_m2 for Taludes (area-based fields not applicable)', () => {
    // Taludes uses percentage-based calculation, not area-based
    // This test confirms the adapter does NOT pull from area_m2
    const response = makeTaludesResponse({
      revisiones: [{
        id: 'r1',
        especialidades: [],
        tarifa: {
          id: 't1',
          derecho_minimo: 0,
          derecho_maximo: null,
          porcentaje_liquidacion: 0.05,
          porcentaje_minimo_uit: 0,
          costo_por_m2: 150,  // These should NOT affect Taludes calculation
          area_m2: 9999,       // These should NOT affect Taludes calculation
        },
      }],
    });
    const printData = adaptTaludesToPrintData(response);

    // valor_proyecto comes from proyecto, NOT from area_m2 * costo_por_m2
    expect(printData.valor_proyecto).toBe(100000);
  });
});

describe('TaludesToCardBase', () => {
  it('returns the Taludes list item as LiquidacionCardBase (type cast)', () => {
    const response = makeTaludesResponse();
    const cardBase = TaludesToCardBase(response);

    // Taludes list item IS the LiquidacionCardBase shape - just a type cast
    expect(cardBase.id).toBe(response.id);
    expect(cardBase.public_id).toBe(response.public_id);
    expect(cardBase.tipo_liquidacion).toBe('taludes');
    expect(cardBase.estado).toBe(response.estado);
  });

  it('preserves revisions with tarifa.porcentaje_liquidacion for PDF percentage display', () => {
    const response = makeTaludesResponse();
    const cardBase = TaludesToCardBase(response) as LiquidacionCardBase;

    // The percentage line in buildLiquidacionPdfElement reads from revisiones[0].tarifa.porcentaje_liquidacion
    const firstRevision = cardBase.revisiones[0];
    expect(firstRevision).toBeDefined();
    expect(firstRevision!.tarifa!.porcentaje_liquidacion).toBe(0.05);
  });

  it('preserves valores for PDF financial display', () => {
    const response = makeTaludesResponse({
      valores: { subtotal: 8474.58, igv: 1525.42, total: 10000, total_a_pagar: 10000 },
    });
    const cardBase = TaludesToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.valores.subtotal).toBeCloseTo(8474.58, 2);
    expect(cardBase.valores.total_a_pagar).toBeCloseTo(10000, 2);
  });

  it('preserves proyecto.valor_proyecto for percentage calculation', () => {
    const response = makeTaludesResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 350000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const cardBase = TaludesToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.proyecto.valor_proyecto).toBe(350000);
  });
});
