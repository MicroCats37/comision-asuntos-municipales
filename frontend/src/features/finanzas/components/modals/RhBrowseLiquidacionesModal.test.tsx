/**
 * RhBrowseLiquidacionesModal — browse de liquidaciones EXISTENTES del RH.
 *
 * Contrato de la capability `rh-mensual-browse-edit` (Slice C):
 * - el browse usa el panel y el contrato de filtros de LIQUIDACIONES
 *   (`LiquidacionFiltroModal` + `LiquidacionFiltros`), no el de candidatas;
 * - los filtros del wizard sólo SIEMBLAN los compatibles y NO limitan la
 *   búsqueda más allá de los filtros de Liquidaciones activos;
 * - NO hay filtro municipal implícito;
 * - los filtros no soportados por el endpoint activo se OMITEN de forma
 *   explícita (se avisa al usuario);
 * - la paginación se restablece al cambiar o limpiar los filtros;
 * - la tarjeta de cada liquidación se renderiza con el componente CENTRALIZADO
 *   `LiquidacionCardShell` (el mismo de las listas de Liquidaciones): el
 *   browse NO dibuja una segunda tarjeta;
 * - la tarjeta expone las acciones "Delegados", "Gestionar comprobante" y
 *   "Ver detalle": el browse NO dibuja una acción de alta y otra de edición
 *   del comprobante, sino UNA que abre el flujo único de gestión;
 * - el browse NUNCA crea revisiones ni liquidaciones: abre flujos de mutación
 *   sobre una liquidación CONCRETA (comprobante y delegados) y nada más;
 * - NUNCA invoca (ni importa) una mutación de nueva revisión;
 * - la acción "Delegados" abre el modal DEDICADO de asignaciones
 *   (`LiquidacionDelegadoDetailModal`), NO el modal genérico de gestión de
 *   delegados: el browse NO implementa su propia lógica de borrado;
 * - el browse monta UN SOLO `ComprobanteFormModal`: ni dos instancias del
 *   modal, ni diálogos separados de alta y de edición, ni selector de modo;
 * - el browse NO se suscribe al `mutationCache`: la invalidación del listado
 *   es EXPLÍCITA (la hace el hook de mutación). Los flujos de COMPROBANTE
 *   terminan en un `refetch()` EXPLÍCITO del listado.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (`sdd-verify`).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { ComponentProps, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: mocks.apiGet,
    post: mocks.apiPost,
    patch: mocks.apiPatch,
    put: mocks.apiPut,
    delete: mocks.apiDelete,
  },
}));

/**
 * El panel de filtros de LIQUIDACIONES se stubbea: el browse sólo lo integra
 * (recibe `initialFiltros` y aplica lo que devuelve `onApply`).
 *
 * El flujo de comprobante también se stubbea: el browse lo integra (recibe la
 * liquidación objetivo y dispara `onSuccess`). El stub NO declara prop `modo`:
 * el modal público es ÚNICO y deriva su vista del comprobante vigente. El
 * contrato de Runtime del PATCH de edición (un PATCH, ningún POST, sin
 * `monto`) lo fija `ComprobanteFormModal.gestionar.test.tsx`; aquí se fija el
 * CONTRATO del browse: a qué liquidación apunta y cuándo refresca el listado.
 */
vi.mock("@/features/liquidaciones/components/forms", () => ({
  LiquidacionFiltroModal: ({
    open,
    initialFiltros,
    onApply,
  }: {
    open: boolean;
    initialFiltros?: Record<string, unknown>;
    onApply: (filtros: Record<string, unknown>) => void;
  }) =>
    open ? (
      <div data-testid="filtro-liquidaciones-modal">
        <span data-testid="filtros-iniciales">
          {JSON.stringify(initialFiltros ?? {})}
        </span>
        <button
          type="button"
          onClick={() =>
            onApply({
              entidad_id: "mun-1",
              distrito_id: "dis-1",
              propietario: "ACME S.A.",
              razon_social: "ACME S.A.",
              documento: "20123456789",
              numero: 88,
              comprobante_serie: "F001",
              comprobante_numero: "55",
            })
          }
        >
          Aplicar Filtros
        </button>
        <button type="button" onClick={() => onApply({})}>
          Aplicar Sin Filtros
        </button>
      </div>
    ) : null,
  ComprobanteFormModal: ({
    open,
    liquidacionGeneral,
    onSuccess,
  }: {
    open: boolean;
    liquidacionGeneral: { id: string };
    onSuccess?: (updated: unknown) => void;
  }) =>
    open ? (
      <div data-testid="comprobante-modal">
        <span>{`objetivo:${liquidacionGeneral.id}`}</span>
        <button
          type="button"
          onClick={() =>
            onSuccess?.({
              id: liquidacionGeneral.id,
              comprobantes: [
                {
                  id: "c-2",
                  tipo_comprobante: "FACTURA",
                  serie: "F002",
                  numero: "99",
                  fecha_emision: "2026-02-01",
                  monto: 118,
                  activo: true,
                  motivo_reemplazo: null,
                },
              ],
            })
          }
        >
          Guardar comprobante
        </button>
      </div>
    ) : null,
}));

