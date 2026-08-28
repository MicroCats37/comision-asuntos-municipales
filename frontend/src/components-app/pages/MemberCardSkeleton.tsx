"use client";

import { Skeleton } from "@/components/ui/skeleton";

interface MemberCardSkeletonProps {
  count?: number;
  className?: string;
}

/**
 * Skeleton that replicates the shape of a ContactCard.
 * Uses rounded-[28px] to match the legacy card border-radius.
 */
export function MemberCardSkeleton({
  count = 1,
  className,
}: MemberCardSkeletonProps) {
  return (
    <div className={className}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-start gap-4 p-5 rounded-[28px] border border-border/50 bg-card shadow-sm"
        >
          {/* Avatar skeleton */}
          <Skeleton className="w-14 h-14 rounded-2xl shrink-0" />

          {/* Content skeleton */}
          <div className="flex flex-col gap-2 flex-1 min-w-0">
            {/* Name skeleton */}
            <Skeleton className="h-5 w-48 rounded" />
            {/* Badges row skeleton */}
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            {/* DNI skeleton */}
            <Skeleton className="h-4 w-32 rounded" />
          </div>

          {/* Action skeleton */}
          <Skeleton className="w-20 h-8 rounded-xl shrink-0" />
        </div>
      ))}
    </div>
  );
}
