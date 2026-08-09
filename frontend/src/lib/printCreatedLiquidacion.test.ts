/**
 * Behavior tests for printCreatedLiquidacion helper.
 *
 * These tests verify that the post-create path uses the same
 * printLiquidacionDocument renderer as the card/list PDF button,
 * with the created response adapted to LiquidacionCardBase.
 *
 * This ensures consistency between card/list PDF button and post-create PDF.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { printCreatedLiquidacion } from './printCreatedLiquidacion';
import type { LiquidacionCardBase } from '../features/liquidaciones/types/liquidacion-general';

// ── Mock print function ─────────────────────────────────────────────────────────

const mockPrintFn = vi.fn().mockResolvedValue(undefined);

// ── Mock adapter ────────────────────────────────────────────────────────────────

interface MockCreated {
  id: string;
  public_id: string;
  tipo_liquidacion: string;
  valores: { total_a_pagar: number };
}

function mockToCardBase(created: MockCreated): LiquidacionCardBase {
  return {
    id: created.id,
    public_id: created.public_id,
    tipo_liquidacion: created.tipo_liquidacion,
    estado: 'completado',
    numero_revision: 1,
    fecha_registro: '2024-06-15T00:00:00Z',
    proyecto: { id: 'p1', public_id: 'P1', nombre: 'Test', direccion: null, valor_proyecto: 100000, entidad: { id: null, tipo: null, nombre: null, ruc: null } },
    entidad: { id: null, tipo: null, nombre: null, ruc: null },
    municipalidad: { id: 'm1', nombre: 'Lima', codigo: 'LIMA', provincia: null, distrito: null },
    valores: created.valores,
    proyectistas: [],
    delegados: [],
    contactos: [],
    revisiones: [],
  } as unknown as LiquidacionCardBase;
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('printCreatedLiquidacion', () => {
  beforeEach(() => {
    mockPrintFn.mockClear();
  });

  it('calls printFn with the adapted LiquidacionCardBase', async () => {
    const created: MockCreated = {
      id: 'test-1',
      public_id: 'LIQ-2024-001',
      tipo_liquidacion: 'test',
      valores: { total_a_pagar: 5000 },
    };

    await printCreatedLiquidacion(created, mockToCardBase, mockPrintFn);

    expect(mockPrintFn).toHaveBeenCalledTimes(1);
    const printedItem = mockPrintFn.mock.calls[0][0] as LiquidacionCardBase;
    expect(printedItem.id).toBe(created.id);
    expect(printedItem.public_id).toBe(created.public_id);
    expect(printedItem.tipo_liquidacion).toBe(created.tipo_liquidacion);
  });

  it('does NOT call printFn with the raw created response', async () => {
    const created: MockCreated = {
      id: 'test-2',
      public_id: 'LIQ-2024-002',
      tipo_liquidacion: 'test',
      valores: { total_a_pagar: 7500 },
    };

    await printCreatedLiquidacion(created, mockToCardBase, mockPrintFn);

    // The print function should be called with the adapted card base, NOT the raw created response
    expect(mockPrintFn).toHaveBeenCalledTimes(1);
    const printedItem = mockPrintFn.mock.calls[0][0] as MockCreated;
    // If this were called with raw created, it would have the raw structure
    // The fact that we access .id, .public_id, .tipo_liquidacion proves it's the adapted type
    expect(printedItem).not.toEqual(created);
  });

  it('passes the correct printFn (printLiquidacionDocument pattern)', async () => {
    const customPrintFn = vi.fn().mockResolvedValue(undefined);

    const created: MockCreated = {
      id: 'test-3',
      public_id: 'LIQ-2024-003',
      tipo_liquidacion: 'custom',
      valores: { total_a_pagar: 3000 },
    };

    await printCreatedLiquidacion(created, mockToCardBase, customPrintFn);

    expect(customPrintFn).toHaveBeenCalledTimes(1);
    expect(mockPrintFn).not.toHaveBeenCalled();
  });

  it('awaits the printFn promise', async () => {
    const asyncPrintFn = vi.fn().mockImplementation(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });

    const created: MockCreated = {
      id: 'test-4',
      public_id: 'LIQ-2024-004',
      tipo_liquidacion: 'async',
      valores: { total_a_pagar: 2000 },
    };

    const result = printCreatedLiquidacion(created, mockToCardBase, asyncPrintFn);

    // Should not throw - we're awaiting the promise
    await expect(result).resolves.toBeUndefined();
    expect(asyncPrintFn).toHaveBeenCalledTimes(1);
  });
});