/**
 * El modal DEDICADO de asignaciones se stubbea: el browse sólo lo abre con el
 * contexto crudo de la fila (`raw.liquidacion_general`) y con el endpoint
 * activo del browse (para que el hook de mutación pueda invalidar el listado).
 *
 * El browse NO implementa la remoción: la emite el hook compartido
 * `useQuitarDelegadoLiquidacion` (PATCH batch `{ delete: [{ delegado_id }] }`),
 * cuya invalidación de caché se verifica en
 * `useQuitarDelegadoLiquidacion.test.ts`.
 */
vi.mock(
  "@/features/liquidaciones/components/LiquidacionDelegadoDetailModal",
  () => ({
    LiquidacionDelegadoDetailModal: ({
      open,
      liquidacionGeneral,
      rhBrowseEndpoint,
    }: {
      open: boolean;
      liquidacionGeneral: { id: string };
      rhBrowseEndpoint?: string | null;
    }) =>
      open ? (
        <div data-testid="delegados-modal">
          <span>{`objetivo:${liquidacionGeneral.id}`}</span>
          <span data-testid="delegados-endpoint">
            {rhBrowseEndpoint ?? "-"}
          </span>
        </div>
      ) : null,
  }),
);

/** Municipalidades y distritos: sólo se usan para etiquetar los chips. */
vi.mock("@/features/liquidaciones/hooks/useMunicipalidades", () => ({
  useMunicipalidades: () => ({
    data: [
      {
        id: "mun-1",
        nombre: "Municipalidad Uno",
        codigo: "001",
        provincia: null,
        distrito: null,
      },
    ],
  }),
}));

vi.mock("@/features/liquidaciones/hooks/useDistritos", () => ({
  useDistritos: () => ({
    data: [
      {
        id: "dis-1",
        nombre: "Distrito Uno",
        provinciaNombre: "Provincia Uno",
        departamentoNombre: "Departamento Uno",
      },
    ],
  }),
}));

vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: ({ id }: { id: string | null }) => ({
    data: id
      ? {
          liquidacion_general: { id, estado: "PENDIENTE", uit: null },
          liquidacion_especifica: { id: "le-1", numero: 88 },
          liquidacion_tipo: null,
        }
      : undefined,
    isLoading: false,
  }),
}));

vi.mock("@/features/liquidaciones/components/detail", () => ({
  composeDetalleSections: () => <div>detalle</div>,
  getTipoDetalleSection: () => null,
  LiquidacionDetalleModal: ({
    open,
    children,
  }: {
    open: boolean;
    children: ReactNode;
  }) => (open ? <div data-testid="detalle-modal">{children}</div> : null),
}));

import { RhBrowseLiquidacionesModal } from "./RhBrowseLiquidacionesModal";

const LIQUIDACION_GENERAL = {
  id: "lg-1",
  estado: "PENDIENTE",
  municipalidad: { id: "m-1", codigo: "001", nombre: "Municipalidad Uno" },
  usuario_creador: null,
  fecha_registro: "2026-01-15",
  expediente: "EXP-001",
  observacion: null,
  numero_revision: 1,
  sub_total: 100,
  total: 118,
  legacy: false,
  codigo_cta: null,
  igv: null,
  uit: null,
  proyecto: {
    id: "p-1",
    nombre_propietario: "ACME S.A.",
    direccion: "Av. Siempre Viva 742",
    urbanizacion: null,
    distrito: null,
    entidad: {
      tipo_documento: "RUC",
      numero_documento: "20123456789",
      razon_social: "ACME S.A.",
    },
  },
  denominacion_de_proyecto: "Edificio Central",
  contacto: null,
  tipo_liquidacion: { codigo: "EDIFICACION", nombre: "Edificación" },
  delegados: [],
  comprobantes: [
    {
      id: "c-1",
      tipo_comprobante: "FACTURA",
      serie: "F001",
      numero: "55",
      fecha_emision: "2026-01-20",
      monto: 118,
      activo: true,
      motivo_reemplazo: null,
    },
  ],
};

