import { type QueryKey, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

interface UseGenericCacheSyncOptions<TItem> {
  listQueryKey: QueryKey;
  detailKeyFn: (item: TItem) => QueryKey;
}

export function useGenericCacheSync<TItem extends { id: string | number }>({
  listQueryKey,
  detailKeyFn,
}: UseGenericCacheSyncOptions<TItem>) {
  const queryClient = useQueryClient();

  /** Pre-warm detail caches from a list of items */
  const seedDetailCaches = useCallback(
    (items: TItem[]) => {
      items.forEach((item) => {
        queryClient.setQueryData(detailKeyFn(item), item);
      });
    },
    [queryClient, detailKeyFn],
  );

  /** Update an item in both list and detail caches */
  const syncItem = useCallback(
    (updatedItem: TItem) => {
      // Update in list cache
      queryClient.setQueryData<TItem[]>(
        listQueryKey,
        (old) =>
          old?.map((item) =>
            item.id === updatedItem.id ? updatedItem : item,
          ) ?? [],
      );
      // Update detail cache
      queryClient.setQueryData(detailKeyFn(updatedItem), updatedItem);
    },
    [queryClient, listQueryKey, detailKeyFn],
  );

  /** Remove an item from both list and detail caches */
  const removeItem = useCallback(
    (itemId: TItem["id"]) => {
      queryClient.setQueryData<TItem[]>(
        listQueryKey,
        (old) => old?.filter((item) => item.id !== itemId) ?? [],
      );
      // We need the item to get its detail key, so we use a generic approach
      queryClient.removeQueries({
        queryKey: [
          ...(Array.isArray(listQueryKey) ? listQueryKey : [listQueryKey]),
          itemId,
        ],
      });
    },
    [queryClient, listQueryKey],
  );

  return { seedDetailCaches, syncItem, removeItem };
}
