"use client";

import {
  Building2,
  Eye,
  FileText,
  MapPin,
  RefreshCw,
  Search,
  User,
  X,
} from "lucide-react";
/**
 * SeleccionarPreviaModal — Modal general para buscar/seleccionar una liquidación
 * previa usando el endpoint de últimas revisiones.
 *
 * Endpoint: GET /liquidaciones/generales/ultimas-revisiones
 * - `tipo_liquidacion` se envía como params repetidos (array)
 * - Soporta filtros: numero_documento, razon_social, nombre_propietario, direccion, expediente, numero
 * - Restringe a los tipos permitidos (ej. IO → EDIFICACION + HU)
 *
 * NO dispara la búsqueda al abrir — espera a que el usuario presione "Buscar".
 */
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
} from "../../components/detail";
import {
  type UltimaRevisionGeneralItem,
  useUltimaRevisionGeneral,
} from "../../hooks/useUltimaRevisionGeneral";
import { getLiquidacionTipoInfo } from "../../utils/liquidacionTipoInfo";

interface SeleccionarPreviaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Tipos permitidos como previa (códigos tipo_liquidacion) — ej. ["EDIFICACION", "HABILITACION_URBANA"] */
  tiposPermitidos?: string[];
  /** Título del modal */
  title?: string;
  description?: string;
  onSelect: (previa: UltimaRevisionGeneralItem) => void;
  /** Si se pasa, muestra un botón "Crear sin liquidación previa" en el footer
   * que invoca este callback en lugar de seleccionar una previa. */
  onCreateSinPrevia?: () => void;
  /** Texto del botón "Crear sin previa". Default: "Crear sin liquidación previa". */
  createSinPreviaLabel?: string;
}

