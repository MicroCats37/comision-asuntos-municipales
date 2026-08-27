"use client";

import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Build the page list with ellipsis markers for responsive pagination.
 * - totalPages <= 7: all pages shown, no ellipsis.
 * - currentPage <= 4: first 5 pages + ellipsis + last 3.
 * - currentPage >= N-3: first 3 pages + ellipsis + last 5.
 * - middle: first 3 pages + ellipsis + (cp-1,cp,cp+1) + ellipsis + last 3.
 */
function getPageItems(
  currentPage: number,
  totalPages: number,
): (number | "...")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const lastThree = [totalPages - 2, totalPages - 1, totalPages];

  if (currentPage <= 4) {
    const firstFive = [1, 2, 3, 4, 5];
    // Avoid duplicate: if 5 already appears as part of last three (when N <= 7 handled above, so here N > 7, 5 is safe)
    return [...firstFive, "...", ...lastThree];
  }

  if (currentPage >= totalPages - 3) {
    const firstThree = [1, 2, 3];
    const lastFive = [
      totalPages - 4,
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
    return [...firstThree, "...", ...lastFive];
  }

  // Middle case: current page is between 4 and N-3
  const firstThree = [1, 2, 3];
  const window = [currentPage - 1, currentPage, currentPage + 1];
  return [...firstThree, "...", ...window, "...", ...lastThree];
}

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  totalItems?: number;
  pageSize?: number;
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  onPageSizeChange,
  totalItems,
  pageSize,
  className = "",
}: PaginationProps) {
  if (totalPages === 0 && (!totalItems || totalItems === 0)) return null;

  // Calculate range of items being shown
  const startItem =
    totalItems === 0 ? 0 : (currentPage - 1) * (pageSize || 0) + 1;
  const endItem = Math.min(currentPage * (pageSize || 0), totalItems || 0);

  return (
    <div
      className={`flex flex-col sm:flex-row items-center justify-between gap-4 py-4 ${className}`}
    >
      <div className="flex items-center gap-4 order-2 sm:order-1">
        <div className="text-sm text-muted-foreground">
          {totalItems !== undefined && pageSize !== undefined ? (
            <>
              Mostrando{" "}
              <span className="font-medium text-primary">{startItem}</span> a{" "}
              <span className="font-medium text-primary">{endItem}</span> de{" "}
              <span className="font-medium text-primary">{totalItems}</span>{" "}
              resultados
            </>
          ) : (
            `Página ${currentPage} de ${totalPages}`
          )}
        </div>

        {onPageSizeChange && pageSize && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground hidden lg:inline">
              Ver:
            </span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => onPageSizeChange(Number(value))}
            >
              <SelectTrigger className="h-8 w-[70px] rounded-lg text-xs font-medium">
                <SelectValue placeholder={pageSize.toString()} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5</SelectItem>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2 order-1 sm:order-2">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-lg"
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-lg"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        {(() => {
          let ellipsisCount = 0;
          return getPageItems(currentPage, totalPages).map((item) => {
            if (item === "...") {
              const ellipsisKey = `ellipsis-${ellipsisCount++}`;
              return (
                <span
                  key={ellipsisKey}
                  className="flex items-center justify-center min-w-[32px] h-8 text-muted-foreground text-xs"
                  aria-hidden="true"
                >
                  ...
                </span>
              );
            }
            return (
              <Button
                key={item}
                variant="outline"
                size="icon"
                className={`h-8 min-w-[32px] rounded-lg text-xs font-medium ${
                  item === currentPage
                    ? "bg-primary/10 text-primary font-bold"
                    : ""
                }`}
                onClick={() => onPageChange(item)}
                disabled={item === currentPage}
              >
                {item}
              </Button>
            );
          });
        })()}

        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-lg"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-lg"
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