/** Segunda liquidación: SIN comprobante activo (arranca en el alta). */
const LIQUIDACION_SIN_COMPROBANTE = {
  ...LIQUIDACION_GENERAL,
  id: "lg-2",
  expediente: "EXP-002",
  municipalidad: { id: "m-2", codigo: "002", nombre: "Municipalidad Dos" },
  sub_total: 40,
  total: 47.2,
  proyecto: {
    ...LIQUIDACION_GENERAL.proyecto,
    id: "p-2",
    nombre_propietario: "BETA S.A.",
    direccion: "Av. Otra Calle 100",
    entidad: {
      tipo_documento: "RUC",
      numero_documento: "20999999999",
      razon_social: "BETA S.A.",
    },
  },
  denominacion_de_proyecto: "Edificio Norte",
  comprobantes: [],
};

const ENVELOPE = {
  success: true,
  data: {
    items: [
      {
        liquidacion_general: LIQUIDACION_GENERAL,
        liquidacion_especifica: { id: "le-1", numero: 88 },
      },
      {
        liquidacion_general: LIQUIDACION_SIN_COMPROBANTE,
        liquidacion_especifica: { id: "le-2", numero: 99 },
      },
    ],
    total: 45,
    page: 1,
    page_size: 20,
    total_pages: 3,
  },
  error: null,
};

/** Parámetros de la última petición al listado de liquidaciones. */
function paramsDeListado() {
  const llamada = [...mocks.apiGet.mock.calls]
    .reverse()
    .find(([url]) => String(url).includes("/liquidaciones/"));
  return llamada?.[1]?.params ?? {};
}

/** URL de la última petición al listado de liquidaciones. */
function urlDeListado() {
  const llamada = [...mocks.apiGet.mock.calls]
    .reverse()
    .find(([url]) => String(url).includes("/liquidaciones/"));
  return String(llamada?.[0] ?? "");
}

/** Renderiza el browse con su QueryClientProvider. */
function renderBrowse(
  props: Partial<ComponentProps<typeof RhBrowseLiquidacionesModal>> = {},
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RhBrowseLiquidacionesModal open onOpenChange={vi.fn()} {...props} />
    </QueryClientProvider>,
  );
}

/**
 * Lee el fuente de un fichero del frontend para los guardas de arquitectura.
 *
 * Se resuelve desde `process.cwd()` (raíz del frontend) con un fallback para
 * cuando los tests se lanzan desde la raíz del repositorio.
 */
function leerFuente(relativa: string): string {
  const candidatos = [
    resolve(process.cwd(), relativa),
    resolve(process.cwd(), "frontend", relativa),
  ];
  const encontrado = candidatos.find((candidato) => existsSync(candidato));
  if (!encontrado) {
    throw new Error(`No se encontró el fuente ${relativa}`);
  }
  return readFileSync(encontrado, "utf8");
}

/** Fuente del browse (guardas de arquitectura). */
function leerFuenteBrowse(): string {
  return leerFuente(
    "src/features/finanzas/components/modals/RhBrowseLiquidacionesModal.tsx",
  );
}

/** Fuente del hook de edición del comprobante (guardas del PATCH). */
function leerFuenteHookEditar(): string {
  return leerFuente(
    "src/features/liquidaciones/hooks/useEditarComprobante.ts",
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.apiGet.mockResolvedValue({ data: ENVELOPE });
});

