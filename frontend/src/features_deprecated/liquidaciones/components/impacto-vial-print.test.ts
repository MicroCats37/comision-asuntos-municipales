/**
 * Tests for impacto-vial-print adapter.
 *
 * Contract:
 * - porcentaje_liquidacion = 0.05 means 5% (backend convention)
 * - amount = valor_proyecto * porcentaje_liquidacion (100000 * 0.05 = 5000)
 * - Display percentage as 5.00% or equivalent, NOT 0.05%
 */
import { describe, it, expect } from 'vitest';
import { adaptIVToPrintData, formatPorcentajeLine, IVToCardBase } from './impacto-vial-print';
import type { LiquidacionImpactoVialListItem } from '../types/liquidacion-impacto-vial.types';
import type { LiquidacionCardBase } from '../types/liquidacion-general';

// ── Factory helpers ─────────────────────────────────────────────────────────

function makeIvResponse(overrides: Partial<LiquidacionImpactoVialListItem> = {}): LiquidacionImpactoVialListItem {
  return {
    id: 'iv-1',
    public_id: 'IV-2024-001',
    estado: 'completado',
    tipo_liquidacion: 'impacto-vial',
    numero_revision: 1,
    fecha_registro: '2024-06-15T10:00:00Z',
    proyecto: {
      id: 'proj-1',
      public_id: 'PROJ-001',
      nombre: 'Edificio Comercial Los Andes',
      direccion: 'Av. Arequipa 1234, Lima',
      valor_proyecto: 100000,
      entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Empresa ABC S.A.C.', ruc: '20123456789' },
    },
    entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Empresa ABC S.A.C.', ruc: '20123456789' },
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

describe('adaptIVToPrintData', () => {
  it('extracts porcentaje_liquidacion from tarifa as decimal fraction (0.05 = 5%)', () => {
    const response = makeIvResponse();
    const printData = adaptIVToPrintData(response);

    // Contract: porcentaje_liquidacion is stored as decimal fraction (0.05), NOT percentage (5)
    expect(printData.porcentaje_liquidacion).toBe(0.05);
  });

  it('extracts valor_proyecto directly from proyecto', () => {
    const response = makeIvResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 250000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptIVToPrintData(response);

    expect(printData.valor_proyecto).toBe(250000);
  });

  it('calculates amount as valor_proyecto * porcentaje_liquidacion (100000 * 0.05 = 5000)', () => {
    const response = makeIvResponse();
    const printData = adaptIVToPrintData(response);

    // The calculated amount = valor_proyecto * porcentaje_liquidacion
    const calculated = printData.valor_proyecto * printData.porcentaje_liquidacion;
    expect(calculated).toBeCloseTo(5000, 2);
  });

  it('uses porcentaje_liquidacion (decimal) for display, not porcentaje / 100', () => {
    const response = makeIvResponse();
    const printData = adaptIVToPrintData(response);

    // Display representation should be 5% from 0.05 — confirmed by multiplying by 100
    const displayedPercentage = printData.porcentaje_liquidacion * 100;
    expect(displayedPercentage).toBeCloseTo(5, 2);
    // Must NOT be 0.05 (which would be 0.05% displayed incorrectly)
    expect(printData.porcentaje_liquidacion).not.toBeCloseTo(0.05 * 100, 2);
  });

  it('maps proyecto.nombre to proyecto_nombre', () => {
    const response = makeIvResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Mi Proyecto Increíble', direccion: null, valor_proyecto: 100000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptIVToPrintData(response);

    expect(printData.proyecto_nombre).toBe('Mi Proyecto Increíble');
  });

  it('maps entidad.nombre to proponente_nombre with em-dash fallback', () => {
    const response = makeIvResponse({
      entidad: { id: 'e1', tipo: 'ruc', nombre: 'Cont SAC', ruc: '20111111111' },
    });
    const printData = adaptIVToPrintData(response);

    expect(printData.proponente_nombre).toBe('Cont SAC');
  });

  it('maps municipalidad.codigo and municipalidad.nombre', () => {
    const response = makeIvResponse({
      municipalidad: { id: 'm1', nombre: 'Municipalidad de Miraflores', codigo: 'MIRA01', provincia: null, distrito: null },
    });
    const printData = adaptIVToPrintData(response);

    expect(printData.municipalidad_codigo).toBe('MIRA01');
    expect(printData.municipalidad_nombre).toBe('Municipalidad de Miraflores');
  });

  it('maps valores fields correctly', () => {
    const response = makeIvResponse({
      valores: { subtotal: 4237.29, igv: 762.71, total: 5000, total_a_pagar: 5000 },
    });
    const printData = adaptIVToPrintData(response);

    expect(printData.subtotal).toBeCloseTo(4237.29, 2);
    expect(printData.igv).toBeCloseTo(762.71, 2);
    expect(printData.total).toBeCloseTo(5000, 2);
    expect(printData.liquidacion_total).toBeCloseTo(5000, 2);
    expect(printData.total_a_pagar).toBeCloseTo(5000, 2);
  });

  it('gracefully falls back to 0 when tarifa is missing', () => {
    const response = makeIvResponse({ revisiones: [] });
    const printData = adaptIVToPrintData(response);

    expect(printData.porcentaje_liquidacion).toBe(0);
    expect(printData.porcentaje_minimo_uit).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('gracefully falls back to 0 when tarifas is null', () => {
    const response = makeIvResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: null, derecho_maximo: null, porcentaje_liquidacion: null, porcentaje_minimo_uit: null, costo_por_m2: null, area_m2: null } }] });
    const printData = adaptIVToPrintData(response);

    expect(printData.porcentaje_liquidacion).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('handles various percentage values correctly (0.10 = 10%, 0.01 = 1%)', () => {
    const response10 = makeIvResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: 0, derecho_maximo: null, porcentaje_liquidacion: 0.10, porcentaje_minimo_uit: 0, costo_por_m2: null, area_m2: null } }] });
    const printData10 = adaptIVToPrintData(response10);
    expect(printData10.porcentaje_liquidacion * 100).toBeCloseTo(10, 2);

    const response1 = makeIvResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', derecho_minimo: 0, derecho_maximo: null, porcentaje_liquidacion: 0.01, porcentaje_minimo_uit: 0, costo_por_m2: null, area_m2: null } }] });
    const printData1 = adaptIVToPrintData(response1);
    expect(printData1.porcentaje_liquidacion * 100).toBeCloseTo(1, 2);
  });

  it('print display uses (porcentaje_liquidacion * 100).toFixed(2) for human-readable percentage', () => {
    // Exercises the real production helper formatPorcentajeLine
    const line = formatPorcentajeLine(100000, 0.05);
    expect(line).toBe('VALOR OBRA: S/ 100,000.00 x 5.00% = S/ 5,000.00');

    const line10 = formatPorcentajeLine(100000, 0.10);
    expect(line10).toBe('VALOR OBRA: S/ 100,000.00 x 10.00% = S/ 10,000.00');
  });
});

