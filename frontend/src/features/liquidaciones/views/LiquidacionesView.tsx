/**
 * Main view for Liquidaciones — redirects or shows domain selection.
 * Ruta: /liquidaciones
 */
"use client";

import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Building2,
  Car,
  ClipboardCheck,
  Map,
  Mountain,
  ReceiptJapaneseYen,
} from "lucide-react";
import Link from "next/link";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components-app/pages/PageHeader";

const KIND_ICON: LucideIcon = ReceiptJapaneseYen;

interface DomainCard {
  title: string;
  description: string;
  icon: LucideIcon;
  href: string;
}

const DOMAIN_CARDS: DomainCard[] = [
  {
    title: "Edificaciones",
    description: "Liquidaciones de proyectos de edificaciones",
    icon: Building2,
    href: "/liquidaciones/edificaciones",
  },
  {
    title: "Habilitación Urbana",
    description: "Liquidaciones de habilitación urbana",
    icon: Map,
    href: "/liquidaciones/habilitacion-urbana",
  },
  {
    title: "Mecánica de Suelos",
    description: "Liquidaciones de mecánica de suelos",
    icon: AlertTriangle,
    href: "/liquidaciones/mecanica-suelos",
  },
  {
    title: "Impacto Vial",
    description: "Liquidaciones de impacto vial",
    icon: Car,
    href: "/liquidaciones/impacto-vial",
  },
  {
    title: "Taludes",
    description: "Liquidaciones de taludes",
    icon: Mountain,
    href: "/liquidaciones/taludes",
  },
  {
    title: "Inspección de Obra",
    description: "Liquidaciones de inspección de obra",
    icon: ClipboardCheck,
    href: "/liquidaciones/inspeccion-obra",
  },
];

export function LiquidacionesView() {
  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Liquidaciones"
          description="Gestión de liquidaciones por tipo de proyecto"
          icon={KIND_ICON}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {DOMAIN_CARDS.map((card) => (
            <Link key={card.href} href={card.href}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <card.icon className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{card.title}</CardTitle>
                      <CardDescription>{card.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
