import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { CoachingDevelopmentContent } from '../../src/ui/developmentPage'
import { formatPlayerName, getTeamRoster } from '../../src/ui/leagueViewModel'
import { MedicalDepartmentContent } from '../../src/ui/medicalPage'
import { RotationGameplanContent } from '../../src/ui/rotationGameplanPage'

const league = generateLeague('team-operations-fixture')
const team = league.teams[0]
const roster = getTeamRoster(league, team.id)

function expectHonest(markup: string): void {
  expect(markup).toContain('Coming later')
  const visible = markup
    .replace(/datetime="[^"]*"/gi, '')
    .replace(/style="[^"]*"/gi, '')
  expect(visible).not.toMatch(/\b\d{2,3}\s*[–-]\s*\d{2,3}\b/)
  expect(visible).not.toMatch(/\b[WL]\d+\b/)
  expect(visible).not.toMatch(/\$\d/)
}

describe('Rotation & Gameplan', () => {
  const noop = (): void => {}

  it('renders a functional §8 editor with real minutes and a 240 target', () => {
    const markup = renderToStaticMarkup(
      <RotationGameplanContent
        league={league}
        team={team}
        savedPlan={null}
        busy={false}
        onSaveRotationPlan={noop}
      />,
    )

    expect(markup).toContain('/ 240')
    expect(markup).toContain(formatPlayerName(roster[0]))
    for (const label of [
      'Rotation Board',
      '48-Minute Map',
      '6-Minute Splits',
      'Auto Rotation',
      'Reset',
      'Save Rotation',
      'Target Minutes',
      'OVR',
      'Starter',
      'Allowed Positions',
    ]) {
      expect(markup).toContain(label)
    }
  })

  it('shows the empty state without a team', () => {
    const markup = renderToStaticMarkup(
      <RotationGameplanContent
        league={null}
        team={null}
        savedPlan={null}
        busy={false}
        onSaveRotationPlan={noop}
      />,
    )
    expect(markup).toContain('No team selected')
  })
})

describe('Medical Department', () => {
  it('renders the availability board with plain-word honest slots', () => {
    const markup = renderToStaticMarkup(
      <MedicalDepartmentContent league={league} team={team} />,
    )

    expect(markup).toContain(formatPlayerName(roster[0]))
    for (const label of [
      'Participation and availability board',
      'Status',
      'Staff Recommendation',
      'Your Decision',
      'Workload',
      'Return to Play',
    ]) {
      expect(markup).toContain(label)
    }
    // Health is plain words — no invented risk scores or readiness gauges.
    expect(markup).not.toMatch(/risk \d/i)
    expectHonest(markup)
  })

  it('shows the empty state without a team', () => {
    const markup = renderToStaticMarkup(
      <MedicalDepartmentContent league={null} team={null} />,
    )
    expect(markup).toContain('No team selected')
  })
})

describe('Coaching & Development', () => {
  it('renders the player plans table with honest slots', () => {
    const markup = renderToStaticMarkup(
      <CoachingDevelopmentContent league={league} team={team} />,
    )

    expect(markup).toContain(formatPlayerName(roster[0]))
    for (const label of [
      'Player Plans',
      'Primary Focus',
      'Assigned Coach',
      'Intensity',
      'Progress',
      'Blocker',
      'Mentorship',
    ]) {
      expect(markup).toContain(label)
    }
    expectHonest(markup)
  })

  it('shows the empty state without a team', () => {
    const markup = renderToStaticMarkup(
      <CoachingDevelopmentContent league={null} team={null} />,
    )
    expect(markup).toContain('No team selected')
  })
})
