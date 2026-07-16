import {
  createSeasonFoundation,
  parseSeasonFoundationConfiguration,
} from './createSeasonFoundation'
import type { SeasonFoundationConfigurationInput } from './createSeasonFoundation'
import { generateLeague } from '../../generation/generateLeague'
import {
  parseLeagueSnapshotV2,
  serializeLeagueSnapshotV2,
} from '../../persistence/leagueSnapshotV2'
import type { LeagueSnapshotV2 } from '../../persistence/leagueSnapshotV2'
import { normalizeSeed } from '../../random/seed'

export interface CreateNewLeagueSnapshotV2Input
  extends SeasonFoundationConfigurationInput {
  readonly rootSeed: string
}

/**
 * Creates one complete initial V2 application snapshot without performing I/O.
 * The visible league seed uses the existing trusted creation normalization,
 * while season configuration follows the coordinator's stricter contract.
 */
export function createNewLeagueSnapshotV2(
  input: CreateNewLeagueSnapshotV2Input,
): LeagueSnapshotV2 {
  const rootSeed = normalizeSeed(input.rootSeed)
  const creationInputs = parseSeasonFoundationConfiguration(input)
  const league = generateLeague(rootSeed)
  const foundation = createSeasonFoundation({
    league,
    ...creationInputs,
  })

  return parseLeagueSnapshotV2(
    serializeLeagueSnapshotV2({
      rootSeed,
      managedTeamId: null,
      league,
      foundation,
      creationInputs,
    }),
  )
}