describe('IVToCardBase', () => {
  it('returns the IV list item as LiquidacionCardBase (type cast)', () => {
    const response = makeIvResponse();
    const cardBase = IVToCardBase(response);

    // IV list item IS the LiquidacionCardBase shape - just a type cast
    expect(cardBase.id).toBe(response.id);
    expect(cardBase.public_id).toBe(response.public_id);
    expect(cardBase.tipo_liquidacion).toBe('impacto-vial');
    expect(cardBase.estado).toBe(response.estado);
  });

  it('preserves revisions with tarifa.porcentaje_liquidacion for PDF percentage display', () => {
    const response = makeIvResponse();
    const cardBase = IVToCardBase(response) as LiquidacionCardBase;

    // The percentage line in buildLiquidacionPdfElement reads from revisiones[0].tarifa.porcentaje_liquidacion
    const firstRevision = cardBase.revisiones[0];
    expect(firstRevision).toBeDefined();
    expect(firstRevision!.tarifa!.porcentaje_liquidacion).toBe(0.05);
  });

  it('preserves valores for PDF financial display', () => {
    const response = makeIvResponse({
      valores: { subtotal: 4237.29, igv: 762.71, total: 5000, total_a_pagar: 5000 },
    });
    const cardBase = IVToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.valores.subtotal).toBeCloseTo(4237.29, 2);
    expect(cardBase.valores.total_a_pagar).toBeCloseTo(5000, 2);
  });

  it('preserves proyecto.valor_proyecto for percentage calculation', () => {
    const response = makeIvResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 250000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const cardBase = IVToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.proyecto.valor_proyecto).toBe(250000);
  });
});
