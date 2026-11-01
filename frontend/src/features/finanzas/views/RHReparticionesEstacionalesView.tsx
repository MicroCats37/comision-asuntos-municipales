/**
 * Vista para lista de Reparticiones Estacionales.
 * Ruta: /liquidaciones/reparticiones-estacionales
 *
 * Muestra: periodo, especialidad, fondo común, delegados, capítulos, monto por participación.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import {
  FilePenLine,
  FileText,
  PieChart,
  Plus,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";
import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import {
  type RhCardAction,
  RhMensualCardShell,
} from "@/features/finanzas/components/cards/RhMensualCardShell";
import { NuevaRHReparticionEstacionalModal } from "@/features/finanzas/components/modals/NuevaRHReparticionEstacionalModal";
import { useEliminarRHReparticionEstacional } from "@/features/finanzas/hooks/useEliminarRHReparticionEstacional";
import { useRHReparticionesEstacionales } from "@/features/finanzas/hooks/useRHReparticionesEstacionales";
import type { RHReparticionEstacional } from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";
import { formatCurrency } from "@/features/liquidaciones/components/liquidacion-ui";

const KIND_ICON: LucideIcon = PieChart;

const MONTH_NAMES = [
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

interface ReparticionCardProps {
  item: RHReparticionEstacional;
  /** Abre el modal de RH Trimestral en modo edición con este item. */
  onEdit?: (item: RHReparticionEstacional) => void;
  /** Solicita la eliminación (soft-delete) de este item. */
  onDelete?: (id: string) => void;
}

export function ReparticionCard({
  item,
  onEdit,
  onDelete,
}: ReparticionCardProps) {
  const { identidad, general, distribucion } = item;
  const trimestre = `T${Math.ceil(general.mes_desde / 3)}`;
  const periodoLabel = `${general.periodo} · ${trimestre} (${MONTH_NAMES[general.mes_desde].slice(0, 3)}–${MONTH_NAMES[general.mes_hasta].slice(0, 3)})`;
  const actions: RhCardAction[] = [];

  if (onEdit) {
    actions.push({
      key: "edit",
      icon: <FilePenLine className="h-3 w-3" />,
      label: "Editar",
      ariaLabel: "Editar RH trimestral",
      onAction: () => onEdit(item),
    });
  }

  if (onDelete) {
    actions.push({
      key: "delete",
      icon: <Trash2 className="h-3 w-3" />,
      label: "Eliminar",
      ariaLabel: "Eliminar RH trimestral",
      onAction: () => onDelete(identidad.id),
      variant: "danger",
    });
  }

  return (
    <RhMensualCardShell
      kindIcon={PieChart}
      kindLabel="Trimestral"
      title="Recibo de Honorario Trimestral"
      fechaRegistro={identidad.created_at}
      periodo={{ periodo: general.periodo }}
      periodoLabel={periodoLabel}
      personaNombre={general.especialidad_revision.nombre}
      identityLabel="Especialidad"
      identityIcon={PieChart}
      totalLabel="Fondo común distribuido"
      total={distribucion.total_fondo_comun}
      summaryItems={[
        {
          label: "Por participación",
          value: formatCurrency(distribucion.monto_por_participacion),
        },
        { label: "Delegados", value: String(distribucion.numero_delegados) },
        { label: "Capítulos", value: String(distribucion.numero_capitulos) },
        ...(distribucion.residual !== 0
          ? [
              {
                label: "Residual",
                value: formatCurrency(distribucion.residual),
                tone: "muted" as const,
              },
            ]
          : []),
      ]}
      actions={actions}
    >
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <section className="p-3 rounded-lg border border-border/60 bg-muted/10 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Users className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Distribución por delegado
            </span>
            <span className="ml-auto text-xs font-semibold text-primary">
              {distribucion.detalles_delegados.length}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="pb-1.5 pr-3 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Delegado
                  </th>
                  <th className="pb-1.5 px-3 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    CIP
                  </th>
                  <th className="pb-1.5 pl-3 text-right text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Monto
                  </th>
                </tr>
              </thead>
              <tbody>
                {distribucion.detalles_delegados.map((detalle) => (
                  <tr
                    key={detalle.delegado.id}
                    className="border-b border-border/30 last:border-b-0 hover:bg-muted/20 transition-colors"
                  >
                    <td className="py-1.5 pr-3 font-medium">
                      {detalle.delegado.nombre_completo}
                    </td>
                    <td className="py-1.5 px-3 font-mono text-muted-foreground">
                      {detalle.delegado.cip}
                    </td>
                    <td className="py-1.5 pl-3 text-right font-semibold whitespace-nowrap">
                      {formatCurrency(detalle.monto)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="p-3 rounded-lg border border-border/60 bg-muted/10 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Distribución por capítulo
            </span>
            <span className="ml-auto text-xs font-semibold text-primary">
              {distribucion.detalles_capitulos.length}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="pb-1.5 pr-3 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Capítulo
                  </th>
                  <th className="pb-1.5 pl-3 text-right text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Monto
                  </th>
                </tr>
              </thead>
              <tbody>
                {distribucion.detalles_capitulos.map((detalle) => (
                  <tr
                    key={detalle.capitulo.id}
                    className="border-b border-border/30 last:border-b-0 hover:bg-muted/20 transition-colors"
                  >
                    <td className="py-1.5 pr-3 font-medium">
                      {detalle.capitulo.nombre}
                    </td>
                    <td className="py-1.5 pl-3 text-right font-semibold whitespace-nowrap">
                      {formatCurrency(detalle.monto)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </RhMensualCardShell>
  );
}

export function RHReparticionesEstacionalesView() {
  const { items, isLoading, isError, refetch } = useRHReparticionesEstacionales(
    {},
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [rhEnEdicion, setRhEnEdicion] =
    useState<RHReparticionEstacional | null>(null);
  const { confirm, Dialog } = useConfirmationDialog();
  const eliminarMutation = useEliminarRHReparticionEstacional();

  const handleOpenModal = useCallback(() => {
    setRhEnEdicion(null);
    setModalOpen(true);
  }, []);
  const handleCloseModal = useCallback((open: boolean) => {
    setModalOpen(open);
    if (!open) setRhEnEdicion(null);
  }, []);
  const handleModalSuccess = useCallback(() => {
    setModalOpen(false);
    setRhEnEdicion(null);
    refetch();
  }, [refetch]);

  /** Abre el wizard de RH Trimestral en modo edición sobre el item elegido. */
  const handleEdit = useCallback((item: RHReparticionEstacional) => {
    setRhEnEdicion(item);
    setModalOpen(true);
  }, []);

  /** Elimina (soft-delete) la repartición confirmada por el usuario. */
  const handleDelete = useCallback(
    (id: string) => {
      confirm({
        title: "Eliminar repartición trimestral",
        description:
          "¿Estás seguro de que deseas eliminar esta repartición trimestral? Esta acción no se puede deshacer.",
        confirmLabel: "Eliminar",
        variant: "danger",
      }).then((confirmed) => {
        if (confirmed) {
          eliminarMutation.eliminar(id);
        }
      });
    },
    [confirm, eliminarMutation],
  );

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
                <ReparticionCard
                  key={item.identidad.id}
                  item={item}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <NuevaRHReparticionEstacionalModal
        open={modalOpen}
        onOpenChange={handleCloseModal}
        onSuccess={handleModalSuccess}
        editContext={rhEnEdicion}
      />

      {Dialog}
    </div>
  );
}
