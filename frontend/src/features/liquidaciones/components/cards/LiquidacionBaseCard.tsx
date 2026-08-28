"use client";

import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import {
  LiquidacionCardHeader,
  type LiquidacionCardHeaderData,
} from "../LiquidacionCardHeader";

interface LiquidacionBaseCardProps {
  data: LiquidacionCardHeaderData;
  rightSlotChildren?: React.ReactNode;
  children: React.ReactNode;
  displayPublicId?: string;
}

/**
 * Base card component for liquidaciones lists.
 * Provides the collapsible accordion structure with a consistent header.
 * Domain-specific content is rendered via children.
 */
export function LiquidacionBaseCard({
  data,
  rightSlotChildren,
  children,
  displayPublicId,
}: LiquidacionBaseCardProps) {
  return (
    <Collapsible className="group bg-card rounded-2xl border shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      <LiquidacionCardHeader
        data={data}
        displayPublicId={displayPublicId}
        rightSlotChildren={rightSlotChildren}
      />
      <CollapsibleContent className="p-5 space-y-4 border-t border-border/40 bg-muted/10">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
