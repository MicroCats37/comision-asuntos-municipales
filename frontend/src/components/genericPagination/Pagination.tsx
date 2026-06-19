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

        <div className="flex items-center justify-center min-w-[32px] h-8 px-3 rounded-lg bg-primary/10 text-primary text-xs font-bold">
          {currentPage}
        </div>

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
