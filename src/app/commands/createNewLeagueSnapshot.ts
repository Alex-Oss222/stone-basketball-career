import {
  createSeasonFoundation,
  parseSeasonFoundationConfiguration,
} from './createSeasonFoundation'
import type { SeasonFoundationConfigurationInput } from './createSeasonFoundation'
import { generateLeague } from '../../generation/generateLeague'
import {
  parseLeagueSnapshot,
  serializeLeagueSnapshot,
} from '../../persistence/leagueSnapshot'
import type { LeagueSnapshot } from '../../persistence/leagueSnapshot'
import { normalizeSeed } from '../../random/seed'

export interface CreateNewLeagueSnapshotInput
  extends SeasonFoundationConfigurationInput {
  readonly rootSeed: string
}

/**
 * Creates one complete initial application snapshot without performing I/O.
 * The visible league seed uses the existing trusted creation normalization,
 * while season configuration follows the coordinator's stricter contract.
 */
export function createNewLeagueSnapshot(
  input: CreateNewLeagueSnapshotInput,
): LeagueSnapshot {
  const rootSeed = normalizeSeed(input.rootSeed)
  const creationInputs = parseSeasonFoundationConfiguration(input)
  const league = generateLeague(rootSeed)
  const foundation = createSeasonFoundation({
    league,
    ...creationInputs,
  })

  return parseLeagueSnapshot(
    serializeLeagueSnapshot({
      rootSeed,
      managedTeamId: null,
      league,
      foundation,
      creationInputs,
    }),
  )
}
