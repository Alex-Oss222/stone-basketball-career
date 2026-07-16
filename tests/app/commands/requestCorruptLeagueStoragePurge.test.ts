import { describe, expect, it, vi } from 'vitest'
import {
  CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION,
  requestCorruptLeagueStoragePurge,
} from '../../../src/app/commands/requestCorruptLeagueStoragePurge'

describe('requestCorruptLeagueStoragePurge', () => {
  it('cancels without calling storage when confirmation is declined', async () => {
    const confirm = vi.fn(() => false)
    const purge = vi.fn(async () => undefined)

    await expect(
      requestCorruptLeagueStoragePurge({ confirm, purge }),
    ).resolves.toBe('cancelled')

    expect(confirm).toHaveBeenCalledOnce()
    expect(confirm).toHaveBeenCalledWith(
      CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION,
    )
    expect(purge).not.toHaveBeenCalled()
  })

  it('uses explicit permanent-deletion confirmation copy', () => {
    expect(CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION).toContain(
      'Permanently delete',
    )
    expect(CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION).toContain(
      'version 1 and version 2',
    )
    expect(CORRUPT_LEAGUE_STORAGE_PURGE_CONFIRMATION).toContain(
      'cannot be undone',
    )
  })

  it('propagates a purge failure instead of reporting success', async () => {
    const failure = new Error('transient transaction failure')

    await expect(
      requestCorruptLeagueStoragePurge({
        confirm: () => true,
        purge: async () => {
          throw failure
        },
      }),
    ).rejects.toBe(failure)
  })

  it('allows retry after a transient purge failure', async () => {
    const failure = new Error('transient transaction failure')
    const confirm = vi.fn(() => true)
    const purge = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(failure)
      .mockResolvedValueOnce(undefined)

    await expect(
      requestCorruptLeagueStoragePurge({ confirm, purge }),
    ).rejects.toBe(failure)
    await expect(
      requestCorruptLeagueStoragePurge({ confirm, purge }),
    ).resolves.toBe('purged')

    expect(confirm).toHaveBeenCalledTimes(2)
    expect(purge).toHaveBeenCalledTimes(2)
  })
})
