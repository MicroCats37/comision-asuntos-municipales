"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  actionNodes?: React.ReactNode;
}

/**
 * Reusable page header component.
 * Provides consistent page title, description, icon, and action buttons layout.
 */
export function PageHeader({
  title,
  description,
  icon: Icon,
  actionNodes,
}: PageHeaderProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        )}
        <div>
          <h1 className="text-3xl font-black tracking-tight">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      {actionNodes && (
        <div className={cn("flex flex-wrap items-center gap-3")}>
          {actionNodes}
        </div>
      )}
    </div>
  );
}
