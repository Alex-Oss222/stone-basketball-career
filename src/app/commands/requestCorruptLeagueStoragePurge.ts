export const CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION =
  'Permanently delete the active local league save from this browser? This removes the current and legacy active-league snapshots and cannot be undone.'

export interface CorruptLeagueStoragePurgeRequest {
  readonly confirm: (message: string) => boolean
  readonly purge: () => Promise<void>
}

export type CorruptLeagueStoragePurgeResult = 'cancelled' | 'purged'

export async function requestCorruptLeagueStoragePurge(
  request: CorruptLeagueStoragePurgeRequest,
): Promise<CorruptLeagueStoragePurgeResult> {
  if (!request.confirm(CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION)) {
    return 'cancelled'
  }

  await request.purge()
  return 'purged'
}
