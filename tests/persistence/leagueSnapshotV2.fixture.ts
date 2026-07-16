import { createSeasonFoundation } from '../../src/app/commands/createSeasonFoundation'
import type { SeasonFoundationConfiguration } from '../../src/app/commands/createSeasonFoundation'
import type { TeamId } from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'
import { generateLeague } from '../../src/generation/generateLeague'
import { serializeLeagueSnapshotV2 } from '../../src/persistence/leagueSnapshotV2'
import type { LeagueSnapshotV2 } from '../../src/persistence/leagueSnapshotV2'
import { createLeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import type { LeagueSnapshotV1 } from '../../src/persistence/leagueSnapshot'

export const V2_FIXTURE_ROOT_SEED = 'league-snapshot-v2-fixture'

export const V2_FIXTURE_CREATION_INPUTS: SeasonFoundationConfiguration =
  Object.freeze({
    startingYear: 2026,
    regularSeasonStartDate: parseLocalDate('2026-10-05'),
    calendarDaySpacing: 3,
    scheduleSeed: 'league-snapshot-v2-schedule',
  })

const fixtureLeague = generateLeague(V2_FIXTURE_ROOT_SEED)
const fixtureFoundation = createSeasonFoundation({
  league: fixtureLeague,
  ...V2_FIXTURE_CREATION_INPUTS,
})

export const V2_FIXTURE_MANAGED_TEAM_ID = fixtureLeague.teams[0].id

const selectedSnapshot = serializeLeagueSnapshotV2({
  rootSeed: V2_FIXTURE_ROOT_SEED,
  managedTeamId: V2_FIXTURE_MANAGED_TEAM_ID,
  league: fixtureLeague,
  foundation: fixtureFoundation,
  creationInputs: V2_FIXTURE_CREATION_INPUTS,
})

const v1Snapshot = createLeagueSnapshot(
  V2_FIXTURE_ROOT_SEED,
  fixtureLeague,
  V2_FIXTURE_MANAGED_TEAM_ID,
)

export function createLeagueSnapshotV2Fixture(
  managedTeamId: TeamId | null = V2_FIXTURE_MANAGED_TEAM_ID,
): LeagueSnapshotV2 {
  return {
    ...structuredClone(selectedSnapshot),
    managedTeamId,
  }
}

export function createLeagueSnapshotV1Fixture(): LeagueSnapshotV1 {
  return structuredClone(v1Snapshot)
}
