/**
 * LiquidacionCardShell — Card base común de liquidación (PARTE BASE).
 *
 * Estructura:
 * 1. <article> wrapper con grid 2-col [card-main | card-summary]
 *    - card-main (flex-1):
 *      - card-header (icon + ID + Rev + tipo + fecha + status)
 *      - identity-grid 2-col (Contribuyente | Proyecto/Trámite)
 *      - meta-strip (Expediente | Municipalidad | Sin comprobante)
 *    - card-summary (300px):
 *      - total-block (gran total)
 *      - financials 2-col (Subtotal | IGV)
 * 2. card-footer (Dirección | Acciones)
 *
 * La PARTE ESPECÍFICA por tipo se inyecta desde cada card via `delegadosSlot`
 * (renderiza un bloque custom con el detalle del cálculo según el motor:
 * PorcentajeObra (Edif/Taludes/IV) → Valor declarado + % Liquidación + Especialidades;
 * M2 (HU/MS) → Área + Costo por m²;
 * Visitas (IO) → Cantidad + Categoría + Inspector + CIP).
 *
 * Colores: rose/red para categorías (Contribuyente, Proyecto), emerald
 * para Comprobante, primary para badges.
 */
import {
  Building2,
  Calendar,
  CheckCircle2,
  FileDown,
  FilePenLine,
  FileText,
  type LucideIcon,
  MapPin,
  Receipt,
  User,
  XCircle,
} from "lucide-react";
import type { ReactNode } from "react";
import {
  type CardActionItem,
  CardActionsMenu,
  formatCurrency,
  formatDate,
  LiquidacionCardAction,
} from "../liquidacion-ui";

export interface LiquidacionCardComprobante {
  tipo_comprobante?: string | null;
  serie?: string | null;
  numero?: string | null;
}

