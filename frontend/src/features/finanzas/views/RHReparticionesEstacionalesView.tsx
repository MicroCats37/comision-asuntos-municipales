/**
 * Vista para lista de Reparticiones Estacionales.
 * Ruta: /liquidaciones/reparticiones-estacionales
 *
 * Muestra: periodo, especialidad, fondo común, delegados, capítulos, monto por participación.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  Calendar,
  FileText,
  PieChart,
  Plus,
  RefreshCw,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { NuevaRHReparticionEstacionalModal } from "@/features/finanzas/components/modals/NuevaRHReparticionEstacionalModal";
import { useRHReparticionesEstacionales } from "@/features/finanzas/hooks/useRHReparticionesEstacionales";
import type { RHReparticionEstacionalListItem } from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

const KIND_ICON: LucideIcon = PieChart;

function ReparticionCard({ item }: { item: RHReparticionEstacionalListItem }) {
  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Trimestral
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" />
            <span>{formatDate(item.created_at)}</span>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Periodo + Especialidad */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Calendar className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Periodo
              </p>
              <p className="text-sm font-bold truncate">{item.periodo}</p>
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
        </div>

        {/* Montos y participantes */}
        <div className="rounded-lg border border-border/60 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-muted/30 border-b border-border">
            <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Detalle de Distribución
            </span>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground">Fondo Común</p>
                <p className="text-sm font-semibold">
                  {formatCurrency(item.total_fondo_comun)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">
                  x Participación
                </p>
                <p className="text-sm font-semibold">
                  {formatCurrency(item.monto_por_participacion)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">
                  <Users className="h-3 w-3 inline mr-1" />
                  Delegados
                </p>
                <p className="text-sm font-semibold">{item.numero_delegados}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">
                  <FileText className="h-3 w-3 inline mr-1" />
                  Capítulos
                </p>
                <p className="text-sm font-semibold">{item.numero_capitulos}</p>
              </div>
            </div>

            {item.residual != null && item.residual !== 0 && (
              <div className="mt-3 pt-3 border-t border-border/60">
                <p className="text-[10px] text-muted-foreground">Residual</p>
                <p className="text-sm font-semibold text-muted-foreground">
                  {formatCurrency(item.residual)}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" className="gap-1.5 h-8" asChild>
            <Link href={`/liquidaciones/reparticiones-estacionales/${item.id}`}>
              Ver detalle
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

export function RHReparticionesEstacionalesView() {
  const { items, isLoading, isError, refetch } = useRHReparticionesEstacionales(
    {},
  );
  const [modalOpen, setModalOpen] = useState(false);

  const handleOpenModal = useCallback(() => setModalOpen(true), []);
  const handleCloseModal = useCallback(
    (open: boolean) => setModalOpen(open),
    [],
  );
  const handleModalSuccess = useCallback(() => setModalOpen(false), []);

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Trimestral"
          description="Distribución trimestral del fondo común entre delegados y capítulos"
          icon={KIND_ICON}
          actionNodes={
            <Button
              className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
              onClick={handleOpenModal}
            >
              <Plus className="h-4 w-4" />
              Nueva repartición
            </Button>
          }
        />

        {/* Cards View */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
                />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-8 text-destructive">
              <p className="font-medium mb-4">
                Error al cargar las reparticiones
              </p>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reintentar
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-2">
                No hay Trimestral registrada
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                Las reparticiones se crean desde el asistente de distribución
              </p>
              <Button
                variant="outline"
                className="gap-2 h-10 rounded-xl font-semibold"
                onClick={handleOpenModal}
              >
                <Plus className="h-4 w-4" />
                Nueva repartición
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {items.map((item) => (
                <ReparticionCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

      <NuevaRHReparticionEstacionalModal
        open={modalOpen}
        onOpenChange={handleCloseModal}
        onSuccess={handleModalSuccess}
      />
    </div>
  );
}
