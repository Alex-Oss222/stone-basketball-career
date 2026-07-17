import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { parseLocalDate } from '../../src/domain/localDate'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  DashboardOverviewContent,
  LeaguePlayersContent,
  LeagueTeamsContent,
  TeamRosterContent,
} from '../../src/ui/dashboardPages'
import { getTeamRoster } from '../../src/ui/leagueViewModel'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

const league = generateLeague('dashboard-pages-fixture')
const controlledTeam = league.teams[0]
const roster = getTeamRoster(league, controlledTeam.id)

describe('dashboard page rendering', () => {
  it('describes the empty local state without a false saved status', () => {
    const markup = renderToStaticMarkup(
      <DashboardOverviewContent
        snapshot={null}
        saveState={null}
      />,
    )

    expect(markup).toContain('No league is currently saved.')
    expect(markup).toContain('No league has been created.')
    expect(markup).not.toContain('Saved locally')
  })

  it('renders the managed team schedule summary and upcoming stored games without fabricated results', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <DashboardOverviewContent
        snapshot={snapshot}
        saveState={{ label: 'Saved locally', state: 'saved' }}
      />,
    )

    expect(markup).toContain(snapshot.season.displayLabel)
    expect(markup).toContain('October 5, 2026')
    expect(markup).toContain('Regular season')
    expect(markup).toContain('<dt>Total games</dt><dd>28</dd>')
    expect(markup).toContain('<dt>Home</dt><dd>14</dd>')
    expect(markup).toContain('<dt>Away</dt><dd>14</dd>')
    expect(markup.match(/class="dashboard-scheduled-game"/g)).toHaveLength(4)
    expect(markup).not.toContain('No season started')
    expect(markup).not.toContain('Score')
    expect(markup).not.toContain('Record')
    expect(markup).not.toContain('Standings')
  })

  it('shows an honest empty state when the stored current date has no future game', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const afterSchedule = {
      ...snapshot,
      season: {
        ...snapshot.season,
        currentDate: parseLocalDate('2027-12-31'),
      },
    }
    const markup = renderToStaticMarkup(
      <DashboardOverviewContent
        snapshot={afterSchedule}
        saveState={{ label: 'Saved locally', state: 'saved' }}
      />,
    )

    expect(markup).toContain(
      'No future scheduled game exists on or after the stored current date.',
    )
    expect(markup).toContain(
      'No additional future scheduled games are available.',
    )
  })

  it('keeps the complete real roster and rating details in keyboard-scrollable regions', () => {
    const markup = renderToStaticMarkup(
      <TeamRosterContent
        league={league}
        team={controlledTeam}
        selectedPlayerId={roster[0].id}
        busy={false}
        onSelectPlayer={() => undefined}
        onChangeTeam={() => undefined}
      />,
    )

    expect(markup.match(/class="player-detail-button"/g)).toHaveLength(12)
    expect(markup.match(/class="grade-badge /g)).toHaveLength(16)
    expect(markup.match(/role="region"/g)).toHaveLength(2)
    expect(markup.match(/tabindex="0"/g)).toHaveLength(2)
  })

  it('renders all eight real teams with only the controlled roster action', () => {
    const markup = renderToStaticMarkup(
      <LeagueTeamsContent
        league={league}
        controlledTeamId={controlledTeam.id}
        busy={false}
        onOpenControlledRoster={() => undefined}
      />,
    )

    expect(markup).toContain('8 fictional teams')
    expect(markup.match(/Open controlled roster/g)).toHaveLength(1)
    expect(markup).toContain('aria-label="League teams table"')
    expect(markup).toContain('tabindex="0"')
  })

  it('renders the complete real player directory and accessible filters', () => {
    const markup = renderToStaticMarkup(<LeaguePlayersContent league={league} />)

    expect(markup).toContain('96 matching players')
    expect(markup).toContain('Player name')
    expect(markup).toContain('Primary position')
    expect(markup).toContain('aria-label="League players table"')
    expect(markup).not.toContain('Overall')
    expect(markup).not.toContain('Potential')
  })
})
