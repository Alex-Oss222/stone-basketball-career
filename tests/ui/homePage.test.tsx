import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { parseLocalDate } from '../../src/domain/localDate'
import { HomeTodayContent } from '../../src/ui/homePage'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

describe('Home rendering', () => {
  it('describes the empty local state without a false saved status', () => {
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={null} saveState={null} />,
    )

    expect(markup).toContain('No league available')
    expect(markup).not.toContain('Saved locally')
  })

  it('renders the command bar and the full card grid', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent
        snapshot={snapshot}
        saveState={{ label: 'Saved locally', state: 'saved' }}
      />,
    )

    expect(markup).toContain(snapshot.season.displayLabel)
    for (const card of [
      'Needs Attention',
      'Roster Health',
      'Front Office',
      'Next Game',
      'Recent Results',
      'Upcoming Games',
      'Standings',
      'Season Pulse',
      'Important Headlines',
      'Team Stats',
    ]) {
      expect(markup).toContain(card)
    }
  })

  it('shows the caught-up state naming the real next event', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    expect(markup).toContain('all caught up')
    expect(markup).toContain('Next event: Game')
  })

  it('splits Standings into division and conference sections', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    expect(markup).toContain('Division Standings')
    expect(markup).toContain('Conference Standings')
    // Two coming-later sections, not two fabricated tables.
    expect(markup).not.toMatch(/<td>\s*\d+\s*<\/td>/)
  })

  it('compares real average ratings in Next Game and defers results-era context', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    expect(markup).toContain('Regular Season Game')
    expect(markup).toContain('Avg rating')
    expect(markup).toContain('Records · Ranks · Last 10')
    expect(markup).toContain('Availability')
  })

  it('fabricates no score or record values anywhere', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent
        snapshot={snapshot}
        saveState={{ label: 'Saved locally', state: 'saved' }}
      />,
    )

    expect(markup).toContain('No completed games yet')
    // No score-like value (e.g. 101-96) may appear in visible text. ISO dates
    // inside datetime attributes legitimately contain digit-dash-digit, so
    // strip attributes and compare visible content only.
    const visibleMarkup = markup.replace(/datetime="[^"]*"/gi, '')
    expect(visibleMarkup).not.toMatch(/\b\d{2,3}\s*[–-]\s*\d{2,3}\b/)
    // No fabricated record-like W/L value (e.g. 12-7, W3, L5).
    expect(visibleMarkup).not.toMatch(/\b[WL]\d+\b/)
  })

  it('keeps simulation-era actions visibly disabled: Continue, Sim, Watch', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    expect(markup).toContain('Continue')
    expect(markup).toContain('Sim to Next Event')
    expect(markup).toContain('Watch Game')
    expect(markup).toContain('Sim Game')
    expect(markup).not.toContain('Prepare Game')
    expect((markup.match(/disabled=""/g) ?? []).length).toBeGreaterThanOrEqual(
      4,
    )
  })

  it('renders live navigation entry points only when onNavigate is provided', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const withNavigate = renderToStaticMarkup(
      <HomeTodayContent
        snapshot={snapshot}
        saveState={null}
        onNavigate={() => undefined}
      />,
    )
    const withoutNavigate = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    for (const action of [
      'Review Offers',
      'View Free Agents',
      'Adjust Rotation',
      'View Finances',
      'View Full Schedule',
    ]) {
      expect(withNavigate).toContain(action)
      expect(withoutNavigate).not.toContain(action)
    }
  })

  it('renders the dev preview entry only when a handler is provided', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const withHandler = renderToStaticMarkup(
      <HomeTodayContent
        snapshot={snapshot}
        saveState={null}
        onOpenGameResultPreview={() => undefined}
      />,
    )
    const withoutHandler = renderToStaticMarkup(
      <HomeTodayContent snapshot={snapshot} saveState={null} />,
    )

    expect(withHandler).toContain('Preview the post-game screen')
    expect(withoutHandler).not.toContain('Preview the post-game screen')
  })

  it('shows honest empty schedule states past the end of the season', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const afterSchedule = {
      ...snapshot,
      season: {
        ...snapshot.season,
        currentDate: parseLocalDate('2027-12-31'),
      },
    }
    const markup = renderToStaticMarkup(
      <HomeTodayContent snapshot={afterSchedule} saveState={null} />,
    )

    expect(markup).toContain('No upcoming event is currently scheduled.')
    expect(markup).toContain(
      'No additional future scheduled games are available.',
    )
  })
})
