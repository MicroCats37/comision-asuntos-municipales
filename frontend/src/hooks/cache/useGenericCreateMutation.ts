import {
  type MutationFunction,
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

interface UseGenericCreateMutationOptions<TItem, TVars = unknown> {
  queryKey: QueryKey;
  mutationFn: MutationFunction<TItem, TVars>;
  /** Where to insert: 'start' prepends (newest first), 'end' appends (oldest first). Default: 'start' */
  insertPosition?: "start" | "end";
}

export function useGenericCreateMutation<
  TItem extends { id: string | number },
  TVars = unknown,
>({
  queryKey,
  mutationFn,
  insertPosition = "start",
}: UseGenericCreateMutationOptions<TItem, TVars>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: (newItem) => {
      // Add new item to list cache
      queryClient.setQueryData<TItem[]>(queryKey, (old) => {
        const list = old ?? [];
        return insertPosition === "start"
          ? [newItem, ...list]
          : [...list, newItem];
      });
      // Seed detail cache
      queryClient.setQueryData([...queryKey, newItem.id], newItem);
    },
  });
}
