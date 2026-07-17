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
  it('renders one month of managed-team games with stage and view tabs', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const presentation = createLeaguePresentationBundle(snapshot)
    const managedTeam = presentation.league.teams.find(
      (team) => team.id === presentation.managedTeamId,
    )
    if (managedTeam === undefined) throw new Error('Fixture managed team missing')

    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )

    // Season current date is 2026-10-05, so October 2026 shows by default.
    expect(markup).toContain('October 2026')
    expect(markup).not.toContain('December 2026')
    // Calendar is the default view.
    expect(markup).toContain('team-calendar-grid')
    expect(markup).toMatch(/team-calendar-chip/)
    expect(markup).not.toContain('data-schedule-game')
    expect(markup).toContain('9 games in October 2026')
    // Season totals still appear in the summary.
    expect(markup).toContain('<dt>Total games</dt><dd>28</dd>')
    expect(markup).toContain('<dt>Home games</dt><dd>14</dd>')
    expect(markup).toContain('<dt>Away games</dt><dd>14</dd>')
    // Stage and view tab rows are scaffolded.
    expect(markup).toContain('Regular season')
    expect(markup).toContain('Preseason')
    expect(markup).toContain('Postseason')
    expect(markup).toContain('<span>List</span>')
    expect(markup).toContain('<span>Calendar</span>')
    expect(markup).toContain('Soon')
    expect(markup).toContain('Show previous month')
    expect(markup).toContain('Show next month')
    expect(markup).toContain(`${managedTeam.city} ${managedTeam.nickname}`)
    expect(markup).toContain('Your GM')
    expect(markup).toContain('Off-season')
    expect(markup).not.toContain('Date to be announced')
  })

  it('splits the list view into upcoming and recent games', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    // Season opens on 2026-10-05, so every October game is still upcoming.
    expect(markup).toContain('Upcoming games')
    expect(markup).toContain('October 2026 · 9 games')
    expect(markup.match(/data-schedule-game=/g)).toHaveLength(9)
    // No games have been played yet, so there is no recent-games section.
    expect(markup).not.toContain('Recent games')
  })

  it('renders the next-game command bar, derived badges, and Today control', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const calendar = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} />,
    )
    const list = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    // Next-game command bar with disabled (coming-later) actions.
    expect(calendar).toContain('next-game-bar')
    expect(calendar).toContain('Next game')
    expect(calendar).toContain('Sim Day')
    expect(calendar).toContain('title="Coming later"')
    expect(calendar).toContain('schedule-today-button')
    // Derived schedule-pressure badges appear on games (a road trip in October).
    expect(list).toMatch(/schedule-badge/)
    expect(list).toContain('Road')
  })

  it('renders the inspected team calendar view when selected', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="calendar" />,
    )

    expect(markup).toContain('team-calendar-grid')
    expect(markup).toContain('October 2026')
    expect(markup).toContain('Today')
    expect(markup).toMatch(/team-calendar-chip/)
    expect(markup).not.toContain('role="grid"')
  })

  it('shows an honest placeholder for a scaffolded stage', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const postseason = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialStage="postseason" />,
    )

    expect(postseason).toContain('Coming later')
    expect(postseason).toContain('Postseason schedule')
    expect(postseason).not.toContain('data-schedule-game')
  })

  it('filters the list timeline by All, Upcoming, and Final', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const list = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    // The Results filter replaces the old Results view tab.
    expect(list).toContain('name="team-schedule-results"')
    expect(list).toContain('All games')
    expect(list).toContain('Upcoming')
    expect(list).toContain('Final')
    expect(list).toContain('Upcoming games')
    // No games have been played, so the season opens with no finals.
    expect(list).not.toContain('Final games')
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
    expect(markup).toContain('Return to my team')
    expect(markup).not.toContain('class="managed-team-label"')
    expect(snapshot.managedTeamId).toBe(managedTeamBefore)
    expect(snapshot.revision).toBe(revisionBefore)
  })

  it('permits first-canonical-team inspection when no managed team exists', () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)
    const presentation = createLeaguePresentationBundle(snapshot)
    const firstTeam = presentation.league.teams[0]

    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    expect(markup.match(/data-schedule-game=/g)).toHaveLength(9)
    expect(markup).toContain(`${firstTeam.city} ${firstTeam.nickname}`)
    expect(markup).not.toContain('Return to my team')
    expect(markup).not.toContain('class="managed-team-label"')
  })

  it('applies the site filter within the visible month', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const homeMarkup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialViewMode="list"
        initialFilter="home"
      />,
    )
    const awayMarkup = renderToStaticMarkup(
      <TeamScheduleContent
        presentation={presentation}
        initialViewMode="list"
        initialFilter="away"
      />,
    )

    const homeCount = (homeMarkup.match(/data-schedule-game=/g) ?? []).length
    const awayCount = (awayMarkup.match(/data-schedule-game=/g) ?? []).length

    // Every October game is home or away, so the split covers the month total.
    expect(homeCount + awayCount).toBe(9)
    expect(homeCount).toBeGreaterThan(0)
    expect(awayCount).toBeGreaterThan(0)
    expect(homeMarkup).toMatch(
      /checked="" value="home"|value="home" checked=""/,
    )
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
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    expect(markup).toContain('Date to be announced')
    expect(markup).toContain('Undated schedule games')
    expect(markup).toContain('TBA')
    expect(markup).toContain('Postponed')
  })

  it('renders semantic filters, tables, and focusable game controls', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <TeamScheduleContent presentation={presentation} initialViewMode="list" />,
    )

    expect(markup).toContain('<label for="')
    expect(markup).toContain('>Team</label>')
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

  it('renders a scrollable date-grouped list of full-name games', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const managedTeam = presentation.league.teams.find(
      (team) => team.id === presentation.managedTeamId,
    )
    if (managedTeam === undefined) throw new Error('Fixture managed team missing')

    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} initialViewMode="list" />,
    )

    expect(markup).toContain('league-calendar-daylist')
    expect(markup).toContain('league-calendar-daygroup-header')
    expect(markup).toContain('league-calendar-daygame')
    expect(markup).toContain('games by day')
    // Full weekday-and-date headings, not abbreviations.
    expect(markup).toMatch(/(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), October/)
    // Full team names on a game row, and the managed team is marked.
    expect(markup).toContain(
      `${managedTeam.city} ${managedTeam.nickname}`,
    )
    expect(markup).toContain('is-managed')
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

  it('shows a derived league-events timeline with the next milestone', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const markup = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} />,
    )

    expect(markup).toContain('League events')
    expect(markup).toContain('Trade deadline')
    expect(markup).toContain('All-Star break')
    expect(markup).toContain('Draft')
    // The first milestone on or after the current date is flagged.
    expect(markup).toContain('league-timeline-item is-next')
    expect(markup).toContain('Next:')
  })

  it('shows the derived schedule overview and swaps the complementary panel', () => {
    const presentation = createLeaguePresentationBundle(
      createLeagueSnapshotV2Fixture(),
    )
    const calendar = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} />,
    )
    const list = renderToStaticMarkup(
      <LeagueCalendarContent presentation={presentation} initialViewMode="list" />,
    )

    // Managed team → derived, no-simulation overview panel.
    expect(calendar).toContain('Schedule overview')
    expect(calendar).toContain('Games remaining')
    expect(calendar).toContain('Back-to-backs')
    expect(calendar).toContain('Longest road trip')
    expect(calendar).toContain('Broadcast')
    // Calendar view shows the day agenda; list view swaps in the mini calendar.
    expect(calendar).toContain('league-calendar-agenda')
    expect(calendar).not.toContain('league-calendar-mini')
    expect(list).toContain('league-calendar-mini')
    expect(list).not.toContain('league-calendar-agenda')
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
