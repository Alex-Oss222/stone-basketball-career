import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { ratingToGrade } from '../../src/domain/ratings'
import { deriveOverall } from '../../src/domain/playerDerivations'
import { getTeamRoster } from '../../src/ui/leagueViewModel'
import { PlayerPageContent } from '../../src/ui/playerPage'
import type { PlayerPageTab } from '../../src/ui/playerPage'

const league = generateLeague('player-page-fixture')
const team = league.teams[0]
const roster = getTeamRoster(league, team.id)
const player = roster[0]

function renderPage(options?: {
  readonly initialTab?: PlayerPageTab
}): string {
  return renderToStaticMarkup(
    <PlayerPageContent
      player={player}
      team={team}
      roster={roster}
      busy={false}
      onBack={() => undefined}
      onSelectPlayer={() => undefined}
      initialTab={options?.initialTab}
    />,
  )
}

describe('Player page', () => {
  it('shows real identity and the derived Overall with its letter — no Potential, no badges', () => {
    const markup = renderPage()
    const overall = deriveOverall(player)

    expect(markup).toContain(`${player.firstName} ${player.lastName}`)
    expect(markup).toContain('OVR')
    expect(markup).toContain(String(overall))
    expect(markup).toContain(ratingToGrade(overall))
    expect(markup).not.toContain('Potential')
    expect(markup).not.toContain('POTENTIAL')
    expect(markup).not.toContain('Badges')
  })

  it('renders the roster rail with every teammate and the open player marked', () => {
    const markup = renderPage()

    expect(markup.match(/class="player-rail-button"/g)).toHaveLength(12)
    expect(markup.match(/aria-current="true"/g)).toHaveLength(2) // rail + Overview tab
    expect(markup).toContain('Team Chemistry')
  })

  it('renders the stat-card row and hero profile with honest deferred slots', () => {
    const markup = renderPage()

    for (const label of [
      'Contract',
      'Health',
      'Morale',
      'Fatigue',
      'Draft',
      'Agent',
      'Personality',
      'Work Ethic',
      'Quick Summary',
    ]) {
      expect(markup).toContain(label)
    }
    expect(markup).toContain('Coming later')
  })

  it('overview imposes the reference: profiles, stats, zones, letters, concerns/strengths', () => {
    const markup = renderPage()

    for (const section of [
      'Position Profiles',
      'Season Stats',
      'Shooting Zones',
      'Physicals',
      'Mental',
      'Skill Breakdown',
      'Concerns',
      'Strengths',
    ]) {
      expect(markup).toContain(section)
    }
    // Season stat labels are present but only as honest dashes.
    for (const stat of ['MIN', 'USG%', 'PER']) {
      expect(markup).toContain(stat)
    }
    // The court spans the badges area with dashed zones.
    for (const zone of ['Paint', 'Left Corner 3', 'Top 3', 'Free Throw']) {
      expect(markup).toContain(zone)
    }
    expect(markup).toContain('Natural')
    // 26 category letters + 8 derived concern/strength letters.
    expect(markup.match(/class="grade-list-label"/g)).toHaveLength(34)
    // New detailed categories from the rehaul surface on the page.
    expect(markup).toContain('Durability')
    expect(markup).toContain('Post Scoring')
    expect(markup).toContain('Off-Ball Offense')
    expect(markup).toContain('Competitive Makeup')
  })

  it('skills tab is a collapsed letter accordion — sub-ratings only drop down on click', () => {
    const markup = renderPage({ initialTab: 'skills' })

    expect(markup.match(/aria-expanded="false"/g)).toHaveLength(26)
    expect(markup).not.toContain('aria-expanded="true"')
    expect(markup).not.toContain('grade-accordion-panel')
    // Collapsed: no sub-rating labels leak out.
    expect(markup).not.toContain('Standing Finish')
  })

  it('keeps the tab strip and the four reference actions, all honestly gated', () => {
    const markup = renderPage()

    for (const tab of ['Overview', 'Skills', 'Performance', 'Role', 'Career']) {
      expect(markup).toContain(tab)
    }
    for (const action of [
      'Compare Player',
      'Trade Player',
      'Watch Player',
      'Edit Player',
    ]) {
      expect(markup).toContain(action)
    }
    expect(markup).toContain('Back to roster')
    expect(markup).not.toContain('Trade Block')
    expect(markup).not.toContain('Trade Center')
  })

  it('fabricates no stat, record, streak, or dollar figure', () => {
    const visible = renderPage()
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
