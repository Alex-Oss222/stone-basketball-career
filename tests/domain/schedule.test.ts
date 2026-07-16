import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
  MILESTONE_1_REGULAR_SEASON_RULE_SET_ID,
  MILESTONE_1_REGULAR_SEASON_RULE_SET_VERSION,
  buildOpponentRequirementMatrix,
  classifyScheduleConstraints,
  createOpponentRequirement,
  getCanonicalTeamPair,
  getTeamPairKey,
  supportsTeamCount,
} from '../../src/domain/schedule'
import type {
  LeagueSchedule,
  OpponentRequirement,
  ScheduleConstraint,
  ScheduleRuleSet,
} from '../../src/domain/schedule'
import { parseScheduleRuleSetId, parseTeamId } from '../../src/domain/ids'
import type { TeamId } from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'

const TEAM_IDS = [
  'team_alpha',
  'team_bravo',
  'team_charlie',
  'team_delta',
  'team_echo',
  'team_foxtrot',
  'team_golf',
  'team_hotel',
].map(parseTeamId)

describe('Milestone 1 regular-season rule set', () => {
  it('makes identity and version explicit', () => {
    expect(MILESTONE_1_REGULAR_SEASON_RULE_SET.id).toBe(
      MILESTONE_1_REGULAR_SEASON_RULE_SET_ID,
    )
    expect(MILESTONE_1_REGULAR_SEASON_RULE_SET.version).toBe(
      MILESTONE_1_REGULAR_SEASON_RULE_SET_VERSION,
    )
    expect(MILESTONE_1_REGULAR_SEASON_RULE_SET_ID).toBe(
      'schedule_rule_milestone_1_regular_season_v1',
    )
    expectTypeOf(MILESTONE_1_REGULAR_SEASON_RULE_SET).toMatchTypeOf<ScheduleRuleSet>()
  })

  it('describes the complete current eight-team format', () => {
    const ruleSet = MILESTONE_1_REGULAR_SEASON_RULE_SET

    expect(ruleSet.stage).toBe('regular_season')
    expect(ruleSet.teamCountPolicy).toEqual({ kind: 'exact', count: 8 })
    expect(ruleSet.gamesPerTeam).toBe(28)
    expect(ruleSet.expectedTotalGames).toBe(112)
    expect(ruleSet.expectedHomeGamesPerTeam).toBe(14)
    expect(ruleSet.expectedAwayGamesPerTeam).toBe(14)
    expect(ruleSet.gameDayCount).toBe(28)
    expect(ruleSet.expectedGamesPerGameDay).toBe(4)
    expect(ruleSet.everyTeamPlaysEachGameDay).toBe(true)
    expect(ruleSet.allowsTbdOpponents).toBe(false)
    expect(ruleSet.calendarSpacingRules).toEqual({
      minimumDaysBetweenGameDays: 1,
      maximumDaysBetweenGameDays: null,
    })
    expect(ruleSet.opponentPolicy).toEqual({
      kind: 'uniform_round_robin',
      meetingsPerOpponent: 4,
      homeGamesPerOpponent: 2,
      awayGamesPerOpponent: 2,
      sourceTag: 'milestone_1_equal_round_robin',
    })
    expect(supportsTeamCount(8, ruleSet.teamCountPolicy)).toBe(true)
    expect(supportsTeamCount(7, ruleSet.teamCountPolicy)).toBe(false)
    expect(supportsTeamCount(9, ruleSet.teamCountPolicy)).toBe(false)
  })
})

