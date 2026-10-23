import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  type QueryKey,
  type UseMutationOptions,
  type UseMutationResult,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";
import { createContext, useContext, useState, type ReactNode } from "react";

import {
  createApiClient,
  type ApiClient,
  type ApiClientConfig,
} from "./client";

const ApiContext = createContext<ApiClient | null>(null);

export interface ApiProviderProps {
  client?: ApiClient;
  config?: ApiClientConfig;
  children: ReactNode;
}

export function ApiProvider({ client, config, children }: ApiProviderProps) {
  const [fallback] = useState(() => createApiClient(config));
  return (
    <ApiContext.Provider value={client ?? fallback}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApi(): ApiClient {
  const client = useContext(ApiContext);
  if (!client) {
    throw new Error("useApi must be used within <ApiProvider>");
  }
  return client;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
    },
  });
}

export type ApiQueryOptions<
  TData,
  TKey extends QueryKey = QueryKey,
> = {
  queryKey: TKey;
  queryFn: (signal: AbortSignal) => Promise<TData>;
} & Omit<UseQueryOptions<TData, Error, TData, TKey>, "queryKey" | "queryFn">;

export function useApiQuery<TData, TKey extends QueryKey = QueryKey>(
  options: ApiQueryOptions<TData, TKey>,
): UseQueryResult<TData, Error> {
  const { queryKey, queryFn, ...rest } = options;
  return useQuery({
    queryKey,
    queryFn: ({ signal }) => queryFn(signal),
    ...rest,
  });
}

export type ApiMutationOptions<TData, TVariables> = {
  mutationFn: (variables: TVariables) => Promise<TData>;
} & Omit<UseMutationOptions<TData, Error, TVariables>, "mutationFn">;

export function useApiMutation<TData, TVariables = void>(
  options: ApiMutationOptions<TData, TVariables>,
): UseMutationResult<TData, Error, TVariables> {
  return useMutation(options);
}

export { QueryClientProvider, useQueryClient } from "@tanstack/react-query";
