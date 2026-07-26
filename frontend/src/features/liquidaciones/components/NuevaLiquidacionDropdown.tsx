"use client";

import {
  Building2,
  ChevronDown,
  FileText,
  Plus,
  RefreshCw,
  Home,
  Layers,
  Car,
  Mountain,
  ClipboardCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LiquidacionEdificacionFormModal } from "@/features/liquidaciones/components/deprecadedForm";
import { NuevaRevisionEdificacionesFormModal } from "@/features/liquidaciones/components/NuevaRevisionEdificacionesFormModal";
import {
  LiquidacionHabilitacionUrbanaStepperModal,
  LiquidacionMecanicaSuelosStepperModal,
  LiquidacionImpactoVialStepperModal,
  LiquidacionTaludesStepperModal,
  LiquidacionInspeccionObraStepperModal,
  LiquidacionInspeccionObraSingleFormModal,
} from "@/features/liquidaciones/components";

// ── Tipos de revisión ──────────────────────────────────────────────────────────

type RevisionKind = "primera-revision" | "nueva-revision";

interface OpcionLiquidacion {
  key: string;
  label: string;
  description: string;
  icon: LucideIcon;
  kinds: RevisionKind[];
}

// ── Configuración de opciones del dropdown ────────────────────────────────────
// Agregar nuevas entradas aquí para nuevos tipos de liquidación.

