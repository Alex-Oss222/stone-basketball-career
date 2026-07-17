import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'
import {
  LeagueScheduleOverviewContent,
  ScheduleCalendarContent,
  TeamScheduleContent,
} from '../../src/ui/schedulePages'

describe('TeamScheduleContent', () => {
  it('renders all 28 stored managed-team games with accessible filters and headers', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const managedTeam = snapshot.league.teams.find(
      (team) => team.id === snapshot.managedTeamId,
    )
    if (managedTeam === undefined) throw new Error('Fixture managed team missing')

    const markup = renderToStaticMarkup(
      <TeamScheduleContent snapshot={snapshot} />,
    )

    expect(markup.match(/data-schedule-game=/g)).toHaveLength(28)
    expect(markup).toContain('All games (28)')
    expect(markup).toContain('Home games (14)')
    expect(markup).toContain('Away games (14)')
    expect(markup).toContain('Schedule view')
    expect(markup).toContain('<caption>')
    expect(markup).toContain(snapshot.season.displayLabel)
    expect(markup).toContain(`${managedTeam.city} ${managedTeam.nickname}`)
    expect(markup).toContain('<th scope="col">Scheduled date</th>')
    expect(markup).toContain('<th scope="row">')
    expect(markup).not.toContain('Score')
    expect(markup).not.toContain('Winner')
  })

  it('shows exactly 14 rows for either initial location filter', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const homeMarkup = renderToStaticMarkup(
      <TeamScheduleContent snapshot={snapshot} initialFilter="home" />,
    )
    const awayMarkup = renderToStaticMarkup(
      <TeamScheduleContent snapshot={snapshot} initialFilter="away" />,
    )

    expect(homeMarkup.match(/data-schedule-game=/g)).toHaveLength(14)
    expect(homeMarkup).toContain('14 home games')
    expect(awayMarkup.match(/data-schedule-game=/g)).toHaveLength(14)
    expect(awayMarkup).toContain('14 away games')
  })

  it('requires a managed team instead of inventing a team schedule', () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)
    const markup = renderToStaticMarkup(
      <TeamScheduleContent snapshot={snapshot} />,
    )

    expect(markup).toContain('No managed team selected')
    expect(markup).not.toContain('data-schedule-game')
  })

  it('keeps an unresolved postponed date visibly TBA', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const firstGame = snapshot.leagueSchedule.games.find(
      (game) =>
        game.homeTeamId === snapshot.managedTeamId ||
        game.awayTeamId === snapshot.managedTeamId,
    )
    if (firstGame === undefined) throw new Error('Fixture schedule is empty')

    const postponedSnapshot = {
      ...snapshot,
      leagueSchedule: {
        ...snapshot.leagueSchedule,
        games: snapshot.leagueSchedule.games.map((game) =>
          game.id === firstGame.id
            ? { ...game, status: 'postponed' as const, currentScheduledDate: null }
            : game,
        ),
      },
    }
    const markup = renderToStaticMarkup(
      <TeamScheduleContent snapshot={postponedSnapshot} />,
    )

    expect(markup).toContain('TBA')
    expect(markup).toContain('originally October')
    expect(markup).toContain('Postponed')
  })

  it('shows an honest empty state on every page when no V2 schedule exists', () => {
    const markups = [
      renderToStaticMarkup(<TeamScheduleContent snapshot={null} />),
      renderToStaticMarkup(<ScheduleCalendarContent snapshot={null} />),
      renderToStaticMarkup(<LeagueScheduleOverviewContent snapshot={null} />),
    ]

    for (const markup of markups) {
      expect(markup).toContain('No league schedule available')
      expect(markup).not.toContain('data-schedule-game')
      expect(markup).not.toContain('data-calendar-game')
    }
  })
})

describe('ScheduleCalendarContent', () => {
  it('renders 28 stored game-day groups with all four matchups in each group', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <ScheduleCalendarContent snapshot={snapshot} />,
    )
    const gameDaySections = markup
      .split('<section')
      .filter((section) => section.includes('data-game-day='))

    expect(gameDaySections).toHaveLength(28)
    expect(markup.match(/data-calendar-game=/g)).toHaveLength(112)
    for (const section of gameDaySections) {
      expect(section.match(/data-calendar-game=/g)).toHaveLength(4)
      expect(section).toContain('<caption>')
      expect(section).toContain('<th scope="col">Away team</th>')
      expect(section).toContain('<th scope="col">Home team</th>')
      expect(section).toContain('<th scope="row">')
    }
  })

  it('marks every managed-team matchup with visible text, not color alone', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <ScheduleCalendarContent snapshot={snapshot} />,
    )

    expect(markup.match(/aria-label="Managed team"/g)).toHaveLength(28)
    expect(markup.match(/· Managed team/g)).toHaveLength(28)
  })
})

describe('LeagueScheduleOverviewContent', () => {
  it('summarizes only authoritative season and schedule values', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <LeagueScheduleOverviewContent snapshot={snapshot} />,
    )

    expect(markup).toContain(snapshot.season.displayLabel)
    expect(markup).toContain('Publication status')
    expect(markup).toContain('Draft')
    expect(markup).toContain('<dt>Game days</dt><dd>28</dd>')
    expect(markup).toContain(
      '<dt>Regular-season games</dt><dd>112</dd>',
    )
    expect(markup).toContain('<dt>Teams</dt><dd>8</dd>')
    expect(markup).not.toContain('Standings')
    expect(markup).not.toContain('Record')
    expect(markup).not.toContain('Score')
  })
})
