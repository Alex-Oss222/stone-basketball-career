import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { createLeaguePresentationBundle } from '../../src/app/leagueSnapshotDomainAdapter'
import {
  LeagueCalendarContent,
  LeagueScheduleOverviewContent,
  TeamScheduleContent,
} from '../../src/ui/schedulePages'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

describe('TeamScheduleContent', () => {
  it('renders all 28 managed-team games in chronological month sections', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const presentation = createLeaguePresentationBundle(snapshot)
    const managedTeam = presentation.league.teams.find(
      (team) => team.id === presentation.managedTeamId,
    )
    if (managedTeam === undefined) throw new Error('Fixture managed team missing')

    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )

    expect(markup.match(/data-schedule-game=/g)).toHaveLength(28)
    expect(markup).toContain('Showing 28 of 28 games')
    expect(markup).toContain('<dt>Total games</dt><dd>28</dd>')
    expect(markup).toContain('<dt>Home games</dt><dd>14</dd>')
    expect(markup).toContain('<dt>Away games</dt><dd>14</dd>')
    expect(markup).toContain('October 2026')
    expect(markup).toContain('December 2026')
    expect(markup).toContain(`${managedTeam.city} ${managedTeam.nickname}`)
    expect(markup).toContain(`(${managedTeam.abbreviation})`)
    expect(markup).toContain('Managed team')
    expect(markup).toContain('Contains next game')
    expect(markup).toContain('Next game')
    expect(markup).not.toContain('Date to be announced')
  })

  it('provides all eight inspected teams without changing managed ownership', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const presentation = createLeaguePresentationBundle(snapshot)
    const inspectedTeamId = presentation.league.teams[3].id
    const revisionBefore = snapshot.revision
    const managedTeamBefore = snapshot.managedTeamId

    const markup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialInspectedTeamId={inspectedTeamId}
      />,
    )

    expect(markup.match(/<option/g)).toHaveLength(8)
    for (const team of presentation.league.teams) {
      expect(markup).toContain(
        `${team.city} ${team.nickname} (${team.abbreviation})`,
      )
    }
    expect(markup).toContain('Return to managed team')
    expect(markup).not.toContain('class="managed-team-label"')
    expect(snapshot.managedTeamId).toBe(managedTeamBefore)
    expect(snapshot.revision).toBe(revisionBefore)
  })

  it('permits first-canonical-team inspection when no managed team exists', () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)
    const presentation = createLeaguePresentationBundle(snapshot)
    const firstTeam = presentation.league.teams[0]

    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )

    expect(markup.match(/data-schedule-game=/g)).toHaveLength(28)
    expect(markup).toContain(`${firstTeam.city} ${firstTeam.nickname}`)
    expect(markup).not.toContain('Return to managed team')
    expect(markup).not.toContain('class="managed-team-label"')
  })

  it('renders exactly 14 rows for either initial site filter in stored order', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const homeMarkup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialFilter="home"
      />,
    )
    const awayMarkup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialFilter="away"
      />,
    )

    expect(homeMarkup.match(/data-schedule-game=/g)).toHaveLength(14)
    expect(homeMarkup).toContain('Showing 14 of 28 games')
    expect(homeMarkup).toMatch(
      /checked="" value="home"|value="home" checked=""/,
    )
    expect(awayMarkup.match(/data-schedule-game=/g)).toHaveLength(14)
    expect(awayMarkup).toContain('Showing 14 of 28 games')
    expect(awayMarkup).toMatch(
      /checked="" value="away"|value="away" checked=""/,
    )
  })

  it('keeps an unresolved postponed game in the explicit TBA section', () => {
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
            ? {
                ...game,
                status: 'postponed' as const,
                currentScheduledDate: null,
              }
            : game,
        ),
      },
    }
    const presentation = createLeaguePresentationBundle(postponedSnapshot)
    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )

    expect(markup).toContain('Date to be announced')
    expect(markup).toContain('Undated schedule games')
    expect(markup).toContain('TBA')
    expect(markup).toContain('Postponed')
    expect(markup.match(/data-schedule-game=/g)).toHaveLength(28)
  })

  it('renders semantic filters, tables, and focusable game controls', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )

    expect(markup).toContain('<label for="')
    expect(markup).toContain('>Inspect team</label>')
    expect(markup).toContain('<fieldset class="team-schedule-site-filters">')
    expect(markup).toContain('<legend>Game site</legend>')
    expect(markup).toContain('type="radio"')
    expect(markup).toContain('<caption>')
    expect(markup).toContain('<th scope="col">Game</th>')
    expect(markup).toContain('<th scope="col">Date</th>')
    expect(markup).toContain('<th scope="row"')
    expect(markup).toContain('class="team-schedule-game-button"')
    expect(markup).toContain('aria-label="Open game ')
    expect(markup).not.toContain('role="grid"')
  })

  it('renders the shared details surface from the selected game view model', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const managedGames = presentation.schedule.games.filter(
      (game) =>
        game.homeTeamId === presentation.managedTeamId ||
        game.awayTeamId === presentation.managedTeamId,
    )
    const selectedGame = managedGames[13]
    if (selectedGame === undefined) throw new Error('Middle team game missing')

    const markup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialSelectedGameId={selectedGame.id}
      />,
    )

    expect(markup).toContain(`data-game-details="${selectedGame.id}"`)
    expect(markup).toContain('aria-modal="true"')
    expect(markup).toContain('Game details')
    expect(markup).toContain('Away team')
    expect(markup).toContain('Home team')
    expect(markup).toContain('Competition stage')
    expect(markup).toContain('Original scheduled date')
    expect(markup).toContain('Previous inspected-team game')
    expect(markup).toContain('Next inspected-team game')
    expect(markup).toContain('aria-label="Close game details"')
    expect(markup).not.toContain('<dt>Actual date</dt>')
    expect(markup).not.toMatch(/Score|Winner|Standings|Venue|Tipoff|Box score/)
  })

  it('shows an honest empty state when no hydrated V2 schedule exists', () => {
    const markups = [
      renderToStaticMarkup(
        <TeamScheduleContent presentation={null} />,
      ),
      renderToStaticMarkup(<LeagueCalendarContent presentation={null} />),
      renderToStaticMarkup(<LeagueScheduleOverviewContent snapshot={null} />),
    ]

    for (const markup of markups) {
      expect(markup).toContain('No league schedule available')
      expect(markup).not.toContain('data-schedule-game')
      expect(markup).not.toContain('league-calendar-grid')
    }
  })
})

