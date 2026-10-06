import {
  type MutationFunction,
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

interface UseGenericUpdateMutationOptions<
  TItem extends { id: string | number },
> {
  queryKey: QueryKey;
  mutationFn: MutationFunction<
    TItem,
    { id: TItem["id"]; data: Partial<TItem> }
  >;
}

export function useGenericUpdateMutation<
  TItem extends { id: string | number },
>({ queryKey, mutationFn }: UseGenericUpdateMutationOptions<TItem>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: (updatedItem) => {
      // Update item in list cache
      queryClient.setQueryData<TItem[]>(
        queryKey,
        (old) =>
          old?.map((item) =>
            item.id === updatedItem.id ? updatedItem : item,
          ) ?? [],
      );
      // Also update detail cache if it exists
      queryClient.setQueryData([...queryKey, updatedItem.id], updatedItem);
    },
  });
}
