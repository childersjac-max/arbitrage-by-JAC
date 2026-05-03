/**
 * src/hooks/use-oddsjam.ts
 *
 * React Query hooks for OddsJam data + alerts CRUD.
 * All API calls use apiUrl() so they work on Vercel, dev proxy, and custom domains.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchGames, fetchOdds, fetchSports, OddsJamGame, OddsJamOdds, OddsJamSport } from '../lib/oddsjam-client';
import { apiUrl } from '../lib/api-base';

// ---------------------------------------------------------------------------
// OddsJam data hooks
// ---------------------------------------------------------------------------

/** All active games, optionally filtered by sport slug. */
export function useGames(sport?: string) {
  return useQuery<OddsJamGame[], Error>({
    queryKey: ['games', sport ?? 'all'],
    queryFn: () => fetchGames(sport),
    staleTime: 30_000,       // treat data as fresh for 30 s
    refetchInterval: 30_000, // background refetch every 30 s (matches your dashboard)
  });
}

/** Live odds, refreshed every 30 s. Optionally scoped to a list of game IDs. */
export function useOdds(gameIds?: string[]) {
  return useQuery<OddsJamOdds[], Error>({
    queryKey: ['odds', gameIds ?? 'all'],
    queryFn: () => fetchOdds(gameIds),
    staleTime: 30_000,
    refetchInterval: 30_000,
    enabled: gameIds === undefined || gameIds.length > 0,
  });
}

/** All OddsJam-supported sports (rarely changes — long stale time). */
export function useSports() {
  return useQuery<OddsJamSport[], Error>({
    queryKey: ['sports'],
    queryFn: fetchSports,
    staleTime: 5 * 60_000, // 5 minutes
  });
}

// ---------------------------------------------------------------------------
// Alerts hooks (calls our own backend, not OddsJam directly)
// ---------------------------------------------------------------------------

export interface Alert {
  id: number;
  sport: string;
  min_profit: number;
  label: string;
  created_at: string;
}

interface CreateAlertPayload {
  sport: string;
  min_profit: number;
  label: string;
}

async function fetchAlerts(): Promise<Alert[]> {
  const res = await fetch(apiUrl('/api/alerts'));
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.status}`);
  return res.json();
}

async function createAlert(payload: CreateAlertPayload): Promise<Alert> {
  const res = await fetch(apiUrl('/api/alerts'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to create alert: ${res.status}`);
  return res.json();
}

async function deleteAlert(id: number): Promise<void> {
  const res = await fetch(apiUrl(`/api/alerts/${id}`), { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete alert: ${res.status}`);
}

/** Read all saved alerts. */
export function useAlerts() {
  return useQuery<Alert[], Error>({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
  });
}

/** Create a new alert — optimistically updates the list. */
export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation<Alert, Error, CreateAlertPayload>({
    mutationFn: createAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });
}

/** Delete an alert by ID — optimistically removes it from the list. */
export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteAlert,
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['alerts'] });
      const prev = qc.getQueryData<Alert[]>(['alerts']);
      qc.setQueryData<Alert[]>(['alerts'], (old) => old?.filter((a) => a.id !== id) ?? []);
      return { prev };
    },
    onError: (_err, _id, context: any) => {
      if (context?.prev) qc.setQueryData(['alerts'], context.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });
}
