/**
 * Guardas de FUENTE de los puntos de entrada de comprobante de Liquidaciones.
 *
 * `unified-comprobante-modal` (Slice C): las 6 vistas por tipo, el shell de
 * tarjeta y el estado de tarjeta exponen UNA sola acción de comprobante,
 * etiquetada "Gestionar comprobante", sobre el modal ÚNICO.
 *
 * El test es de fuente (no de render): las 6 vistas comparten el mismo
 * esqueleto (`buildRowActions` + un `ComprobanteFormModal` elevado) y el rótulo
 * que ve el usuario es una constante del código. Verificar el texto en la
 * fuente cubre exactamente el rótulo que ve el usuario, sin arrastrar un
 * render completo de la vista (que exigiría providers, queries y datos).
 *
 * ALCANCE DEL SLICE: estas guardas cubren los puntos de entrada de
 * Liquidaciones. El browse RH y los modales RH mensual se migran en el Slice D.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (`sdd-verify`).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/** Las 6 vistas por tipo de liquidación. */
const VISTAS = [
  "LiquidacionesEdificacionesView.tsx",
  "LiquidacionesHabilitacionUrbanaView.tsx",
  "LiquidacionesImpactoVialView.tsx",
  "LiquidacionesInspeccionObraView.tsx",
  "LiquidacionesMecanicaSuelosView.tsx",
  "LiquidacionesTaludesView.tsx",
];

/** Rótulo ÚNICO de la acción de comprobante. */
const ETIQUETA_UNICA = "Gestionar comprobante";

/** Rótulos por estado que el flujo único sustituye. */
const ETIQUETAS_POR_ESTADO = ["Agregar comprobante", "Reemplazar comprobante"];

/**
 * Una instancia del modal por fichero. El lookahead evita contar
 * `<ComprobanteFormModalGestionar` (la implementación interna del modal) como
 * si fuera un punto de entrada.
 */
const REGEX_INSTANCIA = /<ComprobanteFormModal(?![A-Za-z0-9_])/g;

/**
 * Un selector de modo, en cualquiera de sus formas: atributo JSX (la prop
 * `modo` con valor) o prop declarada (`modo:` / `modo?:`). No casa con
 * `modoFormulario` (el identificador interno del formulario, que no es el
 * selector del modal).
 */
const REGEX_SELECTOR_MODO = /\bmodo\s*\??\s*[:=]/;

/**
 * Directorio de este archivo de test.
 *
 * Se resuelve con `path` y NO con `new URL(relativo, import.meta.url)`: en el
 * entorno jsdom de vitest el constructor `URL` ignora la base `file:` cuando
 * la ruta relativa sale del directorio actual y resuelve contra el origen del
 * dev-server, lo que hace que `readFileSync` falle con "The URL must be of
 * scheme file".
 */
const DIRECTORIO_VIEWS = path.dirname(fileURLToPath(import.meta.url));

function leerVista(nombreArchivo: string): string {
  return readFileSync(path.join(DIRECTORIO_VIEWS, nombreArchivo), "utf8");
}

/** Lee un fichero del feature `liquidaciones` (desde `views/`). */
function leerDelFeature(...partes: string[]): string {
  return readFileSync(path.join(DIRECTORIO_VIEWS, "..", ...partes), "utf8");
}

/**
 * Bloque JSX del elemento `<ComprobanteFormModal … />` de una fuente.
 *
 * Sirve para afirmar sobre lo que el modal hace (refetch o no) sin acoplar el
 * test al resto del fichero.
 */
function bloqueModal(fuente: string): string {
  const inicio = fuente.indexOf("<ComprobanteFormModal");
  if (inicio === -1) return "";
  const fin = fuente.indexOf("/>", inicio);
  return fuente.slice(inicio, fin === -1 ? undefined : fin);
}

describe("Vistas de Liquidaciones — ÚNICA acción de comprobante", () => {
  it.each(VISTAS)(
    "%s ofrece la acción «Gestionar comprobante»",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      expect(fuente).toContain(`label: "${ETIQUETA_UNICA}"`);
    },
  );

  it.each(VISTAS)(
    "%s ofrece esa acción UNA sola vez",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);
      const apariciones = fuente.split(ETIQUETA_UNICA).length - 1;

      expect(apariciones).toBe(1);
    },
  );

  it.each(VISTAS)(
    "%s ya no ofrece los rótulos por estado del comprobante",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      for (const etiqueta of ETIQUETAS_POR_ESTADO) {
        expect(fuente).not.toContain(etiqueta);
      }
    },
  );

  it.each(VISTAS)(
    "%s no bifurca el rótulo por el comprobante vigente",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      expect(fuente).not.toContain("comprobanteActivo");
    },
  );

  it.each(VISTAS)(
    "%s monta UNA sola instancia del modal y SIN selector de modo",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      expect(fuente.match(REGEX_INSTANCIA) ?? []).toHaveLength(1);
      expect(fuente).not.toMatch(REGEX_SELECTOR_MODO);
    },
  );

  it.each(VISTAS)(
    "%s NO hace refetch manual tras guardar el comprobante",
    (nombreArchivo) => {
      const bloque = bloqueModal(leerVista(nombreArchivo));

      expect(bloque).not.toBe("");
      expect(bloque).not.toContain("refetch");
    },
  );
});

describe("LiquidacionCardShell — rótulo por defecto ÚNICO", () => {
  const shell = leerDelFeature(
    "components",
    "cards",
    "LiquidacionCardShell.tsx",
  );

  it("usa «Gestionar comprobante» como rótulo por defecto", () => {
    expect(shell).toContain(`etiquetaComprobante ?? "${ETIQUETA_UNICA}"`);
  });

  it("ya no bifurca el rótulo por el comprobante vigente", () => {
    for (const etiqueta of ETIQUETAS_POR_ESTADO) {
      expect(shell).not.toContain(etiqueta);
    }
  });

  it("conserva `etiquetaComprobante` como override", () => {
    expect(shell).toContain("etiquetaComprobante?: string");
  });
});

describe("useLiquidacionCardState — modal ÚNICO y rótulo ÚNICO", () => {
  const estado = leerDelFeature("hooks", "useLiquidacionCardState.tsx");

  it("monta UNA sola instancia del modal, sin selector de modo", () => {
    expect(estado.match(REGEX_INSTANCIA) ?? []).toHaveLength(1);
    expect(estado).not.toMatch(REGEX_SELECTOR_MODO);
  });

  it("fija el rótulo «Gestionar comprobante»", () => {
    expect(estado).toContain(`etiquetaComprobante: "${ETIQUETA_UNICA}"`);
  });

  it("NO hace refetch manual tras guardar el comprobante (la caché se parchea)", () => {
    const bloque = bloqueModal(estado);

    expect(bloque).not.toBe("");
    expect(bloque).not.toContain("refetch");
    expect(bloque).not.toContain("onUpdated");
  });

  it("conserva `onUpdated?.()` para los flujos que NO parchean caché", () => {
    expect(estado).toContain("onUpdated?.()");
  });
});
