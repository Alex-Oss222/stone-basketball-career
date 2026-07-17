import { createSeasonFoundation } from '../../src/app/commands/createSeasonFoundation'
import type {
  SeasonFoundation,
  SeasonFoundationConfiguration,
} from '../../src/app/commands/createSeasonFoundation'
import type { TeamId } from '../../src/domain/ids'
import type { League } from '../../src/domain/league'
import { parseLocalDate } from '../../src/domain/localDate'
import { generateLeague } from '../../src/generation/generateLeague'
import { serializeLeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import type { LeagueSnapshot } from '../../src/persistence/leagueSnapshot'

// The seed string is arbitrary fixture data; its exact value pins the generated
// league identity, so it is preserved verbatim across the version collapse.
export const FIXTURE_ROOT_SEED = 'league-snapshot-v2-fixture'

export const FIXTURE_CREATION_INPUTS: SeasonFoundationConfiguration =
  Object.freeze({
    startingYear: 2026,
    regularSeasonStartDate: parseLocalDate('2026-10-05'),
    calendarDaySpacing: 3,
    scheduleSeed: 'league-snapshot-v2-schedule',
  })

const fixtureLeague = generateLeague(FIXTURE_ROOT_SEED)
const fixtureFoundation = createSeasonFoundation({
  league: fixtureLeague,
  ...FIXTURE_CREATION_INPUTS,
})

export const FIXTURE_MANAGED_TEAM_ID = fixtureLeague.teams[0].id

export interface LeagueSeasonDomainFixture {
  readonly league: League
  readonly foundation: SeasonFoundation
  readonly managedTeamId: TeamId | null
}

const selectedSnapshot = serializeLeagueSnapshot({
  rootSeed: FIXTURE_ROOT_SEED,
  managedTeamId: FIXTURE_MANAGED_TEAM_ID,
  league: fixtureLeague,
  foundation: fixtureFoundation,
  creationInputs: FIXTURE_CREATION_INPUTS,
})

export function createLeagueSnapshotFixture(
  managedTeamId: TeamId | null = FIXTURE_MANAGED_TEAM_ID,
): LeagueSnapshot {
  return {
    ...structuredClone(selectedSnapshot),
    managedTeamId,
  }
}

/**
 * Returns detached live-domain inputs from the same authoritative source as
 * the serialized fixture. Pure application tests can use these without
 * importing persistence DTO types into production read models.
 */
export function createLeagueSeasonDomainFixture(
  managedTeamId: TeamId | null = FIXTURE_MANAGED_TEAM_ID,
): LeagueSeasonDomainFixture {
  return structuredClone({
    league: fixtureLeague,
    foundation: fixtureFoundation,
    managedTeamId,
  })
}

/**
 * Returns the current fixture DTO with its snapshotVersion literal swapped to a
 * different (monotonic-past) version. Restoration must refuse this as a version
 * mismatch without ever deep-parsing it — the exact shape of an older build's
 * record left in local storage.
 */
export function createLegacyVersionSnapshotFixture(
  storedVersion: number,
): unknown {
  return {
    ...structuredClone(selectedSnapshot),
    snapshotVersion: storedVersion,
  }
}
