import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  LeaguePlayersContent,
  LeagueTeamsContent,
  TeamRosterContent,
} from '../../src/ui/dashboardPages'
import { deriveVersionedOverall } from '../../src/domain/playerDerivations'
import { getTeamRoster } from '../../src/ui/leagueViewModel'

const league = generateLeague('dashboard-pages-fixture')
const controlledTeam = league.teams[0]
const roster = getTeamRoster(league, controlledTeam.id)

describe('dashboard page rendering', () => {
  it('renders the roster table columns with real data and honest deferred slots', () => {
    const markup = renderToStaticMarkup(
      <TeamRosterContent
        league={league}
        team={controlledTeam}
        busy={false}
        onOpenPlayer={() => undefined}
        onChangeTeam={() => undefined}
      />,
    )

    // Every player is a click target for the full player page.
    expect(markup.match(/class="player-name-button"/g)).toHaveLength(12)
    for (const column of [
      'Player',
      'Status',
      'Pos / Role',
      'Age',
      'OVR',
      'Impact',
      'Contract',
      'Dev',
    ]) {
      expect(markup).toContain(column)
    }
    // Real values: every derived Overall appears.
    for (const player of roster) {
      expect(markup).toContain(
        String(deriveVersionedOverall(player.ratings, player.primaryPosition)),
      )
    }
    // No skill grades or Potential on the roster screen.
    expect(markup).not.toContain('grade-badge')
    expect(markup).not.toContain('Potential')
    expect(markup.match(/role="region"/g)).toHaveLength(1)
    expect(markup.match(/tabindex="0"/g)).toHaveLength(1)
  })

  it('hides the quick view until a player is hovered and offers the roster tabs', () => {
    const markup = renderToStaticMarkup(
      <TeamRosterContent
        league={league}
        team={controlledTeam}
        busy={false}
        onOpenPlayer={() => undefined}
        onChangeTeam={() => undefined}
      />,
    )

    // The quick view renders only while hovering/focusing a player.
    expect(markup).not.toContain('player-quick-view')
    for (const tab of ['Players', 'Depth &amp; Roles', 'Contracts', 'Compare']) {
      expect(markup).toContain(tab)
    }
    // Reference columns exist as honest slots.
    for (const column of ['Target', 'Actual', 'USG%', 'Form']) {
      expect(markup).toContain(column)
    }
  })

  it('shows the depth chart on the Depth & Roles tab', () => {
    const markup = renderToStaticMarkup(
      <TeamRosterContent
        league={league}
        team={controlledTeam}
        busy={false}
        onOpenPlayer={() => undefined}
        onChangeTeam={() => undefined}
        initialTab="depth"
      />,
    )

    expect(markup).toContain('Depth Chart')
    for (const position of ['PG', 'SG', 'SF', 'PF', 'C']) {
      expect(markup).toContain(`depth-zone-${position.toLowerCase()}`)
    }
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