describe("RhBrowseLiquidacionesModal — panel de filtros de Liquidaciones", () => {
  it("siembra los filtros compatibles del wizard y NO filtra por municipalidad", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: {
        expediente: "EXP-001",
        numero: "88",
        propietario: "ACME S.A.",
        direccion: "Av. Siempre Viva 742",
      },
      fechaDesde: "2026-01-01",
      fechaHasta: "2026-12-31",
      municipalidadNombre: "Municipalidad Uno",
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    expect(urlDeListado()).toBe("/liquidaciones/edificaciones/");
    expect(paramsDeListado()).toMatchObject({
      expediente: "EXP-001",
      numero: 88,
      propietario: "ACME S.A.",
      direccion: "Av. Siempre Viva 742",
      fecha_desde: "2026-01-01",
      fecha_hasta: "2026-12-31",
      page: 1,
      page_size: 20,
    });

    // La municipalidad de la operatividad es CONTEXTO, no un filtro.
    expect(paramsDeListado()).not.toHaveProperty("entidad_id");
  });

  it("envía los campos EXACTOS de Liquidaciones al endpoint por tipo", async () => {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));

    await waitFor(() =>
      expect(paramsDeListado()).toMatchObject({
        entidad_id: "mun-1",
        distrito_id: "dis-1",
        propietario: "ACME S.A.",
        razon_social: "ACME S.A.",
        documento: "20123456789",
        numero: 88,
        comprobante_serie: "F001",
        comprobante_numero: "55",
      }),
    );
  });

  it("el panel de Liquidaciones recibe los filtros activos como estado inicial", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: { expediente: "EXP-001", propietario: "ACME S.A." },
      fechaDesde: "2026-01-01",
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));

    const iniciales = JSON.parse(
      screen.getByTestId("filtros-iniciales").textContent ?? "{}",
    );
    expect(iniciales).toMatchObject({
      expediente: "EXP-001",
      propietario: "ACME S.A.",
      fecha_desde: "2026-01-01",
    });
  });

  it("el panel reemplaza los filtros que edita y conserva el expediente sembrado", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: { expediente: "EXP-001", propietario: "ACME S.A." },
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));

    await waitFor(() =>
      expect(paramsDeListado()).toMatchObject({ entidad_id: "mun-1" }),
    );
    // El expediente no lo expone el panel → se conserva.
    expect(paramsDeListado()).toMatchObject({ expediente: "EXP-001" });
  });

  it("elimina los filtros que el usuario borra en el panel", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: { expediente: "EXP-001", propietario: "ACME S.A." },
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());
    expect(paramsDeListado()).toMatchObject({ expediente: "EXP-001" });

    // El panel añade varios filtros activos.
    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));
    await waitFor(() =>
      expect(paramsDeListado()).toMatchObject({ entidad_id: "mun-1" }),
    );

    // Quitar un filtro concreto.
    fireEvent.click(
      screen.getByRole("button", { name: "Quitar filtro Expediente: EXP-001" }),
    );

    await waitFor(() =>
      expect(paramsDeListado()).not.toHaveProperty("expediente"),
    );

    // Y "Limpiar todo" vacía el resto.
    fireEvent.click(screen.getByRole("button", { name: /Limpiar todo/ }));
    await waitFor(() =>
      expect(paramsDeListado()).not.toHaveProperty("entidad_id"),
    );
  });

  it("muestra los filtros activos como chips (con el nombre de municipalidad y distrito)", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: { expediente: "EXP-001" },
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));

    await waitFor(() => expect(screen.getByText("Filtros activos:")).toBeTruthy());
    expect(screen.getByText("Expediente:")).toBeTruthy();
    // La municipalidad y el distrito se muestran por NOMBRE, no por id.
    expect(
      screen.getByRole("button", {
        name: "Quitar filtro Municipalidad: Municipalidad Uno",
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: "Quitar filtro Distrito: Distrito Uno",
      }),
    ).toBeTruthy();
  });

  it("permite quitar un filtro activo y limpiar todos", async () => {
    renderBrowse({
      tipoCodigo: "EDIFICACION",
      filtros: { expediente: "EXP-001" },
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());
    expect(paramsDeListado()).toMatchObject({ expediente: "EXP-001" });

    // El panel añade varios filtros activos.
    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));
    await waitFor(() =>
      expect(paramsDeListado()).toMatchObject({ entidad_id: "mun-1" }),
    );

    // Quitar un filtro concreto.
    fireEvent.click(
      screen.getByRole("button", { name: "Quitar filtro Expediente: EXP-001" }),
    );

    await waitFor(() =>
      expect(paramsDeListado()).not.toHaveProperty("expediente"),
    );

    // Y "Limpiar todo" vacía el resto.
    fireEvent.click(screen.getByRole("button", { name: /Limpiar todo/ }));
    await waitFor(() =>
      expect(paramsDeListado()).not.toHaveProperty("entidad_id"),
    );
  });

  it("omite de forma explícita los filtros no soportados por el listado cross-tipo", async () => {
    renderBrowse({
      tipoCodigo: null,
      filtros: { expediente: "EXP-001", numero: "88" },
      fechaDesde: "2026-01-01",
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    expect(urlDeListado()).toBe("/liquidaciones/generales/");
    // El listado cross-tipo no admite `numero` ni el rango de fechas.
    expect(paramsDeListado()).not.toHaveProperty("numero");
    expect(paramsDeListado()).not.toHaveProperty("fecha_desde");
    // …y la omisión se avisa al usuario.
    const aviso = screen.getByRole("note");
    expect(aviso.textContent).toContain("Número");
    expect(aviso.textContent).toContain("Fecha Desde");
  });

  it("restablece la paginación al aplicar y al limpiar los filtros", async () => {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    // El usuario avanza a la página 2.
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    await waitFor(() => expect(paramsDeListado()).toMatchObject({ page: 2 }));

    // Aplicar filtros vuelve a la página 1.
    fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));
    await waitFor(() => expect(paramsDeListado()).toMatchObject({ page: 1 }));

    // Y limpiar los filtros también.
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    await waitFor(() => expect(paramsDeListado()).toMatchObject({ page: 2 }));

    fireEvent.click(screen.getByRole("button", { name: /Limpiar todo/ }));
    await waitFor(() => expect(paramsDeListado()).toMatchObject({ page: 1 }));
  });
});

