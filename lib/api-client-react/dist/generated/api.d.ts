import type { QueryKey, UseQueryOptions, UseQueryResult } from "@tanstack/react-query";
import type { ArbitrageResponse, ErrorResponse, GetArbitrageOpportunitiesParams, HealthStatus, LineTrackerSlateResponse, NbaBacktestResponse, NbaBetLogResponse, NbaPredictionsResponse, PatternsResponse } from "./api.schemas";
import { customFetch } from "../custom-fetch";
import type { ErrorType } from "../custom-fetch";
type AwaitedInput<T> = PromiseLike<T> | T;
type Awaited<O> = O extends AwaitedInput<infer T> ? T : never;
type SecondParameter<T extends (...args: never) => unknown> = Parameters<T>[1];
/**
 * @summary Health check
 */
export declare const getHealthCheckUrl: () => string;
export declare const healthCheck: (options?: RequestInit) => Promise<HealthStatus>;
export declare const getHealthCheckQueryKey: () => readonly ["/api/healthz"];
export declare const getHealthCheckQueryOptions: <TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData> & {
    queryKey: QueryKey;
};
export type HealthCheckQueryResult = NonNullable<Awaited<ReturnType<typeof healthCheck>>>;
export type HealthCheckQueryError = ErrorType<unknown>;
/**
 * @summary Health check
 */
export declare function useHealthCheck<TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Fetches and parses bet_slate_latest.csv from the Line-Tracker-Model GitHub repo
 * @summary Get today's bet slate
 */
export declare const getGetLineTrackerSlateUrl: () => string;
export declare const getLineTrackerSlate: (options?: RequestInit) => Promise<LineTrackerSlateResponse>;
export declare const getGetLineTrackerSlateQueryKey: () => readonly ["/api/line-tracker/slate"];
export declare const getGetLineTrackerSlateQueryOptions: <TData = Awaited<ReturnType<typeof getLineTrackerSlate>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerSlate>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerSlate>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetLineTrackerSlateQueryResult = NonNullable<Awaited<ReturnType<typeof getLineTrackerSlate>>>;
export type GetLineTrackerSlateQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get today's bet slate
 */
export declare function useGetLineTrackerSlate<TData = Awaited<ReturnType<typeof getLineTrackerSlate>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerSlate>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Fetches patterns.json from the Line-Tracker-Model GitHub repo
 * @summary Get discovered betting patterns
 */
export declare const getGetLineTrackerPatternsUrl: () => string;
export declare const getLineTrackerPatterns: (options?: RequestInit) => Promise<PatternsResponse>;
export declare const getGetLineTrackerPatternsQueryKey: () => readonly ["/api/line-tracker/patterns"];
export declare const getGetLineTrackerPatternsQueryOptions: <TData = Awaited<ReturnType<typeof getLineTrackerPatterns>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerPatterns>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerPatterns>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetLineTrackerPatternsQueryResult = NonNullable<Awaited<ReturnType<typeof getLineTrackerPatterns>>>;
export type GetLineTrackerPatternsQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get discovered betting patterns
 */
export declare function useGetLineTrackerPatterns<TData = Awaited<ReturnType<typeof getLineTrackerPatterns>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getLineTrackerPatterns>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Fetches predictions.json from the nba-betting-model GitHub repo
 * @summary Get today's NBA predictions
 */
export declare const getGetNbaModelPredictionsUrl: () => string;
export declare const getNbaModelPredictions: (options?: RequestInit) => Promise<NbaPredictionsResponse>;
export declare const getGetNbaModelPredictionsQueryKey: () => readonly ["/api/nba-model/predictions"];
export declare const getGetNbaModelPredictionsQueryOptions: <TData = Awaited<ReturnType<typeof getNbaModelPredictions>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelPredictions>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getNbaModelPredictions>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetNbaModelPredictionsQueryResult = NonNullable<Awaited<ReturnType<typeof getNbaModelPredictions>>>;
export type GetNbaModelPredictionsQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get today's NBA predictions
 */
export declare function useGetNbaModelPredictions<TData = Awaited<ReturnType<typeof getNbaModelPredictions>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelPredictions>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Fetches bet_log.json from the nba-betting-model GitHub repo
 * @summary Get NBA bet log
 */
export declare const getGetNbaModelBetLogUrl: () => string;
export declare const getNbaModelBetLog: (options?: RequestInit) => Promise<NbaBetLogResponse>;
export declare const getGetNbaModelBetLogQueryKey: () => readonly ["/api/nba-model/bet-log"];
export declare const getGetNbaModelBetLogQueryOptions: <TData = Awaited<ReturnType<typeof getNbaModelBetLog>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBetLog>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBetLog>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetNbaModelBetLogQueryResult = NonNullable<Awaited<ReturnType<typeof getNbaModelBetLog>>>;
export type GetNbaModelBetLogQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get NBA bet log
 */
export declare function useGetNbaModelBetLog<TData = Awaited<ReturnType<typeof getNbaModelBetLog>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBetLog>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Fetches backtest.json from the nba-betting-model GitHub repo
 * @summary Get NBA backtest metrics
 */
export declare const getGetNbaModelBacktestUrl: () => string;
export declare const getNbaModelBacktest: (options?: RequestInit) => Promise<NbaBacktestResponse>;
export declare const getGetNbaModelBacktestQueryKey: () => readonly ["/api/nba-model/backtest"];
export declare const getGetNbaModelBacktestQueryOptions: <TData = Awaited<ReturnType<typeof getNbaModelBacktest>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBacktest>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBacktest>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetNbaModelBacktestQueryResult = NonNullable<Awaited<ReturnType<typeof getNbaModelBacktest>>>;
export type GetNbaModelBacktestQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get NBA backtest metrics
 */
export declare function useGetNbaModelBacktest<TData = Awaited<ReturnType<typeof getNbaModelBacktest>>, TError = ErrorType<ErrorResponse>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getNbaModelBacktest>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Calls OddsJam API using ODDSJAM_API_KEY env var to find live arbitrage opportunities. Falls back gracefully if the key is not configured.

 * @summary Get live arbitrage opportunities
 */
export declare const getGetArbitrageOpportunitiesUrl: (params?: GetArbitrageOpportunitiesParams) => string;
export declare const getArbitrageOpportunities: (params?: GetArbitrageOpportunitiesParams, options?: RequestInit) => Promise<ArbitrageResponse>;
export declare const getGetArbitrageOpportunitiesQueryKey: (params?: GetArbitrageOpportunitiesParams) => readonly ["/api/arbitrage/opportunities", ...GetArbitrageOpportunitiesParams[]];
export declare const getGetArbitrageOpportunitiesQueryOptions: <TData = Awaited<ReturnType<typeof getArbitrageOpportunities>>, TError = ErrorType<ErrorResponse>>(params?: GetArbitrageOpportunitiesParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getArbitrageOpportunities>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getArbitrageOpportunities>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetArbitrageOpportunitiesQueryResult = NonNullable<Awaited<ReturnType<typeof getArbitrageOpportunities>>>;
export type GetArbitrageOpportunitiesQueryError = ErrorType<ErrorResponse>;
/**
 * @summary Get live arbitrage opportunities
 */
export declare function useGetArbitrageOpportunities<TData = Awaited<ReturnType<typeof getArbitrageOpportunities>>, TError = ErrorType<ErrorResponse>>(params?: GetArbitrageOpportunitiesParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getArbitrageOpportunities>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export {};
//# sourceMappingURL=api.d.ts.map