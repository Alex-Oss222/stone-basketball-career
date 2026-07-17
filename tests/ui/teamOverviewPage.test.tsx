import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { formatTeamName } from '../../src/domain/league'
import type { LeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import type { Team } from '../../src/domain/league'
import { TeamOverviewContent } from '../../src/ui/teamOverviewPage'
import { createLeagueSnapshotFixture } from '../persistence/leagueSnapshot.fixture'

function managedTeam(snapshot: LeagueSnapshot): Team {
  const team = snapshot.league.teams.find(
    (candidate) => candidate.id === snapshot.managedTeamId,
  )
  if (team === undefined) {
    throw new Error('fixture must have a managed team')
  }
  return team
}

describe('Team Overview rendering', () => {
  it('describes the empty state with no team', () => {
    const markup = renderToStaticMarkup(
      <TeamOverviewContent snapshot={null} team={null} />,
    )
    expect(markup).toContain('No team selected')
  })

  it('renders the Evergreens panel set with the two swapped panels', () => {
    const snapshot = createLeagueSnapshotFixture()
    const markup = renderToStaticMarkup(
      <TeamOverviewContent snapshot={snapshot} team={managedTeam(snapshot)} />,
    )

    for (const panel of [
      'Needs Attention',
      'Starting Five / Rotation',
      'Team Strengths', // '&' is HTML-escaped in static markup
      'Health Summary',
      'Development Watch',
      'Roster Breakdown', // swapped into the Recent Form slot
      'Team Metrics', // swapped into the Cap & Asset slot
      'Upcoming Games',
      'Recent Transactions / News',
    ]) {
      expect(markup).toContain(panel)
    }

    // The two removed panels must not appear.
    expect(markup).not.toContain('Recent Form')
    expect(markup).not.toContain('Asset')
  })

  it('shows real identity, rating, and roster-composition data', () => {
    const snapshot = createLeagueSnapshotFixture()
    const team = managedTeam(snapshot)
    const markup = renderToStaticMarkup(
      <TeamOverviewContent snapshot={snapshot} team={team} />,
    )

    expect(markup).toContain(formatTeamName(team))
    expect(markup).toContain('Team Rating')
    // Roster-breakdown donut labels its real total.
    expect(markup).toContain('Players')
  })

  it('renders live navigation entry points only when onNavigate is provided', () => {
    const snapshot = createLeagueSnapshotFixture()
    const team = managedTeam(snapshot)
    const withNavigate = renderToStaticMarkup(
      <TeamOverviewContent
        snapshot={snapshot}
        team={team}
        onNavigate={() => undefined}
      />,
    )
    const withoutNavigate = renderToStaticMarkup(
      <TeamOverviewContent snapshot={snapshot} team={team} />,
    )

    for (const action of [
      'Review Rotation',
      'View Development',
      'View Health',
      'View Full Schedule',
    ]) {
      expect(withNavigate).toContain(action)
      expect(withoutNavigate).not.toContain(action)
    }
  })

  it('fabricates no record, ranking, score, or streak anywhere', () => {
    const snapshot = createLeagueSnapshotFixture()
    const markup = renderToStaticMarkup(
      <TeamOverviewContent
        snapshot={snapshot}
        team={managedTeam(snapshot)}
        onNavigate={() => undefined}
      />,
    )

    // Every results-era slot is honestly deferred.
    expect(markup).toContain('Coming later')

    // Strip attributes that legitimately contain digits/dashes (ISO dates,
    // inline chart styles) and check only visible content.
    const visibleMarkup = markup
      .replace(/datetime="[^"]*"/gi, '')
      .replace(/style="[^"]*"/gi, '')
    // No score/record-like "NN-NN" value.
    expect(visibleMarkup).not.toMatch(/\b\d{2,3}\s*[–-]\s*\d{2,3}\b/)
    // No fabricated streak-like "W3" / "L5" value.
    expect(visibleMarkup).not.toMatch(/\b[WL]\d+\b/)
  })
})
