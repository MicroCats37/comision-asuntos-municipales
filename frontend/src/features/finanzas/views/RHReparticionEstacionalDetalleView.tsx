/**
 * Vista de detalle para una Repartición Estacional individual.
 * Ruta: /liquidaciones/reparticiones-estacionales/[id]
 *
 * Muestra: periodo, mes_desde/mes_hasta, especialidad, total_fondo_comun,
 * numero_delegados, numero_capitulos, monto_por_participacion, residual,
 * tabla de detalle de delegados, tabla de detalle de capítulos.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import {
  ArrowLeft,
  Banknote,
  Calendar,
  FileText,
  PieChart,
  RefreshCw,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useRHReparticionEstacionalDetalle } from "@/features/finanzas/hooks/useRHReparticionesEstacionales";
import type {
  RHReparticionEstacionalCapitulo,
  RHReparticionEstacionalDelegado,
  RHReparticionEstacionalDetalle,
} from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

const KIND_ICON: LucideIcon = PieChart;

function DetailCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border/60 bg-card shadow-sm overflow-hidden">
      <header className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/30">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-[11px] font-bold text-foreground uppercase tracking-wider">
          {title}
        </h3>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

function DelegatesTable({
  items,
}: {
  items: RHReparticionEstacionalDelegado[];
}) {
  if (!items || items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No hay delegados en esta repartición
      </p>
    );
  }
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Delegado
            </th>
            <th className="px-3 py-2 text-right text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Monto
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.delegado_id} className="border-t">
              <td className="px-3 py-2 font-medium">
                {row.delegado?.nombre_completo ?? row.delegado_id}
              </td>
              <td className="px-3 py-2 text-right font-medium">
                {formatCurrency(row.monto)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChaptersTable({
  items,
}: {
  items: RHReparticionEstacionalCapitulo[];
}) {
  if (!items || items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No hay capítulos en esta repartición
      </p>
    );
  }
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Capítulo
            </th>
            <th className="px-3 py-2 text-right text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Monto
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.capitulo_id} className="border-t">
              <td className="px-3 py-2 font-medium">
                {row.capitulo?.nombre ?? row.capitulo_id}
              </td>
              <td className="px-3 py-2 text-right font-medium">
                {formatCurrency(row.monto)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface RHReparticionEstacionalDetalleContentProps {
  item: RHReparticionEstacionalDetalle;
  onBack: () => void;
}

function RHReparticionEstacionalDetalleContent({
  item,
  onBack,
}: RHReparticionEstacionalDetalleContentProps) {
  const meses = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Setiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
  ];
  const mesDesde = item.mes_desde
    ? (meses[item.mes_desde] ?? item.mes_desde)
    : "—";
  const mesHasta = item.mes_hasta
    ? (meses[item.mes_hasta] ?? item.mes_hasta)
    : "—";

  return (
    <div className="space-y-6">
      {/* Header with back */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8"
          onClick={onBack}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Volver
        </Button>
      </div>

      {/* Summary Card */}
      <DetailCard title="Resumen de Repartición">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Calendar className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Periodo
              </p>
              <p className="text-sm font-bold">{item.periodo}</p>
              <p className="text-xs text-muted-foreground">
                {mesDesde} — {mesHasta}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <PieChart className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Especialidad
              </p>
              <p
                className="text-sm font-semibold truncate"
                title={item.especialidad_revision_nombre}
              >
                {item.especialidad_revision_nombre || "—"}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Banknote className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Fondo Común
              </p>
              <p className="text-sm font-bold">
                {formatCurrency(item.total_fondo_comun)}
              </p>
            </div>
          </div>
        </div>

        {/* Distribution details */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="flex flex-col gap-1 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-muted-foreground" />
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Delegados
              </p>
            </div>
            <p className="text-lg font-bold">{item.numero_delegados}</p>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Capítulos
              </p>
            </div>
            <p className="text-lg font-bold">{item.numero_capitulos}</p>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="flex items-center gap-1.5">
              <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                x Participación
              </p>
            </div>
            <p className="text-lg font-bold">
              {formatCurrency(item.monto_por_participacion)}
            </p>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="flex items-center gap-1.5">
              <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Residual
              </p>
            </div>
            <p className="text-lg font-bold">{formatCurrency(item.residual)}</p>
          </div>
        </div>

        {/* Metadata */}
        <div className="mt-4 pt-4 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
          <span>Creado: {formatDate(item.created_at)}</span>
          {item.is_deleted && (
            <span className="text-destructive font-semibold">(Eliminado)</span>
          )}
        </div>
      </DetailCard>

      {/* Delegates Detail */}
      <DetailCard title="Detalle de Delegados">
        <DelegatesTable items={item.detalles_delegados} />
      </DetailCard>

      {/* Chapters Detail */}
      <DetailCard title="Detalle de Capítulos">
        <ChaptersTable items={item.detalles_capitulos} />
      </DetailCard>
    </div>
  );
}

export function RHReparticionEstacionalDetalleView({
  reparticionId,
}: {
  reparticionId: string;
}) {
  const router = useRouter();

  const {
    detalle: item,
    isLoading,
    isError,
    refetch,
  } = useRHReparticionEstacionalDetalle({
    reparticionId,
  });

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Repartición Estacional"
          description="Detalle de la distribución estacional del fondo común"
          icon={KIND_ICON}
        />

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
              />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center p-8 text-destructive border border-destructive/30 rounded-xl">
            <p className="font-medium mb-4">
              Error al cargar el detalle de la repartición
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        ) : item ? (
          <RHReparticionEstacionalDetalleContent
            item={item}
            onBack={handleBack}
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-muted-foreground border border-dashed border-border rounded-xl">
            <p>No se encontró la repartición estacional</p>
          </div>
        )}
      </div>
    </div>
  );
}