describe("RhBrowseLiquidacionesModal — arquitectura del browse", () => {
  it("usa el panel de filtros de Liquidaciones y NO el de candidatas", () => {
    const source = leerFuenteBrowse();

    // Panel y contrato de Liquidaciones.
    expect(source).toContain("LiquidacionFiltroModal");
    expect(source).toContain("LiquidacionFiltros");

    // Sin panel de filtros de CANDIDATAS en el browse.
    expect(source).not.toContain("RHCandidatasFiltroModal");
    expect(source).not.toContain("RHActiveFiltersPanel");
    expect(source).not.toContain("countActiveFiltros");
    expect(source).not.toContain("RhDatePickerField");
  });

  it("nunca importa ni invoca una mutación de nueva revisión", () => {
    const source = leerFuenteBrowse();

    expect(source).not.toMatch(/useCrearNuevaRevision/);
    expect(source).not.toMatch(/nueva-revision/);
    expect(source).not.toMatch(/nueva_revision/);
  });

  it("renderiza la tarjeta con el shell CENTRALIZADO (no una segunda tarjeta)", () => {
    const source = leerFuenteBrowse();

    // La tarjeta del browse es el shell que usan las listas de Liquidaciones.
    expect(source).toContain("LiquidacionCardShell");
    expect(source).toContain("LiquidacionCardShell }");

    // El browse NO implementa su propia lógica de borrado de delegados:
    // abre el modal DEDICADO, que usa el hook de remoción compartido.
    expect(source).toContain("LiquidacionDelegadoDetailModal");
    expect(source).not.toContain("GestionarDelegadosModal");
    expect(source).not.toContain("useQuitarDelegadoLiquidacion");

    // El browse no escribe directamente contra la API.
    expect(source).not.toMatch(/api\.(post|patch|put|delete)\(/);
  });

  it("NO se suscribe al mutationCache: la invalidación del listado es explícita", () => {
    const source = leerFuenteBrowse();

    // La suscripción al `mutationCache` era el mecanismo OBSOLETO: el modal
    // dedicado invalida el listado del browse desde su propio hook.
    expect(source).not.toMatch(/getMutationCache/);
    expect(source).not.toMatch(/\.subscribe\(/);
  });
});

describe("RhBrowseLiquidacionesModal — tarjeta jerárquica", () => {
  /** Renderiza el browse con liquidaciones existentes. */
  async function renderBrowseConItems() {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });
    await waitFor(() => expect(screen.getByText("EXP-001")).toBeInTheDocument());
  }

  it("conserva la información de la fila y la jerarquía de la tarjeta", async () => {
    await renderBrowseConItems();

    // Expediente, comprobante vigente, propietario, total, tipo, estado,
    // municipalidad y fecha de registro siguen visibles.
    expect(screen.getByText("EXP-001")).toBeInTheDocument();
    expect(screen.getByText("ACME S.A.")).toBeInTheDocument();
    expect(screen.getByText("Edificio Central")).toBeInTheDocument();
    expect(screen.getByText("Municipalidad Uno")).toBeInTheDocument();
    expect(screen.getByText("Av. Siempre Viva 742")).toBeInTheDocument();
    // El ID público con el formato de las vistas por tipo.
    expect(screen.getByText("EDIF-2026-000088")).toBeInTheDocument();
    // El comprobante vigente se muestra en la tarjeta.
    expect(screen.getByText(/FACTURA/)).toBeInTheDocument();
    expect(screen.getByText(/F001/)).toBeInTheDocument();
    // El total con el formato de la tarjeta.
    expect(screen.getByText("S/ 118.00")).toBeInTheDocument();
  });

  it("abre el detalle de solo lectura desde la tarjeta", async () => {
    await renderBrowseConItems();

    fireEvent.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    await waitFor(() =>
      expect(screen.getByTestId("detalle-modal")).toBeInTheDocument(),
    );
  });
});

