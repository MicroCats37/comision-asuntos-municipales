/**
 * Tests for mecanica-suelos-print adapter.
 *
 * Key contract for MS (area-based, NOT percentage-based):
 * - area_solicitada comes from tarifa.area_solicitada, NOT tarifa.area_m2
 * - MS uses area-based calculation (area * costo_por_m2), not percentage
 */
import { describe, it, expect } from 'vitest';
import { adaptMSToPrintData, MSToCardBase } from './mecanica-suelos-print';
import type { LiquidacionMecanicaSuelosListItem } from '../types/liquidacion-mecanica-suelos.types';
import type { LiquidacionCardBase } from '../types/liquidacion-general';

// ── Factory helpers ─────────────────────────────────────────────────────────

function makeMsResponse(overrides: Partial<LiquidacionMecanicaSuelosListItem> = {}): LiquidacionMecanicaSuelosListItem {
  return {
    id: 'ms-1',
    public_id: 'MS-2024-001',
    estado: 'completado',
    tipo_liquidacion: 'mecanica-suelos',
    numero_revision: 1,
    fecha_registro: '2024-06-15T10:00:00Z',
    proyecto: {
      id: 'proj-1',
      public_id: 'PROJ-001',
      nombre: 'Edificio Residencial Los Jardines',
      direccion: 'Av. Arenales 1234, Lima',
      valor_proyecto: 0,  // MS uses area, not valor_proyecto
      entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Constructora Omega S.A.C.', ruc: '20123456789' },
    },
    entidad: { id: 'ent-1', tipo: 'ruc', nombre: 'Constructora Omega S.A.C.', ruc: '20123456789' },
    municipalidad: { id: 'mun-1', nombre: 'Municipalidad de Lima', codigo: 'LIMA001', provincia: null, distrito: null },
    valores: { subtotal: 8850, igv: 1593, total: 10443, total_a_pagar: 10443 },
    proyectistas: [],
    delegados: [],
    contactos: [],
    revisiones: [
      {
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 88.50,
          area_m2: 100,           // Different from user-requested area
          area_solicitada: 500,    // User-requested area should be used
          derecho_minimo: 500,
          derecho_maximo: null,
        },
      },
    ],
    ...overrides,
  };
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('adaptMSToPrintData', () => {
  it('extracts area_solicitada from tarifa.area_solicitada, NOT tarifa.area_m2', () => {
    const response = makeMsResponse();
    const printData = adaptMSToPrintData(response);

    // Critical contract: area_solicitada comes from tarifa.area_solicitada
    // In the factory, area_solicitada = 500, area_m2 = 100
    expect(printData.area_solicitada).toBe(500);
    expect(printData.area_solicitada).not.toBe(100);
  });

  it('maps area_solicitada from tarifa even when area_m2 is different', () => {
    const response = makeMsResponse({
      revisiones: [{
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 75,
          area_m2: 200,        // Tariff's standard area
          area_solicitada: 800, // User's actual requested area
          derecho_minimo: 0,
          derecho_maximo: null,
        },
      }],
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.area_solicitada).toBe(800);
    expect(printData.area_solicitada).not.toBe(200);
  });

  it('extracts costo_por_m2 from tarifa', () => {
    const response = makeMsResponse({
      revisiones: [{
        id: 'rev-1',
        especialidades: [],
        tarifa: {
          id: 'tar-1',
          costo_por_m2: 95.75,
          area_m2: 150,
          area_solicitada: 300,
          derecho_minimo: 0,
          derecho_maximo: null,
        },
      }],
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.costo_por_m2).toBeCloseTo(95.75, 2);
  });

  it('maps proyecto.nombre to proyecto_nombre', () => {
    const response = makeMsResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Torre Empresarial San Miguel', direccion: null, valor_proyecto: 0, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.proyecto_nombre).toBe('Torre Empresarial San Miguel');
  });

  it('maps entidad.nombre to proponente_nombre with em-dash fallback', () => {
    const response = makeMsResponse({
      entidad: { id: 'e1', tipo: 'ruc', nombre: 'Inmobiliaria Norte S.A.', ruc: '20111111111' },
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.proponente_nombre).toBe('Inmobiliaria Norte S.A.');
  });

  it('maps municipalidad.codigo and municipalidad.nombre', () => {
    const response = makeMsResponse({
      municipalidad: { id: 'm1', nombre: 'Municipalidad de San Isidro', codigo: 'SI001', provincia: null, distrito: null },
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.municipalidad_codigo).toBe('SI001');
    expect(printData.municipalidad_nombre).toBe('Municipalidad de San Isidro');
  });

  it('maps valores fields correctly', () => {
    const response = makeMsResponse({
      valores: { subtotal: 8850, igv: 1593, total: 10443, total_a_pagar: 10443 },
    });
    const printData = adaptMSToPrintData(response);

    expect(printData.subtotal).toBeCloseTo(8850, 2);
    expect(printData.igv).toBeCloseTo(1593, 2);
    expect(printData.total).toBeCloseTo(10443, 2);
    expect(printData.liquidacion_total).toBeCloseTo(10443, 2);
    expect(printData.total_a_pagar).toBeCloseTo(10443, 2);
  });

  it('gracefully falls back to 0 when tarifa is missing', () => {
    const response = makeMsResponse({ revisiones: [] });
    const printData = adaptMSToPrintData(response);

    expect(printData.area_solicitada).toBe(0);
    expect(printData.costo_por_m2).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('gracefully falls back to 0 when tarifa has null fields', () => {
    const response = makeMsResponse({ revisiones: [{ id: 'r1', especialidades: [], tarifa: { id: 't1', costo_por_m2: null, area_m2: null, area_solicitada: null, derecho_minimo: null, derecho_maximo: null } }] });
    const printData = adaptMSToPrintData(response);

    expect(printData.area_solicitada).toBe(0);
    expect(printData.costo_por_m2).toBe(0);
    expect(printData.derecho_minimo).toBe(0);
  });

  it('maps derecho_maximo correctly when present', () => {
    const response = makeMsResponse({
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
    const printData = adaptMSToPrintData(response);

    expect(printData.derecho_maximo).toBe(5000);
  });

  it('maps derecho_maximo as null when absent', () => {
    const response = makeMsResponse();
    const printData = adaptMSToPrintData(response);

    expect(printData.derecho_maximo).toBeNull();
  });

  it('does NOT use percentage-based fields (porcentaje_liquidacion not applicable for MS)', () => {
    // MS is area-based, not percentage-based
    const response = makeMsResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 1000000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const printData = adaptMSToPrintData(response);

    // MS does not have porcentaje_liquidacion field - the interface only has area-based fields
    expect(printData).not.toHaveProperty('porcentaje_liquidacion');
  });
});

describe('MSToCardBase', () => {
  it('returns the MS list item as LiquidacionCardBase (type cast)', () => {
    const response = makeMsResponse();
    const cardBase = MSToCardBase(response);

    // MS list item IS the LiquidacionCardBase shape - just a type cast
    expect(cardBase.id).toBe(response.id);
    expect(cardBase.public_id).toBe(response.public_id);
    expect(cardBase.tipo_liquidacion).toBe('mecanica-suelos');
    expect(cardBase.estado).toBe(response.estado);
  });

  it('preserves revisions with tariff data for post-create PDF renderer', () => {
    const response = makeMsResponse();
    const cardBase = MSToCardBase(response) as LiquidacionCardBase;

    // The m² fields are preserved in revisiones[0].tarifa
    const firstRevision = cardBase.revisiones[0];
    expect(firstRevision).toBeDefined();
    // area_solicitada is MS-specific; cast to any to access it through the general LiquidacionCardBase type
    expect((firstRevision!.tarifa as any).area_solicitada).toBe(500);
    expect(firstRevision!.tarifa!.costo_por_m2).toBe(88.50);
  });

  it('preserves valores for PDF financial display', () => {
    const response = makeMsResponse({
      valores: { subtotal: 8850, igv: 1593, total: 10443, total_a_pagar: 10443 },
    });
    const cardBase = MSToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.valores.subtotal).toBeCloseTo(8850, 2);
    expect(cardBase.valores.total_a_pagar).toBeCloseTo(10443, 2);
  });

  it('preserves proyecto data for PDF display', () => {
    const response = makeMsResponse({
      proyecto: { id: 'p1', public_id: 'P1', nombre: 'Centro Comercial Norte', direccion: 'Av. La Marina 456', valor_proyecto: 0, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    });
    const cardBase = MSToCardBase(response) as LiquidacionCardBase;

    expect(cardBase.proyecto.nombre).toBe('Centro Comercial Norte');
    expect(cardBase.proyecto.direccion).toBe('Av. La Marina 456');
  });
});
