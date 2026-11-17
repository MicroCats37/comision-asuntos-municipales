/**
 * Guardas de FUENTE del modal ÚNICO de comprobante.
 *
 * `unified-comprobante-modal` (Slice A): el producto tiene UNA sola
 * implementación de modal de comprobante. Estas guardas leen el CÓDIGO (no lo
 * renderizan) y comprueban que la bifurcación por `modo` ya no existe:
 *
 *   1. Ningún fichero del frontend declara ni pasa `modo="crear"`.
 *   2. Cada punto de entrada monta UNA sola instancia del modal.
 *   3. El modal NO declara prop `modo` (ni el tipo `ModoComprobante`, ni la
 *      segunda implementación `ComprobanteFormModalCrear`).
 *   4. Ningún punto de entrada PASA un selector de modo al modal.
 *
 * ALCANCE: estas guardas cubren el MODAL y sus puntos de entrada (código de
 * producto). El Slice D retiró el último selector de modo que quedaba (el
 * browse RH): ya no hay ningún call site que lo pase.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (`sdd-verify`).
 */
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { describe, expect, it } from "vitest";

/** Raíz de `src` del frontend (se resuelve desde el cwd del test). */
function resolverRaizSrc(): string {
  const candidatos = [
    resolve(process.cwd(), "src"),
    resolve(process.cwd(), "frontend", "src"),
  ];
  const encontrada = candidatos.find(
    (candidato) => existsSync(candidato) && statSync(candidato).isDirectory(),
  );
  if (!encontrada) {
    throw new Error("No se encontró la raíz `src` del frontend");
  }
  return encontrada;
}

const RAIZ_SRC = resolverRaizSrc();

/**
 * Este fichero se EXCLUYE del barrido: contiene literalmente los needles que
 * busca (autorreferencia) y no es código de producto.
 */
const RELATIVO_GUARDIA =
  "features/liquidaciones/components/forms/comprobante-modal-unico.test.tsx";

const RELATIVO_MODAL =
  "features/liquidaciones/components/forms/ComprobanteFormModal.tsx";

interface Fuente {
  /** Ruta relativa a `src`, con `/` como separador. */
  relativo: string;
  contenido: string;
}

/** Lista recursivamente los ficheros `.ts`/`.tsx` bajo un directorio. */
function listarFuentes(dir: string): string[] {
  const salida: string[] = [];
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    if (entrada.name === "node_modules" || entrada.name.startsWith(".")) {
      continue;
    }
    const completo = join(dir, entrada.name);
    if (entrada.isDirectory()) {
      salida.push(...listarFuentes(completo));
    } else if (/\.tsx?$/.test(entrada.name)) {
      salida.push(completo);
    }
  }
  return salida;
}

/** ¿El fichero es un test? (los tests NO son puntos de entrada). */
function esFicheroDePrueba(relativo: string): boolean {
  return /\.test\.(ts|tsx)$/.test(relativo);
}

const FUENTES: Fuente[] = listarFuentes(RAIZ_SRC)
  .map((ruta) => ({
    relativo: relative(RAIZ_SRC, ruta).split(sep).join("/"),
    contenido: readFileSync(ruta, "utf8"),
  }))
  .filter(
    (fuente) =>
      fuente.relativo.toLowerCase() !== RELATIVO_GUARDIA.toLowerCase(),
  );

/** Código de producto (sin tests): los puntos de entrada del modal. */
const FUENTES_PRODUCCION = FUENTES.filter(
  (fuente) => !esFicheroDePrueba(fuente.relativo),
);

/**
 * El lookahead evita contar `<ComprobanteFormModalGestionar` (la
 * implementación interna del modal) como si fuera un punto de entrada.
 */
const REGEX_INSTANCIA = /<ComprobanteFormModal(?![A-Za-z0-9_])/g;

/** Ficheros que MONTAN el modal: sus puntos de entrada. */
const MONTajes_MODAL = FUENTES_PRODUCCION.filter(
  (fuente) =>
    // El fichero del modal no es un punto de entrada: renderiza su
    // implementación interna, no se monta a sí mismo.
    fuente.relativo !== RELATIVO_MODAL &&
    (fuente.contenido.match(REGEX_INSTANCIA) ?? []).length > 0,
);

