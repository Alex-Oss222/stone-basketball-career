import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  EXHIBITION_AWAY_TEAM,
  EXHIBITION_GAME_RESULT,
  EXHIBITION_HOME_TEAM,
  EXHIBITION_PLAYER_INFO,
} from '../../src/dev/exhibitionGameResult'
import { GameResultPage } from '../../src/ui/gameResultPage'

function renderPage() {
  return renderToStaticMarkup(
    <GameResultPage
      result={EXHIBITION_GAME_RESULT}
      homeTeam={EXHIBITION_HOME_TEAM}
      awayTeam={EXHIBITION_AWAY_TEAM}
      playerInfo={EXHIBITION_PLAYER_INFO}
      contextLabel="Exhibition preview · design fixture"
    />,
  )
}

describe('post-game workspace rendering', () => {
  it('renders the final score header with fictional identities only', () => {
    const markup = renderPage()

    expect(markup).toContain('Emberlyn Forgekeepers')
    expect(markup).toContain('Duskmere Nightjars')
    expect(markup).toContain('118')
    expect(markup).toContain('112')
    expect(markup).toContain('Final / OT')
    expect(markup).toContain('Exhibition preview · design fixture')
  })

  it('renders the full quarter line including overtime', () => {
    const markup = renderPage()

    for (const label of ['Q1', 'Q2', 'Q3', 'Q4', 'OT']) {
      expect(markup).toContain(`>${label}<`)
    }
    expect(markup).toContain('EFK')
    expect(markup).toContain('DMN')
  })

  it('defaults to an overview: performers, panel row, then the full box score', () => {
    const markup = renderPage()

    expect(markup).toContain('Top Performers')
    expect(markup).toContain('Dorian Vale')
    expect(markup).toContain('Lucan Merrow')
    expect(markup).toContain('27 PTS')

    // The panel row sits between performers and the box score:
    // Game Flow | Four Factors | Key Moments | Game Info.
    expect(markup).toContain('Game Flow')
    expect(markup).toContain('Four Factors')
    expect(markup).toContain('Effective FG%')
    expect(markup).toContain('Key Moments')
    expect(markup).toContain('Game Info')

    // The box score lives on Overview, not behind a separate tab.
    expect(markup).not.toContain('Box Score')
    expect(markup).toContain('Both Teams')
    expect(markup).toContain('Starters')
    expect(markup).toContain('Bench')
    expect(markup).toContain('DNP')
    expect(markup).toContain('Totals')
    // Both teams render by default: two box-score tables.
    expect((markup.match(/box-score-table/g) ?? []).length).toBe(2)
  })

  it('marks event-log features as coming later instead of inventing them', () => {
    const markup = renderPage()

    expect(markup).toContain('Coming later')
    expect(markup).toContain('Play-by-Play')
    // Charts was removed as a tab — Game Flow lives on Overview instead.
    expect(markup).not.toContain('Charts')
    // Lineups was removed — the box score already shows who played.
    expect(markup).not.toContain('Lineups')
    // The Game Info panel is an honest slot; nothing may render a fabricated
    // venue, attendance, referee, or game-time value.
    expect(markup).not.toContain('Attendance')
    expect(markup).not.toContain('Referees')
  })

  it('keeps records and venue out of the header until standings exist', () => {
    const markup = renderPage()

    expect(markup).toContain('Records &amp; venue')
    // No parenthesized record like (48-20) may appear — season records are
    // standings-era data a single GameResult cannot know.
    expect(markup).not.toMatch(/\(\d{1,2}[–-]\d{1,2}\)/)
  })
})