describe("RhBrowseLiquidacionesModal — acción de delegados", () => {
  /** Renderiza el browse con liquidaciones existentes. */
  async function renderBrowseConItems() {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });
    await waitFor(() => expect(screen.getByText("EXP-001")).toBeInTheDocument());
  }

  it("abre el modal DEDICADO de asignaciones con el payload CRUDO de la fila", async () => {
    await renderBrowseConItems();

    fireEvent.click(screen.getAllByRole("button", { name: "Delegados" })[0]);

    await waitFor(() =>
      expect(screen.getByTestId("delegados-modal")).toBeInTheDocument(),
    );
    // Es el modal DEDICADO el que se abre (y no otro flujo de la tarjeta).
    expect(screen.queryByTestId("detalle-modal")).toBeNull();
    expect(screen.queryByTestId("comprobante-modal")).toBeNull();
    // El objetivo es la liquidación EXACTA de la tarjeta.
    expect(screen.getByTestId("delegados-modal")).toHaveTextContent(
      "objetivo:lg-1",
    );
  });

  it("el modal dedicado recibe el id de la liquidación de la tarjeta", async () => {
    await renderBrowseConItems();

    fireEvent.click(screen.getAllByRole("button", { name: "Delegados" })[0]);

    await waitFor(() =>
      expect(screen.getByTestId("delegados-modal")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("delegados-modal")).toHaveTextContent(
      "objetivo:lg-1",
    );
  });

  it("el modal dedicado recibe el endpoint ACTIVO del browse", async () => {
    await renderBrowseConItems();

    fireEvent.click(screen.getAllByRole("button", { name: "Delegados" })[0]);

    await waitFor(() =>
      expect(screen.getByTestId("delegados-modal")).toBeInTheDocument(),
    );
    // El endpoint permite al hook de mutación invalidar ESTE listado.
    expect(screen.getByTestId("delegados-endpoint")).toHaveTextContent(
      "/liquidaciones/edificaciones/",
    );
  });

  it("el browse NO implementa su propia lógica de borrado de delegados", () => {
    const source = leerFuenteBrowse();

    // El browse abre el modal DEDICADO y no el genérico de gestión.
    expect(source).toContain("LiquidacionDelegadoDetailModal");
    expect(source).not.toContain("GestionarDelegadosModal");
    // Y no instancia el hook de remoción: la remoción es del modal.
    expect(source).not.toContain("useQuitarDelegadoLiquidacion");
    // Ni escribe contra la API.
    expect(source).not.toMatch(/api\.(post|patch|put|delete)\(/);
  });
});