/**
 * ÁMBITO de las guardas de `modo`: el modal y SUS puntos de entrada.
 *
 * El barrido de `modo` NO puede abarcar todo `src`: `modo` es un nombre
 * genérico que otro dominio puede usar legítimamente — p. ej. el
 * discriminador `modo` del bloque de continuidad de la Inspección de Obra
 * (`liquidacion_tipo.continuidad.modo`), que viaja DENTRO de `continuidad` y
 * NO es un selector de vista del modal de comprobante.
 *
 * El contrato de `unified-comprobante-modal` es "el modal de comprobante no
 * se bifurca por `modo`", y eso se vigila sobre el modal y quien lo monta.
 * Con el barrido global, cualquier otro dominio que usara la palabra `modo`
 * rompía una guarda que no le atañe.
 */
const FUENTES_MODAL_COMPROBANTE = [
  ...MONTajes_MODAL,
  ...FUENTES.filter((fuente) => fuente.relativo === RELATIVO_MODAL),
];

describe("ComprobanteFormModal — implementación ÚNICA (guardas de fuente)", () => {
  it("el frontend NO usa el modo 'crear' del modal", () => {
    const infractores = FUENTES.filter((fuente) =>
      fuente.contenido.includes('modo="crear"'),
    ).map((fuente) => fuente.relativo);

    expect(infractores).toEqual([]);
  });

  it("cada punto de entrada monta UNA sola instancia del modal", () => {
    const montajes = MONTajes_MODAL;

    // Si nadie montase el modal, la guarda no vigilaría nada.
    expect(montajes.length).toBeGreaterThan(0);

    for (const montaje of montajes) {
      const instancias = montaje.contenido.match(REGEX_INSTANCIA) ?? [];
      expect({
        fichero: montaje.relativo,
        instancias: instancias.length,
      }).toEqual({ fichero: montaje.relativo, instancias: 1 });
    }
  });

  it("el modal NO declara prop `modo` ni mantiene una segunda implementación", () => {
    const modal = FUENTES.find((fuente) => fuente.relativo === RELATIVO_MODAL);
    expect(modal).toBeDefined();
    const contenido = modal?.contenido ?? "";

    // La interfaz pública del modal NO tiene prop `modo`.
    const inicio = contenido.indexOf("interface ComprobanteFormModalProps");
    expect(inicio).toBeGreaterThan(-1);
    const bloqueProps = contenido.slice(inicio, contenido.indexOf("}", inicio));
    expect(bloqueProps).not.toContain("modo");

    // Ni el tipo público del modo, ni la segunda implementación ("crear").
    expect(contenido).not.toContain("ModoComprobante");
    expect(contenido).not.toContain("ComprobanteFormModalCrear");

    // El export renderiza SIEMPRE la implementación de gestión.
    expect(
      contenido.match(/<ComprobanteFormModalGestionar/g) ?? [],
    ).toHaveLength(1);
    // Y no queda ninguna rama de render por "modo".
    expect(contenido).not.toMatch(/if\s*\(\s*modo\s*===/);
  });

  it("ningún punto de entrada DECLARA una prop `modo`", () => {
    const infractores = FUENTES_MODAL_COMPROBANTE.filter((fuente) =>
      /^\s*modo\??\s*:/m.test(fuente.contenido),
    ).map((fuente) => fuente.relativo);

    expect(infractores).toEqual([]);
  });

  it("ningún punto de entrada PASA un selector de modo al modal", () => {
    // El browse RH era el último call site que pasaba `modo="gestionar"`.
    // Ya no hay ninguno: el modal es ÚNICO y deriva su vista del comprobante
    // vigente real.
    const infractores = FUENTES_MODAL_COMPROBANTE.filter((fuente) =>
      /\bmodo\s*=/.test(fuente.contenido),
    ).map((fuente) => fuente.relativo);

    expect(infractores).toEqual([]);
  });
});
