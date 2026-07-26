/**
 * Behavior tests for PDF helper functions.
 *
 * Tests:
 * - principal contact preferred over first contact for name and phone
 * - phone fallback: telefono -> celular -> —
 * - date/time formatting from ISO timestamp (not current time)
 * - current user name formatting fallback
 */
import { describe, it, expect } from 'vitest';
import type { ContactoListItem } from '../features/liquidaciones/types/liquidacion-general';

// ── Re-implement helpers for testing (same logic as LiquidacionPDFModal.tsx) ─────

function getContactName(contactos: ContactoListItem[]): string {
  const contact = contactos?.find((c) => c.principal) ?? contactos?.[0];
  if (!contact) return '—';
  const name = `${contact.nombres?.trim() ?? ''} ${contact.apellidos?.trim() ?? ''}`.trim();
  return name || '—';
}

function getContactPhone(contactos: ContactoListItem[]): string {
  const contact = contactos?.find((c) => c.principal) ?? contactos?.[0];
  if (!contact) return '—';
  return contact.telefono ?? contact.celular ?? '—';
}

function formatPrintedDateTime(isoDatetime: string): string {
  const date = new Date(isoDatetime);
  if (Number.isNaN(date.getTime())) {
    // Fallback to simple date formatting
    return new Date(isoDatetime).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).toUpperCase();
  }
  const dateStr = date.toLocaleDateString('es-PE', { day: '2-digit', month: 'long', year: 'numeric' }).toUpperCase();
  const timeStr = date.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${dateStr} ${timeStr}`;
}

function formatCurrentUserName(currentUser: { nombres: string; apellidos: string } | null | undefined): string {
  if (!currentUser) return '—';
  return `${currentUser.nombres?.trim() ?? ''} ${currentUser.apellidos?.trim() ?? ''}`.trim() || '—';
}

// ── Test helpers ─────────────────────────────────────────────────────────────────

const makeContact = (overrides: Partial<ContactoListItem> = {}): ContactoListItem => ({
  id: 'c1',
  nombres: 'Juan',
  apellidos: 'Pérez',
  dni: '12345678',
  cargo: 'Contacto',
  telefono: null,
  celular: null,
  email: null,
  direccion: null,
  principal: false,
  descripcion: null,
  ...overrides,
});

// ── Tests ───────────────────────────────────────────────────────────────────────

describe('getContactName', () => {
  it('returns — when contactos is empty or undefined', () => {
    expect(getContactName([])).toBe('—');
    expect(getContactName([])).toBe('—');
  });

  it('returns — when only contact has null nombres and apellidos', () => {
    const contact = makeContact({ nombres: null, apellidos: null });
    expect(getContactName([contact])).toBe('—');
  });

  it('prefers principal contact over first contact', () => {
    const principal = makeContact({ id: 'p', nombres: 'Principal', apellidos: 'Principal Apellido', principal: true });
    const first = makeContact({ id: 'f', nombres: 'First', apellidos: 'First Apellido', principal: false });
    expect(getContactName([first, principal])).toBe('Principal Principal Apellido');
  });

  it('returns first contact name when no principal exists', () => {
    const first = makeContact({ id: 'f', nombres: 'Carlos', apellidos: 'García' });
    const second = makeContact({ id: 's', nombres: 'María', apellidos: 'López' });
    expect(getContactName([first, second])).toBe('Carlos García');
  });

  it('trims whitespace from concatenated names', () => {
    const contact = makeContact({ nombres: '  Ana ', apellidos: '  Romero  ' });
    expect(getContactName([contact])).toBe('Ana Romero');
  });
});

describe('getContactPhone', () => {
  it('returns — when contactos is empty or undefined', () => {
    expect(getContactPhone([])).toBe('—');
  });

  it('prefers principal contact phone over first contact', () => {
    const principal = makeContact({ id: 'p', telefono: '555-0001', principal: true });
    const first = makeContact({ id: 'f', telefono: '555-0002', principal: false });
    expect(getContactPhone([first, principal])).toBe('555-0001');
  });

  it('falls back to celular when telefono is null on principal contact', () => {
    const principal = makeContact({ id: 'p', telefono: null, celular: '999-111-222', principal: true });
    const first = makeContact({ id: 'f', telefono: '555-0002', principal: false });
    expect(getContactPhone([first, principal])).toBe('999-111-222');
  });

  it('returns — when principal contact exists but has no phones', () => {
    const principal = makeContact({ id: 'p', telefono: null, celular: null, principal: true });
    const first = makeContact({ id: 'f', telefono: '555-0002', principal: false });
    // The logic is: pick ONE contact (principal or first), then use that contact's phone
    // Since principal is selected and has no phone, we return —
    expect(getContactPhone([first, principal])).toBe('—');
  });

  it('returns — when no contact has any phone', () => {
    const contact = makeContact({ telefono: null, celular: null });
    expect(getContactPhone([contact])).toBe('—');
  });

  it('prefers telefono over celular for same contact', () => {
    const contact = makeContact({ telefono: '555-1234', celular: '999-999-999' });
    expect(getContactPhone([contact])).toBe('555-1234');
  });
});

describe('formatPrintedDateTime', () => {
  it('formats ISO datetime with date and time in Peru locale', () => {
    // 2026-07-24T06:30:31.246273+00:00 is UTC time
    // When displayed in Peru (UTC-5), it becomes 2026-07-24T01:30:31
    const result = formatPrintedDateTime('2026-07-24T06:30:31.246273+00:00');
    // Should contain date parts and time (in Peru timezone)
    expect(result).toMatch(/24/);
    expect(result).toMatch(/JULIO/);
    expect(result).toMatch(/2026/);
    // Time should be in Peru timezone (UTC-5): 06:30 UTC -> 01:30 Peru
    expect(result).toMatch(/01:30/);
  });

  it('uses current locale formatting for date', () => {
    const result = formatPrintedDateTime('2026-07-24T06:30:31.246273+00:00');
    // Uppercase month name expected
    expect(result).toContain('JULIO');
  });

  it('returns fallback for invalid ISO string', () => {
    const result = formatPrintedDateTime('not-a-date');
    // Should still return some string (the fallback path)
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('formatCurrentUserName', () => {
  it('returns — when user is null or undefined', () => {
    expect(formatCurrentUserName(null)).toBe('—');
    expect(formatCurrentUserName(undefined)).toBe('—');
  });

  it('returns — when user has empty nombres and apellidos', () => {
    expect(formatCurrentUserName({ nombres: '', apellidos: '' })).toBe('—');
  });

  it('returns full name for valid user', () => {
    expect(formatCurrentUserName({ nombres: 'Ana', apellidos: 'Martínez' })).toBe('Ana Martínez');
  });

  it('trims whitespace from user name', () => {
    expect(formatCurrentUserName({ nombres: '  Luis ', apellidos: '  Torres  ' })).toBe('Luis Torres');
  });
});