describe("RhBrowseLiquidacionesModal — acción ÚNICA de comprobante", () => {
  /** Renderiza el browse con liquidaciones existentes. */
  async function renderBrowseConItems() {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });
    await waitFor(() => expect(screen.getByText("EXP-001")).toBeInTheDocument());
  }

  it("la tarjeta expone UNA sola acción de comprobante: «Gestionar comprobante»", async () => {
    await renderBrowseConItems();

    // Las DOS liquidaciones (con y sin comprobante vigente) tienen la MISMA
    // acción: el flujo de gestión es único.
    expect(
      screen.getAllByRole("button", { name: "Gestionar comprobante" }),
    ).toHaveLength(2);

    // Y NO hay acciones separadas de alta/reemplazo ni de edición.
    expect(
      screen.queryByRole("button", { name: "Agregar comprobante" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Reemplazar comprobante" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Editar comprobante" }),
    ).toBeNull();
  });

  it("abre UN SOLO modal de comprobante con la liquidación correcta", async () => {
    await renderBrowseConItems();

    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[0],
    );

    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );
    // UNA sola instancia del modal (no dos: alta y edición).
    expect(screen.getAllByTestId("comprobante-modal")).toHaveLength(1);
    // El objetivo es la liquidación EXACTA de la tarjeta.
    expect(screen.getByTestId("comprobante-modal")).toHaveTextContent(
      "objetivo:lg-1",
    );
    // Y es el flujo ÚNICO de gestión (resumen → alta/reemplazo → edición): el
    // modal NO recibe ningún selector de modo, deriva la vista del vigente.
    expect(leerFuenteBrowse()).not.toMatch(/\bmodo=/);
  });

  it("la acción apunta a la liquidación de la fila desde la que se dispara", async () => {
    await renderBrowseConItems();

    // La segunda liquidación NO tiene comprobante vigente: el flujo arranca
    // en el formulario de alta, pero es el MISMO modal.
    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[1],
    );

    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("comprobante-modal")).toHaveTextContent(
      "objetivo:lg-2",
    );
    expect(screen.getAllByTestId("comprobante-modal")).toHaveLength(1);
  });

  it("refresca el listado tras guardar el comprobante", async () => {
    await renderBrowseConItems();

    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[0],
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    const llamadasAntes = mocks.apiGet.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    // Refetch EXPLÍCITO del listado: sin él el comprobante vigente de la
    // fila seguiría mostrando el valor anterior.
    await waitFor(() =>
      expect(mocks.apiGet.mock.calls.length).toBeGreaterThan(llamadasAntes),
    );
    // El flujo de comprobante se cierra tras el éxito.
    expect(screen.queryByTestId("comprobante-modal")).toBeNull();
  });

  it("refresca el listado con un refetch() EXPLÍCITO (no depende del parche de caché)", async () => {
    await renderBrowseConItems();

    /** Peticiones al listado del browse (su endpoint de liquidaciones). */
    const llamadasBrowse = () =>
      mocks.apiGet.mock.calls.filter(([url]) =>
        String(url).includes("/liquidaciones/"),
      ).length;

    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[0],
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    const llamadasAntes = llamadasBrowse();

    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    // El browse RE-LEE su propio listado (una nueva petición a SU endpoint):
    // sin esto, el comprobante vigente de la fila no se actualiza.
    await waitFor(() => expect(llamadasBrowse()).toBeGreaterThan(llamadasAntes));
    expect(urlDeListado()).toBe("/liquidaciones/edificaciones/");

    // Y NO se apoya en el parche estándar de liquidaciones: la clave del
    // browse (`["rh-browse", …]`) queda FUERA del prefijo `["liquidaciones"]`
    // que parchea `useComprobanteCacheSync`, así que ese helper no lo toca.
    const cacheSync = leerFuente(
      "src/features/liquidaciones/hooks/cache/useComprobanteCacheSync.ts",
    );
    expect(cacheSync).toContain(
      'LISTAS_COMPROBANTE_KEY_PREFIX = ["liquidaciones"]',
    );

    const hookBrowse = leerFuente(
      "src/features/finanzas/hooks/useRhBrowseLiquidaciones.ts",
    );
    expect(hookBrowse).toContain(
      'queryKey: ["rh-browse", "liquidaciones", endpoint]',
    );

    // El browse llama explícitamente a `refetch()` en el `onSuccess` del modal.
    expect(leerFuenteBrowse()).toContain("void refetch();");
  });

  it("la acción de comprobante no crea revisiones", async () => {
    await renderBrowseConItems();

    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[0],
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    // Ninguna escritura del browse apunta a una revisión.
    const urls = [
      ...mocks.apiPost.mock.calls,
      ...mocks.apiPatch.mock.calls,
      ...mocks.apiPut.mock.calls,
    ].map((llamada) => String(llamada[0]));
    expect(urls.some((url) => url.includes("revision"))).toBe(false);
  });

  it("el browse monta UN SOLO ComprobanteFormModal (no dos instancias)", () => {
    const source = leerFuenteBrowse();

    // Una única instancia del modal de comprobante en todo el browse.
    const instancias = source.match(/<ComprobanteFormModal/g) ?? [];
    expect(instancias).toHaveLength(1);

    // Y es el flujo ÚNICO de gestión: no hay un modal de alta y otro de
    // edición, ni selector de modo (el modal deriva la vista del vigente).
    expect(source).not.toMatch(/\bmodo=/);
    expect(source).not.toContain("ComprobanteFormModalCrear");
  });
});

