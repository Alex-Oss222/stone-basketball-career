import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { deriveOverall } from '../../src/domain/playerDerivations'
import { getTeamRoster } from '../../src/ui/leagueViewModel'
import { PlayerQuickView } from '../../src/ui/playerQuickView'

const league = generateLeague('player-quick-view-fixture')
const team = league.teams[0]
const player = getTeamRoster(league, team.id)[0]
const markup = renderToStaticMarkup(
  <PlayerQuickView player={player} team={team} />,
)

describe('Player Quick View', () => {
  it('shows real identity and the derived Overall', () => {
    expect(markup).toContain(`${player.firstName} ${player.lastName}`)
    expect(markup).toContain('OVR')
    expect(markup).toContain(String(deriveOverall(player)))
    // The player's primary position is marked as a natural fit.
    expect(markup).toContain('Natural')
  })

  it('renders the left-to-right key stats strip honestly deferred', () => {
    for (const label of [
      'PTS',
      'REB',
      'AST',
      'STL',
      'BLK',
      'FG%',
      '3P%',
      'TS%',
    ]) {
      expect(markup).toContain(label)
    }
    expect(markup).toContain('Coming later')
  })

  it('renders Target Role, Contract, and Position Coverage as field-row blocks', () => {
    for (const label of [
      'Target Role',
      'Actual Role',
      'Target MPG',
      'Actual MPG',
      'Usage Rate',
      'Contract',
      'Years Left',
      'Guaranteed',
      'Total Value',
      'Contract Type',
      'Position',
    ]) {
      expect(markup).toContain(label)
    }
    expect(markup.match(/class="pqv-field-rows"/g)).toHaveLength(3)
  })

  it('always shows the Overview/Health/Development tab strip, but no grades, action buttons, or potential', () => {
    // The tab strip is always present (not pin-gated).
    for (const tab of ['Overview', 'Health', 'Development']) {
      expect(markup).toContain(tab)
    }
    // The only buttons are the three tabs — no action buttons, no close button
    // (that arrives only when pinned).
    expect(markup.match(/<button/g)).toHaveLength(3)
    expect(markup).not.toContain('Close quick view')
    // Still a display-only preview: no grades, no Potential.
    expect(markup).not.toContain('grade-badge')
    expect(markup).not.toContain('Potential')
  })

  it('pinned mode keeps the tab strip and adds the close button and Health/Development slots', () => {
    const pinnedMarkup = renderToStaticMarkup(
      <PlayerQuickView
        player={player}
        team={team}
        pinned
        onClose={() => undefined}
      />,
    )
    const healthMarkup = renderToStaticMarkup(
      <PlayerQuickView player={player} team={team} pinned initialTab="health" />,
    )
    const developmentMarkup = renderToStaticMarkup(
      <PlayerQuickView
        player={player}
        team={team}
        pinned
        initialTab="development"
      />,
    )

    for (const tab of ['Overview', 'Health', 'Development']) {
      expect(pinnedMarkup).toContain(tab)
    }
    expect(pinnedMarkup).toContain('Close quick view')
    expect(healthMarkup).toContain('Minutes Cap')
    expect(healthMarkup).toContain('Coming later')
    expect(developmentMarkup).toContain('Primary Focus')
    expect(developmentMarkup).toContain('Assigned Coach')
  })

  it('fabricates no stat, record, streak, or dollar figure', () => {
    const visible = markup
      .replace(/datetime="[^"]*"/gi, '')
      .replace(/style="[^"]*"/gi, '')
    // No score/record-like "NN-NN".
    expect(visible).not.toMatch(/\b\d{2,3}\s*[–-]\s*\d{2,3}\b/)
    // No fabricated streak-like "W3" / "L5".
    expect(visible).not.toMatch(/\b[WL]\d+\b/)
    // No fabricated contract dollars.
    expect(visible).not.toMatch(/\$\d/)
  })
})