export function LiquidacionCardShell({
  kindIcon: KindIcon,
  kindLabel,
  publicId,
  estado,
  entidadNombre,
  entidadDocumento,
  proyectoNombre,
  proyectoUbicacion,
  municipalidadLabel,
  distritoLabel,
  expediente,
  direccion,
  comprobanteActivo,
  total,
  subTotal,
  igvMonto,
  fechaRegistro,
  numeroRevision,
  showDelegados = true,
  onDelegados,
  onPrint,
  canEdit = false,
  onEdit,
  onComprobante,
  onVerDetalle,
  calculoSlot,
  delegadosSlot,
  menuItems,
  primaryAction,
}: {
  kindIcon: LucideIcon;
  kindLabel?: string;
  publicId: string;
  estado?: string | null;
  entidadNombre: string;
  entidadDocumento?: string | null;
  proyectoNombre?: string | null;
  proyectoUbicacion?: string | null;
  municipalidadLabel: string;
  distritoLabel?: string;
  expediente?: string | null;
  direccion?: string | null;
  comprobanteActivo?: LiquidacionCardComprobante | null;
  total?: number;
  subTotal?: number | null;
  igvMonto?: number | null;
  fechaRegistro: string;
  numeroRevision?: number | null;
  showDelegados?: boolean;
  onDelegados?: () => void;
  onPrint?: () => void;
  canEdit?: boolean;
  onEdit?: () => void;
  onComprobante?: () => void;
  onVerDetalle?: () => void;
  calculoSlot?: ReactNode;
  delegadosSlot?: ReactNode;
  menuItems?: CardActionItem[];
  primaryAction?: ReactNode;
}) {
  const igvPct =
    subTotal != null && subTotal > 0 && total != null
      ? Math.round(((total - subTotal) / subTotal) * 100)
      : null;

  return (
    <article
      className="bg-white border border-neutral-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 300px",
        columnGap: "22px",
      }}
    >
      {/* ── card-main (flex-1) ── */}
      <div className="min-w-0">
        {/* card-header */}
        <div className="flex justify-between gap-3 items-start pb-3.5 border-b border-neutral-200">
          <div className="flex gap-2.5 min-w-0">
            {/* type-icon */}
            <div
              className="shrink-0 flex items-center justify-center rounded-xl"
              style={{
                width: "39px",
                height: "39px",
                backgroundColor: "#f8e7e6",
                border: "1px solid #edbfc1",
                color: "#a90c24",
              }}
            >
              <KindIcon className="h-4 w-4" strokeWidth={1.7} />
            </div>
            <div className="min-w-0">
              {/* reference-line */}
              <div className="flex items-center flex-wrap gap-2">
                <h2
                  className="m-0 text-base font-extrabold text-neutral-900 truncate"
                  title={publicId}
                >
                  {publicId}
                </h2>
                {numeroRevision != null && (
                  <span
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-bold"
                    style={{
                      color: "#a90c24",
                      backgroundColor: "#f8e7e6",
                      border: "1px solid #e6adb2",
                    }}
                    title={`Revisión #${numeroRevision}`}
                  >
                    <FileText className="h-2.5 w-2.5" />
                    Rev. {numeroRevision}
                  </span>
                )}
                {estado && estado !== "PENDIENTE" && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase"
                    style={{
                      color: "#078465",
                      backgroundColor: "#e9fbf4",
                      border: "1px solid #66dfb4",
                    }}
                  >
                    <span
                      className="inline-block rounded-full"
                      style={{
                        width: "5px",
                        height: "5px",
                        backgroundColor: "#09a575",
                      }}
                    />
                    {estado}
                  </span>
                )}
              </div>
              {/* type-label */}
              <p className="mt-1 text-xs text-neutral-500 flex items-center gap-2.5">
                {kindLabel && <span>{kindLabel}</span>}
                <span className="flex items-center gap-1 text-neutral-500">
                  <Calendar className="h-3 w-3" />
                  {formatDate(fechaRegistro)}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* identity-grid */}
        <div
          className="grid gap-2 mt-3.5"
          style={{ gridTemplateColumns: "1fr 1fr" }}
        >
          {/* Contribuyente */}
          <section
            className="bg-white rounded-xl p-3 min-w-0"
            style={{
              border: "1px solid #eadedf",
              boxShadow: "inset 3px 0 0 #dca0a5",
            }}
          >
            <span
              className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
              style={{ color: "#a90c24" }}
            >
              <User className="h-3 w-3" />
              Contribuyente
            </span>
            <strong className="block text-[13px] font-bold text-neutral-900 truncate">
              {entidadNombre}
            </strong>
            {entidadDocumento && (
              <span className="flex items-center gap-1 text-[11px] mt-1.5 truncate text-neutral-500">
                {entidadDocumento}
              </span>
            )}
          </section>

          {/* Proyecto / Trámite */}
          <section
            className="bg-white rounded-xl p-3 min-w-0"
            style={{
              border: "1px solid #eadedf",
              boxShadow: "inset 3px 0 0 #a90c24",
            }}
          >
            <span
              className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
              style={{ color: "#a90c24" }}
            >
              <FileText className="h-3 w-3" />
              Proyecto / trámite
            </span>
            <strong className="block text-[13px] font-bold text-neutral-900 truncate">
              {proyectoNombre || "—"}
            </strong>
            {proyectoUbicacion && (
              <span className="flex items-center gap-1 text-[11px] mt-1.5 truncate text-neutral-500">
                <MapPin className="h-3 w-3" />
                {proyectoUbicacion}
              </span>
            )}
          </section>
        </div>

        {/* meta-strip */}
        <div className="flex items-center gap-2 bg-white border border-neutral-200 rounded-lg mt-2 px-3 py-2.5 text-neutral-700 text-[11px] overflow-hidden">
          <span className="flex items-center gap-1 truncate min-w-0">
            <span className="text-[9px] font-bold text-neutral-500 uppercase tracking-wider mr-1">
              Expediente
            </span>
            <span className="font-bold text-neutral-700 truncate">
              {expediente || "—"}
            </span>
          </span>
          {expediente && <div className="shrink-0 w-px h-4 bg-neutral-300" />}
          <span
            className="flex items-center gap-1 px-2 py-0.5 rounded-md min-w-0"
            style={{
              backgroundColor: "#f8e7e6",
              border: "1px solid #ecc4c6",
              color: "#272124",
            }}
          >
            <Building2
              className="h-3 w-3 shrink-0"
              style={{ color: "#a90c24" }}
            />
            <span className="text-[9px] font-bold" style={{ color: "#a90c24" }}>
              Municipalidad
            </span>
            <span className="truncate">
              {municipalidadLabel}
              {distritoLabel ? ` · ${distritoLabel}` : ""}
            </span>
          </span>
          {comprobanteActivo ? (
            <span
              className="flex items-center gap-1 px-2 py-0.5 rounded-md ml-auto shrink-0 text-[11px] font-bold"
              style={{
                color: "#047857",
                backgroundColor: "#ecfdf5",
                border: "1px solid #a7f3d0",
              }}
            >
              <CheckCircle2 className="h-3 w-3" />
              {comprobanteActivo.tipo_comprobante} {comprobanteActivo.serie}-
              {comprobanteActivo.numero}
            </span>
          ) : (
            <span className="ml-auto shrink-0 text-[11px] text-neutral-400 italic">
              <XCircle className="inline h-3 w-3 mr-0.5" />
              Sin comprobante
            </span>
          )}
        </div>
      </div>

      {/* ── card-summary ── */}
      <aside className="flex flex-col justify-center gap-2.5">
        {/* total-block */}
        <div
          className="flex items-end self-stretch"
          style={{ color: "#a90c24" }}
        >
          <div className="flex flex-col">
            <small className="text-[9px] font-bold uppercase tracking-wider text-neutral-500">
              Total a pagar
            </small>
            <strong
              className="text-2xl font-black leading-none"
              style={{ color: "#a90c24" }}
            >
              {formatCurrency(total ?? 0)}
            </strong>
          </div>
        </div>

        {/* financials */}
        <div className="grid grid-cols-2 bg-white border border-neutral-200 rounded-lg">
          <div className="text-center p-2.5 border-r border-neutral-200">
            <span className="block uppercase text-[10px] font-bold tracking-wider text-neutral-500">
              Subtotal
            </span>
            <strong className="block text-base mt-1 text-neutral-900 font-bold">
              {formatCurrency(subTotal ?? 0)}
            </strong>
          </div>
          <div className="text-center p-2.5">
            <span className="block uppercase text-[10px] font-bold tracking-wider text-neutral-500">
              I.G.V.{" "}
              {igvPct != null && (
                <small className="text-[9px]" style={{ color: "#a90c24" }}>
                  {igvPct}%
                </small>
              )}
            </span>
            <strong className="block text-base mt-1 text-neutral-900 font-bold">
              {formatCurrency(igvMonto ?? 0)}
            </strong>
          </div>
        </div>
      </aside>

      {/* ── Bloque específico por motor (full-width) ── */}
      {calculoSlot && (
        <div
          style={{
            gridColumn: "1 / -1",
          }}
        >
          {calculoSlot}
        </div>
      )}

      {/* ── Delegados (custom React slot) ── */}
      {delegadosSlot && (
        <div
          style={{
            gridColumn: "1 / -1",
          }}
        >
          {delegadosSlot}
        </div>
      )}

      {/* ── card-footer ── */}
      <footer
        className="flex items-center justify-end gap-2 pt-2.5 mt-0.5"
        style={{
          gridColumn: "1 / -1",
          borderTop: "1px solid #e8e0df",
        }}
      >
        {direccion && (
          <span className="mr-auto flex items-center gap-1.5 text-[11px] text-neutral-500 min-w-0 truncate">
            <MapPin
              className="h-3.5 w-3.5 shrink-0"
              style={{ color: "#a90c24" }}
            />
            <span className="truncate">
              <b className="text-neutral-900">Dirección de obra:</b> {direccion}
            </span>
          </span>
        )}

        {menuItems && primaryAction ? (
          <CardActionsMenu items={menuItems} primaryAction={primaryAction} />
        ) : (
          <div className="flex items-center gap-1.5 shrink-0">
            {showDelegados && onDelegados && (
              <LiquidacionCardAction
                icon={<User className="h-3 w-3" />}
                label={<span className="hidden sm:inline">Delegados</span>}
                onAction={onDelegados}
              />
            )}
            {onPrint && (
              <LiquidacionCardAction
                icon={<FileDown className="h-3 w-3" />}
                label={<span className="hidden sm:inline">PDF</span>}
                onAction={onPrint}
              />
            )}
            {canEdit && onEdit && (
              <LiquidacionCardAction
                icon={<FilePenLine className="h-3 w-3" />}
                label={<span className="hidden sm:inline">Editar</span>}
                onAction={onEdit}
              />
            )}
            {onComprobante && (
              <LiquidacionCardAction
                icon={<Receipt className="h-3 w-3" />}
                label={
                  <span className="hidden sm:inline">
                    {comprobanteActivo
                      ? "Reemplazar comprobante"
                      : "Agregar comprobante"}
                  </span>
                }
                onAction={onComprobante}
              />
            )}
            {onVerDetalle && (
              <LiquidacionCardAction
                variant="primary"
                label="Ver detalle"
                onAction={onVerDetalle}
              />
            )}
          </div>
        )}
      </footer>
    </article>
  );
}
