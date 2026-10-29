/**
 * Lenguaje de interfaz de las revisiones — Fase 5.
 *
 * La acción que antes decía "Tercera Revisión" ahora dice "Nueva Revisión":
 * el número de revisión es una ETIQUETA editable (cualquiera de 1, 3 o 5) y
 * ya no existe una "tercera revisión" como concepto de negocio.
 *
 * El test es de fuente (no de render): las cinco vistas comparten el mismo
 * esqueleto de listado y el botón vive en un `extraAction` que depende del
 * chrome compartido `LiquidacionesListContent`. Verificar el texto en la
 * fuente cubre exactamente el rótulo que ve el usuario.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/** Vistas con revisión editable (cinco tipos). */
const VISTAS_CON_REVISION = [
  "LiquidacionesEdificacionesView.tsx",
  "LiquidacionesHabilitacionUrbanaView.tsx",
  "LiquidacionesMecanicaSuelosView.tsx",
  "LiquidacionesTaludesView.tsx",
  "LiquidacionesImpactoVialView.tsx",
];

const ETIQUETA_NUEVA = "Nueva Revisión";
const ETIQUETA_VIEJA = "Tercera Revisión";

/**
 * Directorio de este archivo de test.
 *
 * Se resuelve con `path` y NO con `new URL(relativo, import.meta.url)`: en el
 * entorno jsdom de vitest el constructor `URL` ignora la base `file:` cuando
 * la ruta relativa sale del directorio actual (`../components/...`) y resuelve
 * contra el origen del dev-server (`http://localhost:3000`), lo que hace que
 * `readFileSync` falle con "The URL must be of scheme file".
 */
const DIRECTORIO_VIEWS = path.dirname(fileURLToPath(import.meta.url));

function leerVista(nombreArchivo: string): string {
  return readFileSync(path.join(DIRECTORIO_VIEWS, nombreArchivo), "utf8");
}

function leerChromeCompartido(): string {
  return readFileSync(
    path.join(
      DIRECTORIO_VIEWS,
      "..",
      "components",
      "LiquidacionesListContent.tsx",
    ),
    "utf8",
  );
}

describe("Acción de nueva revisión — etiqueta de las cinco vistas", () => {
  it.each(VISTAS_CON_REVISION)(
    "%s ofrece la acción «Nueva Revisión»",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      expect(fuente).toContain(ETIQUETA_NUEVA);
    },
  );

  it.each(VISTAS_CON_REVISION)(
    "%s ya no dice «Tercera Revisión»",
    (nombreArchivo) => {
      const fuente = leerVista(nombreArchivo);

      expect(fuente).not.toContain(ETIQUETA_VIEJA);
    },
  );

  it("Inspección de Obra no ofrece la acción (es revision-less, fija en 1)", () => {
    const fuente = leerVista("LiquidacionesInspeccionObraView.tsx");

    expect(fuente).not.toContain(ETIQUETA_NUEVA);
    expect(fuente).not.toContain(ETIQUETA_VIEJA);
  });

  it("el chrome compartido documenta la nueva etiqueta", () => {
    const fuente = leerChromeCompartido();

    expect(fuente).toContain(ETIQUETA_NUEVA);
    expect(fuente).not.toContain(ETIQUETA_VIEJA);
  });
});
