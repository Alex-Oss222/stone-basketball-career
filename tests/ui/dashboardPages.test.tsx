import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  DashboardOverviewContent,
  LeaguePlayersContent,
  LeagueTeamsContent,
  TeamRosterContent,
} from '../../src/ui/dashboardPages'
import { getTeamRoster } from '../../src/ui/leagueViewModel'

const league = generateLeague('dashboard-pages-fixture')
const controlledTeam = league.teams[0]
const roster = getTeamRoster(league, controlledTeam.id)

describe('dashboard page rendering', () => {
  it('describes the empty local state without a false saved status', () => {
    const markup = renderToStaticMarkup(
      <DashboardOverviewContent summary={null} saveState={null} />,
    )

    expect(markup).toContain('No league is currently saved.')
    expect(markup).toContain('No league has been created.')
    expect(markup).not.toContain('Saved locally')
  })

  it('renders supplied schedule-ready progress without inventing results', () => {
    const markup = renderToStaticMarkup(
      <DashboardOverviewContent
        summary={null}
        saveState={null}
        seasonProgress={{
          primary: 'Schedule ready',
          secondary:
            '2026–27 regular-season schedule stored locally. No games have been played.',
        }}
      />,
    )

    expect(markup).toContain('Schedule ready')
    expect(markup).toContain('No games have been played')
    expect(markup).not.toContain('No season started')
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
