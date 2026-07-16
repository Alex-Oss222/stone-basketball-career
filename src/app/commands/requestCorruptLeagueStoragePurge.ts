export const CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION =
  'Permanently delete the local league save from this browser? This removes every active version 1 and version 2 league snapshot and cannot be undone.'

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