const OPCIONES: OpcionLiquidacion[] = [
  {
    key: "edificacion",
    label: "Edificación",
    description: "Proyectos de edificación",
    icon: Building2,
    kinds: ["primera-revision", "nueva-revision"],
  },
  {
    key: "habilitacion-urbana",
    label: "Habilitación Urbana",
    description: "Liquidaciones de habilitación urbana",
    icon: Home,
    kinds: ["primera-revision"],
  },
  {
    key: "mecanica-suelos",
    label: "Mecánica de Suelos",
    description: "Liquidaciones de mecánica de suelos",
    icon: Layers,
    kinds: ["primera-revision"],
  },
  {
    key: "impacto-vial",
    label: "Impacto Vial",
    description: "Liquidaciones de impacto vial",
    icon: Car,
    kinds: ["primera-revision"],
  },
  {
    key: "taludes",
    label: "Taludes",
    description: "Liquidaciones de taludes",
    icon: Mountain,
    kinds: ["primera-revision"],
  },
  {
    key: "inspeccion-obra",
    label: "Inspección de Obra",
    description: "Liquidaciones de inspección de obra",
    icon: ClipboardCheck,
    kinds: ["primera-revision"],
  },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface NuevaLiquidacionDropdownProps {
  onSuccess?: () => void;
}

// ── Componente ────────────────────────────────────────────────────────────────

export function NuevaLiquidacionDropdown({
  onSuccess,
}: NuevaLiquidacionDropdownProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedOption, setSelectedOption] = useState<OpcionLiquidacion | null>(null);

  // Modal states — Edificación
  const [stepperOpen, setStepperOpen] = useState(false);
  const [nuevaRevisionOpen, setNuevaRevisionOpen] = useState(false);

  // Modal states — No Edificación (M2 family)
  const [huModalOpen, setHuModalOpen] = useState(false);
  const [msModalOpen, setMsModalOpen] = useState(false);
  const [ivModalOpen, setIvModalOpen] = useState(false);
  const [taludesModalOpen, setTaludesModalOpen] = useState(false);

  // Modal states — No Edificación (IO)
  const [ioModalOpen, setIoModalOpen] = useState(false);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleSelectOption = useCallback((opcion: OpcionLiquidacion) => {
    if (opcion.kinds.length === 1) {
      // Solo un tipo de revisión → abrir modal directamente según el tipo
      switch (opcion.key) {
        case "habilitacion-urbana":
          setHuModalOpen(true);
          break;
        case "mecanica-suelos":
          setMsModalOpen(true);
          break;
        case "impacto-vial":
          setIvModalOpen(true);
          break;
        case "taludes":
          setTaludesModalOpen(true);
          break;
        case "inspeccion-obra":
          setIoModalOpen(true);
          break;
        default:
          openModal(opcion.kinds[0]);
      }
    } else {
      // Varios tipos → mostrar diálogo intermedio
      setSelectedOption(opcion);
      setDialogOpen(true);
    }
  }, []);

  const openModal = useCallback((kind: RevisionKind) => {
    if (kind === "primera-revision") setStepperOpen(true);
    if (kind === "nueva-revision") setNuevaRevisionOpen(true);
    setDialogOpen(false);
  }, []);

  const handleSuccess = useCallback(() => {
    onSuccess?.();
  }, [onSuccess]);

  return (
    <>
      {/* ── Dropdown ──────────────────────────────────────────────────────── */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20">
            <Plus className="h-4 w-4" />
            Nueva Liquidación
            <ChevronDown className="h-3.5 w-3.5 opacity-70" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          {OPCIONES.map((opcion) => (
            <DropdownMenuItem
              key={opcion.key}
              onClick={() => handleSelectOption(opcion)}
            >
              <opcion.icon className="h-4 w-4 mr-2" />
              <div className="flex flex-col">
                <span className="font-semibold">{opcion.label}</span>
                <span className="text-xs text-muted-foreground">
                  {opcion.description}
                </span>
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* ── Diálogo intermedio: ¿Primera o Nueva Revisión? ────────────────── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedOption?.icon && <selectedOption.icon className="h-5 w-5" />}
              {selectedOption?.label}
            </DialogTitle>
            <DialogDescription>
              Selecciona el tipo de revisión que deseas crear
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            {selectedOption?.kinds.includes("primera-revision") && (
              <Button
                variant="default"
                onClick={() => openModal("primera-revision")}
                className="flex-1 gap-2 h-11 rounded-xl font-semibold"
              >
                <FileText className="h-4 w-4" />
                Primera Revisión
              </Button>
            )}
            {selectedOption?.kinds.includes("nueva-revision") && (
              <Button
                variant="outline"
                onClick={() => openModal("nueva-revision")}
                className="flex-1 gap-2 h-11 rounded-xl font-semibold"
              >
                <RefreshCw className="h-4 w-4" />
                Nueva Revisión
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Modales finales ────────────────────────────────────────────────── */}
      <LiquidacionEdificacionFormModal
        open={stepperOpen}
        onOpenChange={setStepperOpen}
        onSuccess={handleSuccess}
      />

      <NuevaRevisionEdificacionesFormModal
        open={nuevaRevisionOpen}
        onOpenChange={setNuevaRevisionOpen}
        onSuccess={handleSuccess}
        liquidacionPreviaId={null}
      />

      {/* ── No Edificación: Habilitación Urbana ─────────────────────────────── */}
      <LiquidacionHabilitacionUrbanaStepperModal
        open={huModalOpen}
        onOpenChange={setHuModalOpen}
        onSuccess={handleSuccess}
      />

      {/* ── No Edificación: Mecánica de Suelos ──────────────────────────────── */}
      <LiquidacionMecanicaSuelosStepperModal
        open={msModalOpen}
        onOpenChange={setMsModalOpen}
        onSuccess={handleSuccess}
      />

      {/* ── No Edificación: Impacto Vial ──────────────────────────────────── */}
      <LiquidacionImpactoVialStepperModal
        open={ivModalOpen}
        onOpenChange={setIvModalOpen}
        onSuccess={handleSuccess}
      />

      {/* ── No Edificación: Taludes ────────────────────────────────────────── */}
      <LiquidacionTaludesStepperModal
        open={taludesModalOpen}
        onOpenChange={setTaludesModalOpen}
        onSuccess={handleSuccess}
      />

      {/* ── No Edificación: Inspección de Obra ────────────────────────────── */}
      <LiquidacionInspeccionObraSingleFormModal
        open={ioModalOpen}
        onOpenChange={setIoModalOpen}
        onSuccess={handleSuccess}
      />
    </>
  );
}