describe('LeagueCalendarContent', () => {
  it('renders the current month as an accessible table without a grid role', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} />,
    )

    // Season current date is 2026-10-05, so October 2026 is shown by default.
    expect(markup).toContain('October 2026')
    expect(markup).toContain('league calendar')
    expect(markup).toContain('league-calendar-grid')
    expect(markup).toContain('<caption')
    expect(markup).toContain('Sunday')
    expect(markup).toContain('Saturday')
    expect(markup).toContain('name="league-calendar-view"')
    expect(markup).not.toContain('role="grid"')
  })

  it('shows managed-team game chips and the scope toggle by default', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} />,
    )

    // The default managed-team scope marks every visible game with a star.
    expect(markup).toContain('league-calendar-chip')
    expect(markup).toContain('managed-star')
    expect(markup).toContain('All teams')
    expect(markup).toContain('My team')
    expect(markup).toContain('Today')
  })

  it('renders a day-by-day list when the list view is selected', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} initialViewMode="list" />,
    )

    expect(markup).toContain('league-calendar-list')
    expect(markup).toContain('games by day')
    expect(markup).not.toContain('role="grid"')
  })

  it('omits the scope toggle when no managed team exists', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(null),
    )
    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} />,
    )

    expect(markup).not.toContain('name="league-calendar-scope"')
    expect(markup).toContain('league-calendar-grid')
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
