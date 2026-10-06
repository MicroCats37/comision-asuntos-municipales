import { useCallback, useState } from "react";

interface UsePaginationProps {
  initialPage?: number;
  initialPageSize?: number;
}

export function usePagination({
  initialPage = 1,
  initialPageSize = 10,
}: UsePaginationProps = {}) {
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const onPageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  const onPageSizeChange = useCallback((newPageSize: number) => {
    setPageSize(newPageSize);
    setPage(1);
  }, []);

  return {
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
    paginationParams: {
      page,
      page_size: pageSize,
    },
  };
}