describe("RhBrowseLiquidacionesModal — el browse NO crea revisiones ni liquidaciones", () => {
  /** Renderiza el browse con liquidaciones existentes. */
  async function renderBrowseConItems() {
    renderBrowse({ tipoCodigo: "EDIFICACION", filtros: {} });
    await waitFor(() => expect(screen.getByText("EXP-001")).toBeInTheDocument());
  }

  it("no emite solicitudes de creación de revisión ni de creación de liquidación", async () => {
    await renderBrowseConItems();

    // Listar y navegar no escribe: ni liquidaciones, ni comprobantes, ni
    // revisiones.
    expect(mocks.apiPost).not.toHaveBeenCalled();
    expect(mocks.apiPatch).not.toHaveBeenCalled();
    expect(mocks.apiPut).not.toHaveBeenCalled();
    expect(mocks.apiDelete).not.toHaveBeenCalled();

    // Tampoco al abrir el flujo de comprobante: el browse NO escribe, sólo
    // abre el flujo sobre una liquidación concreta.
    fireEvent.click(
      screen.getAllByRole("button", { name: "Gestionar comprobante" })[0],
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    await waitFor(() => expect(mocks.apiGet.mock.calls.length).toBeGreaterThan(1));

    // Ninguna escritura crea una revisión ni una liquidación.
    expect(mocks.apiPost).not.toHaveBeenCalled();
    const urls = [
      ...mocks.apiPatch.mock.calls,
      ...mocks.apiPut.mock.calls,
      ...mocks.apiDelete.mock.calls,
    ].map((llamada) => String(llamada[0]));
    expect(urls.some((url) => url.includes("revision"))).toBe(false);
    expect(urls.some((url) => url.includes("nueva-liquidacion"))).toBe(false);
  });

  it("la EDICIÓN emite un PATCH al recurso del comprobante y NINGÚN POST", () => {
    // El browse monta el flujo ÚNICO de comprobante: la escritura de la
    // edición la hace el hook `useEditarComprobante` (PATCH in-place).
    const fuente = leerFuenteHookEditar();

    expect(fuente).toContain("api.patch(");
    expect(fuente).toContain("/comprobante/${comprobanteId}");
    expect(fuente).not.toContain("api.post(");

    // Y el browse monta UNA sola instancia del modal, sin selector de modo.
    const browse = leerFuenteBrowse();
    expect(browse.match(/<ComprobanteFormModal/g) ?? []).toHaveLength(1);
    expect(browse).not.toMatch(/\bmodo=/);
  });

  it("el cuerpo del PATCH de edición NO incluye el monto", () => {
    const fuente = leerFuenteHookEditar();

    // El payload que construye el hook no declara `monto`:
    const payload = fuente.slice(
      fuente.indexOf("function buildEditarComprobantePayload"),
    );
    expect(payload.slice(0, payload.indexOf("\n}"))).not.toContain("monto");

    // Y el SCHEMA de entrada tampoco: `monto` no forma parte del contrato
    // (espejo de `LiquidacionComprobanteUpdateIn` del backend).
    const esquema = leerFuente(
      "src/features/liquidaciones/schemas/liquidacion-base.schema.ts",
    );
    const bloque = esquema.slice(
      esquema.indexOf("export const EditarComprobanteInputSchema"),
    );
    expect(bloque.slice(0, bloque.indexOf("\n});"))).not.toContain("monto");
  });
});