describe('opponent requirement matrix', () => {
  it('constructs all 28 canonical pairs before placement', () => {
    const requirements = buildOpponentRequirementMatrix(
      TEAM_IDS,
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )

    expect(requirements).toHaveLength(28)
    expect(requirements.every((requirement) =>
      requirement.firstTeamId < requirement.secondTeamId)).toBe(true)
    expect(new Set(requirements.map((requirement) =>
      getTeamPairKey(requirement.firstTeamId, requirement.secondTeamId))).size)
      .toBe(28)
    expect(requirements.every((requirement) =>
      requirement.totalMeetings === 4 &&
      requirement.homeGamesForFirstTeam === 2 &&
      requirement.homeGamesForSecondTeam === 2 &&
      requirement.stage === 'regular_season')).toBe(true)

    const homeGamesByTeam = new Map<TeamId, number>()
    for (const requirement of requirements) {
      homeGamesByTeam.set(
        requirement.firstTeamId,
        (homeGamesByTeam.get(requirement.firstTeamId) ?? 0) +
          requirement.homeGamesForFirstTeam,
      )
      homeGamesByTeam.set(
        requirement.secondTeamId,
        (homeGamesByTeam.get(requirement.secondTeamId) ?? 0) +
          requirement.homeGamesForSecondTeam,
      )
    }
    expect([...homeGamesByTeam.values()]).toEqual(Array(8).fill(14))
  })

  it('canonicalizes A/B and B/A as the same pair', () => {
    const [alpha, bravo] = TEAM_IDS

    expect(getCanonicalTeamPair(alpha, bravo)).toEqual(
      getCanonicalTeamPair(bravo, alpha),
    )
    expect(getTeamPairKey(alpha, bravo)).toBe(getTeamPairKey(bravo, alpha))
    expect(() => getCanonicalTeamPair(alpha, alpha)).toThrow(RangeError)
  })

  it('keeps home allocations attached to their input teams while ordering', () => {
    const [alpha, bravo] = TEAM_IDS
    const requirement = createOpponentRequirement(
      bravo,
      alpha,
      3,
      2,
      1,
      'regular_season',
      'custom_balance',
    )

    expect(requirement).toEqual({
      firstTeamId: alpha,
      secondTeamId: bravo,
      totalMeetings: 3,
      homeGamesForFirstTeam: 1,
      homeGamesForSecondTeam: 2,
      stage: 'regular_season',
      sourceTag: 'custom_balance',
    })
  })

  it('rejects invalid requirement counts instead of producing bad numbers', () => {
    const [alpha, bravo] = TEAM_IDS

    expect(() => createOpponentRequirement(
      alpha,
      bravo,
      Number.NaN,
      0,
      0,
      'regular_season',
    )).toThrow(RangeError)
    expect(() => createOpponentRequirement(
      alpha,
      bravo,
      4,
      -1,
      5,
      'regular_season',
    )).toThrow(RangeError)
    expect(() => createOpponentRequirement(
      alpha,
      bravo,
      4,
      1,
      1,
      'regular_season',
    )).toThrow(/allocations must equal total meetings/)
  })

  it('is independent of input and final game placement order', () => {
    const forward = buildOpponentRequirementMatrix(
      TEAM_IDS,
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )
    const reversed = buildOpponentRequirementMatrix(
      [...TEAM_IDS].reverse(),
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )

    expect(reversed).toEqual(forward)
    expectTypeOf<LeagueSchedule['opponentRequirements']>()
      .toEqualTypeOf<readonly OpponentRequirement[]>()
    expectTypeOf<LeagueSchedule['games']>()
      .not.toEqualTypeOf<LeagueSchedule['opponentRequirements']>()
  })

  it('rejects invalid automatic matrix team inputs', () => {
    expect(() => buildOpponentRequirementMatrix(
      TEAM_IDS.slice(0, 7),
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )).toThrow(RangeError)
    expect(() => buildOpponentRequirementMatrix(
      [...TEAM_IDS.slice(0, 7), TEAM_IDS[0]],
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )).toThrow(RangeError)

  })

  it('uses a future rule pack explicit matrix without assuming a round robin', () => {
    const [alpha, bravo, charlie] = TEAM_IDS
    const explicitRuleSet: ScheduleRuleSet = {
      ...MILESTONE_1_REGULAR_SEASON_RULE_SET,
      id: parseScheduleRuleSetId('schedule_rule_custom_v2'),
      version: 2,
      opponentPolicy: {
        kind: 'explicit_matrix',
        sourceTag: 'custom_pack_v2',
        requirements: [
          {
            firstTeamId: bravo,
            secondTeamId: alpha,
            totalMeetings: 3,
            homeGamesForFirstTeam: 2,
            homeGamesForSecondTeam: 1,
            stage: 'regular_season',
          },
          {
            firstTeamId: charlie,
            secondTeamId: alpha,
            totalMeetings: 2,
            homeGamesForFirstTeam: 1,
            homeGamesForSecondTeam: 1,
            stage: 'regular_season',
          },
        ],
      },
    }

    expect(explicitRuleSet.id).toBe('schedule_rule_custom_v2')
    expect(explicitRuleSet.version).toBe(2)
    expect(buildOpponentRequirementMatrix(TEAM_IDS, explicitRuleSet)).toEqual([
      {
        firstTeamId: alpha,
        secondTeamId: bravo,
        totalMeetings: 3,
        homeGamesForFirstTeam: 1,
        homeGamesForSecondTeam: 2,
        stage: 'regular_season',
        sourceTag: 'custom_pack_v2',
      },
      {
        firstTeamId: alpha,
        secondTeamId: charlie,
        totalMeetings: 2,
        homeGamesForFirstTeam: 1,
        homeGamesForSecondTeam: 1,
        stage: 'regular_season',
        sourceTag: 'custom_pack_v2',
      },
    ])
  })

  it('rejects duplicate canonical pairs in an explicit matrix', () => {
    const [alpha, bravo] = TEAM_IDS
    const explicitRuleSet: ScheduleRuleSet = {
      ...MILESTONE_1_REGULAR_SEASON_RULE_SET,
      opponentPolicy: {
        kind: 'explicit_matrix',
        requirements: [
          createOpponentRequirement(
            alpha,
            bravo,
            1,
            1,
            0,
            'regular_season',
          ),
          createOpponentRequirement(
            bravo,
            alpha,
            1,
            1,
            0,
            'regular_season',
          ),
        ],
      },
    }

    expect(() => buildOpponentRequirementMatrix(TEAM_IDS, explicitRuleSet))
      .toThrow(/repeat a canonical team pair/)
  })
})

describe('constraint support classification', () => {
  it('reports future constraints as unsupported instead of ignoring them', () => {
    const constraint: ScheduleConstraint = {
      kind: 'venue_unavailable_on_date',
      severity: 'hard',
      venueReference: 'fictional_arena_alpha',
      date: parseLocalDate('2026-11-10'),
    }

    const classification = classifyScheduleConstraints([constraint])

    expect(classification.supported).toEqual([])
    expect(classification.unsupported).toHaveLength(1)
    expect(classification.unsupported[0].constraint).toBe(constraint)
    expect(classification.unsupported[0].reason).toContain(
      'venue_unavailable_on_date',
    )
  })

  it('can classify capabilities explicitly for a future generator', () => {
    const constraint: ScheduleConstraint = {
      kind: 'team_unavailable_on_date',
      severity: 'hard',
      teamId: TEAM_IDS[0],
      date: parseLocalDate('2026-11-10'),
    }

    expect(classifyScheduleConstraints(
      [constraint],
      ['team_unavailable_on_date'],
    )).toEqual({ supported: [constraint], unsupported: [] })
  })
})