export function SeleccionarPreviaModal({
  open,
  onOpenChange,
  tiposPermitidos,
  title = "Nueva Revisión",
  description = "Busca la liquidación previa para crear una nueva revisión",
  onSelect,
  onCreateSinPrevia,
  createSinPreviaLabel = "Crear sin liquidación previa",
}: SeleccionarPreviaModalProps) {
  const [documento, setDocumento] = useState("");
  const [numero, setNumero] = useState("");
  const [propietario, setPropietario] = useState("");
  const [direccion, setDireccion] = useState("");
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [detalleItem, setDetalleItem] =
    useState<UltimaRevisionGeneralItem | null>(null);

  const isDocumentoValid =
    !documento.trim() ||
    documento.trim().length === 8 ||
    documento.trim().length === 11;
  const numeroValue = numero.trim() ? Number(numero) : undefined;
  const isNumeroValid = numeroValue === undefined || numeroValue > 0;
  const canSearch =
    (documento.trim() ||
      numeroValue !== undefined ||
      propietario.trim() ||
      direccion.trim()) &&
    isDocumentoValid &&
    isNumeroValid;

  // IMPORTANTE: cuando tiposPermitidos es vacío, NO disparar query — evita el 422 del backend.
  const tiposParaBuscar =
    tiposPermitidos && tiposPermitidos.length > 0 ? tiposPermitidos : undefined;

  const { items, total, totalPages, pageSize, isLoading, isError, refetch } =
    useUltimaRevisionGeneral({
      page,
      pageSize: 10,
      tipoLiquidacion: tiposParaBuscar,
      numeroDocumento: documento || undefined,
      numero: numeroValue,
      nombrePropietario: propietario || undefined,
      direccion: direccion || undefined,
      enabled: searched && open && tiposParaBuscar !== undefined,
    });

  const handleSearch = useCallback(() => {
    if (!canSearch) return;
    setPage(1);
    setSearched(true);
    refetch();
  }, [canSearch, refetch]);

  const handleReset = useCallback(() => {
    setDocumento("");
    setNumero("");
    setPropietario("");
    setDireccion("");
    setSearched(false);
    setPage(1);
  }, []);

  return (
    <>
      <GenericModal
        open={open}
        onOpenChange={onOpenChange}
        preventClose={false}
      >
        <GenericModal.Content size="lg">
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
                <RefreshCw className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Liquidaciones
                </span>
                <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                  {title}
                </h2>
                <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              </div>
              <div className="w-9 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          <GenericModal.Body className="space-y-6">
            {/* Búsqueda */}
            <div className="p-4 rounded-xl border border-border/60 bg-muted/10 space-y-3">
              <div className="space-y-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label
                      htmlFor="buscar-documento"
                      className="text-sm font-semibold"
                    >
                      N° Documento (RUC/DNI)
                    </Label>
                    <Input
                      id="buscar-documento"
                      placeholder="Ej. 20456789012"
                      inputMode="numeric"
                      value={documento}
                      onChange={(e) => {
                        const val = e.target.value
                          .replace(/\D/g, "")
                          .slice(0, 11);
                        setDocumento(val);
                        setSearched(false);
                      }}
                      onKeyDown={(e) =>
                        e.key === "Enter" && canSearch && handleSearch()
                      }
                      className="w-full h-10 font-mono"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label
                      htmlFor="buscar-numero"
                      className="text-sm font-semibold"
                    >
                      N° Liquidación
                    </Label>
                    <Input
                      id="buscar-numero"
                      placeholder="Ej. 123"
                      inputMode="numeric"
                      value={numero}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, "");
                        setNumero(val);
                        setSearched(false);
                      }}
                      onKeyDown={(e) =>
                        e.key === "Enter" && canSearch && handleSearch()
                      }
                      className="w-full h-10 font-mono"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label
                      htmlFor="buscar-propietario"
                      className="text-sm font-semibold"
                    >
                      Propietario
                    </Label>
                    <Input
                      id="buscar-propietario"
                      placeholder="Ej. ASOC. DE COMERCIANTES"
                      value={propietario}
                      onChange={(e) => {
                        setPropietario(e.target.value);
                        setSearched(false);
                      }}
                      onKeyDown={(e) =>
                        e.key === "Enter" && canSearch && handleSearch()
                      }
                      className="w-full h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label
                      htmlFor="buscar-direccion"
                      className="text-sm font-semibold"
                    >
                      Dirección
                    </Label>
                    <Input
                      id="buscar-direccion"
                      placeholder="Ej. AV. GUARDIA PERUANA"
                      value={direccion}
                      onChange={(e) => {
                        setDireccion(e.target.value);
                        setSearched(false);
                      }}
                      onKeyDown={(e) =>
                        e.key === "Enter" && canSearch && handleSearch()
                      }
                      className="w-full h-10"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="default"
                    onClick={handleSearch}
                    disabled={!canSearch}
                    className="h-10 shrink-0 gap-1.5 px-5"
                  >
                    <Search className="h-4 w-4" />
                    Buscar
                  </Button>
                </div>
                {documento && !isDocumentoValid && (
                  <p className="text-xs text-destructive">
                    El documento debe tener 8 (DNI) u 11 (RUC) dígitos
                  </p>
                )}
                {numero && !isNumeroValid && (
                  <p className="text-xs text-destructive">
                    El número de liquidación debe ser mayor a 0
                  </p>
                )}
              </div>
            </div>

            {/* Resultados */}
            <div className="border-t border-border/40 pt-5">
              {!searched ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/40 mb-3">
                    <Search className="h-5 w-5 text-muted-foreground/70" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Ingresa un documento, número de liquidación, propietario o
                    dirección y presiona Buscar
                  </p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    DNI: 8 dígitos · RUC: 11 dígitos · Otros filtros opcionales
                  </p>
                </div>
              ) : isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="rounded-xl border bg-card p-4"
                      style={{ animationDelay: `${i * 150}ms` }}
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 shrink-0 rounded-lg bg-gradient-to-r from-muted via-muted/50 to-muted animate-pulse" />
                        <div className="flex-1 space-y-2">
                          <div className="h-4 w-2/3 rounded bg-gradient-to-r from-muted via-muted/40 to-muted animate-pulse" />
                          <div className="h-3 w-1/3 rounded bg-gradient-to-r from-muted/70 via-muted/30 to-muted/70 animate-pulse" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : isError ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <p className="text-destructive font-medium">
                    Error al cargar las liquidaciones
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => refetch()}
                  >
                    Reintentar
                  </Button>
                </div>
              ) : items.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Building2 className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-muted-foreground text-sm">
                    No se encontraron liquidaciones previas
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    {items.length} resultado
                    {items.length !== 1 ? "s" : ""}
                  </p>
                  <div className="flex flex-col gap-2">
                    {items.map((item) => {
                      const lg = item.liquidacion_general;
                      const tipoCodigo = lg.tipo_liquidacion?.codigo ?? "—";
                      const propietario =
                        lg.proyecto?.nombre_propietario ?? "—";
                      const tipoDoc = lg.proyecto?.entidad?.tipo_documento;
                      const numDoc = lg.proyecto?.entidad?.numero_documento;
                      const documentoStr =
                        tipoDoc && numDoc
                          ? `${tipoDoc} ${numDoc}`
                          : (numDoc ?? tipoDoc ?? "—");
                      const direccion = lg.proyecto?.direccion ?? "—";
                      return (
                        <div
                          key={lg.id}
                          className="rounded-xl border bg-card p-4 hover:border-primary/40 hover:bg-primary/[0.02] hover:shadow-sm transition-all"
                        >
                          {/* Header — clickable para seleccionar */}
                          <button
                            type="button"
                            onClick={() => onSelect(item)}
                            className="w-full text-left flex items-center justify-between gap-3 cursor-pointer"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                                <Building2 className="h-4 w-4 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <p className="text-sm font-semibold truncate">
                                  {lg.denominacion_de_proyecto ??
                                    "Sin denominación"}
                                </p>
                                <p className="text-xs text-muted-foreground truncate">
                                  {lg.expediente || "Sin expediente"}
                                </p>
                              </div>
                            </div>
                            <div className="shrink-0 flex flex-col items-end gap-1">
                              <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-bold text-primary">
                                {tipoCodigo}
                              </span>
                              <span className="inline-flex items-center rounded-full bg-muted border border-border px-2 py-0.5 text-[10px] font-mono font-bold text-muted-foreground">
                                Rev. {lg.numero_revision ?? "—"}
                              </span>
                            </div>
                          </button>

                          {/* Detalles (proietario, documento, dirección) */}
                          <div className="mt-3 pt-3 border-t border-border/40 space-y-1.5">
                            <DetailRow
                              icon={User}
                              label="Propietario"
                              value={propietario}
                            />
                            <DetailRow
                              icon={FileText}
                              label="Documento"
                              value={documentoStr}
                            />
                            <DetailRow
                              icon={MapPin}
                              label="Dirección"
                              value={direccion}
                            />
                          </div>

                          {/* Ver detalle — abre modal de detalle sin seleccionar */}
                          <div className="mt-3 flex justify-end">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDetalleItem(item);
                              }}
                              className="h-7 gap-1 text-xs text-muted-foreground hover:text-primary"
                            >
                              <Eye className="h-3.5 w-3.5" />
                              Ver detalle
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {total > pageSize && (
                    <div className="pt-2">
                      <Pagination
                        currentPage={page}
                        totalPages={totalPages}
                        totalItems={total}
                        pageSize={pageSize}
                        onPageChange={setPage}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </GenericModal.Body>

          <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
            <div className="flex items-center justify-between gap-2">
              {onCreateSinPrevia ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    onCreateSinPrevia();
                    onOpenChange(false);
                  }}
                  className="h-10 rounded-xl font-semibold"
                >
                  {createSinPreviaLabel}
                </Button>
              ) : (
                <div />
              )}
              <div className="flex items-center gap-2">
                {searched && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleReset}
                    className="h-10 gap-1 text-xs text-muted-foreground"
                  >
                    <X className="h-3 w-3" />
                    Limpiar
                  </Button>
                )}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  className="h-10 rounded-xl font-semibold"
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      {/* Modal de detalle — se abre desde el botón "Ver detalle" de cada card.
          Auto-determina el tipo a partir del codigo (el caller no lo pasa). */}
      {detalleItem !== null && (() => {
        const tipoInfo = getLiquidacionTipoInfo(
          detalleItem.liquidacion_general.tipo_liquidacion?.codigo,
        );
        return (
          <LiquidacionDetalleModal
            open
            onOpenChange={(open) => {
              if (!open) setDetalleItem(null);
            }}
            kindBadge={tipoInfo.label}
            publicId={detalleItem.liquidacion_general.expediente ?? "—"}
            estado={detalleItem.liquidacion_general.estado ?? null}
            kindIcon={tipoInfo.icon}
          >
            {composeDetalleSections({
              lg: detalleItem.liquidacion_general,
              lt: detalleItem.liquidacion_tipo as never,
              showDelegados: false,
            })}
          </LiquidacionDetalleModal>
        );
      })()}
    </>
  );
}

interface DetailRowProps {
  icon: typeof User;
  label: string;
  value: string;
}

function DetailRow({ icon: Icon, label, value }: DetailRowProps) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon className="h-3 w-3 text-muted-foreground/70 shrink-0" />
      <span className="text-muted-foreground shrink-0">{label}:</span>
      <span className="font-medium text-foreground truncate" title={value}>
        {value}
      </span>
    </div>
  );
}
