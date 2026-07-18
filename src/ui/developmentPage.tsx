import { useState } from 'react'
import type { League, Team } from '../domain/league'
import { formatTeamName } from '../domain/league'
import { formatPlayerName, getTeamRoster } from './leagueViewModel'

export interface CoachingDevelopmentContentProps {
  readonly league: League | null
  readonly team: Team | null
}

type DevelopmentTab = 'plans' | 'progress'

/**
 * Coaching & Development — focused, measurable player plans, built UI-first
 * from Alex's reference (2026-07-17). The roster is real; every plan focus,
 * coach assignment, intensity, progress figure, and blocker is an honest
 * Coming-later slot until the development system exists.
 * DEFERRED(later): the plans table and checkpoints fill from the development
 * system.
 */
export function CoachingDevelopmentContent({
  league,
  team,
}: CoachingDevelopmentContentProps) {
  const [activeTab, setActiveTab] = useState<DevelopmentTab>('plans')

  if (league === null || team === null) {
    return (
      <section
        className="development-content empty-state"
        aria-label="No team"
      >
        <h2>No team selected</h2>
        <p>
          Create a league and choose a team to open Coaching &amp; Development.
        </p>
      </section>
    )
  }

  const roster = getTeamRoster(league, team.id)

  return (
    <div className="development-content">
      <div className="page-toolbar">
        <p className="section-intro">
          Focused, measurable player plans for {formatTeamName(team)} — without
          turning every week into administrative busywork.
        </p>
        <div className="page-toolbar-actions">
          <DisabledToolbarButton
            label="Assign staff"
            requirement="Coaching staff arrives with the staff system."
          />
          <DisabledToolbarButton
            label="Apply plan"
            requirement="Player plans arrive with the development system."
          />
        </div>
      </div>

      <nav className="player-page-tabs" aria-label="Development sections">
        <DisabledTab
          label="Staff & Philosophy"
          requirement="Coaching staff arrives with the staff system."
        />
        <DisabledTab
          label="Weekly Plan"
          requirement="Weekly planning arrives with the development system."
        />
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'plans'}
          onClick={() => setActiveTab('plans')}
        >
          Player Plans
        </button>
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'progress'}
          onClick={() => setActiveTab('progress')}
        >
          Progress
        </button>
        <DisabledTab
          label="Mentorship"
          requirement="Mentorship arrives with the personality systems."
        />
      </nav>

      {activeTab === 'plans' ? (
        <section
          className="player-page-card"
          aria-label="Individual player plans"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Individual plans</p>
              <h3>One primary goal, one supporting goal, measurable evidence</h3>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>
          <div
            className="table-scroll"
            role="region"
            aria-label="Player plans table"
            tabIndex={0}
          >
            <table className="roster-table development-plans-table">
              <caption className="visually-hidden">
                Player development plans for {formatTeamName(team)}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">Primary Focus</th>
                  <th scope="col">Assigned Coach</th>
                  <th scope="col">Intensity</th>
                  <th scope="col">Progress</th>
                  <th scope="col">Review</th>
                  <th scope="col">Blocker</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((player) => (
                  <tr key={player.id}>
                    <th scope="row">
                      <span className="player-name">
                        {formatPlayerName(player)}
                      </span>
                      <span className="jersey-number">
                        #{player.jerseyNumber} · {player.primaryPosition} · Age{' '}
                        {player.age}
                      </span>
                    </th>
                    {/* DEFERRED(later): all plan fields need the development system. */}
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="coming-later-requirement">
            Plan focuses, coach assignments, intensity, progress, reviews, and
            blockers arrive with the development system.
          </p>
        </section>
      ) : (
        <section className="player-page-card" aria-label="Plan progress">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Measurable outcomes</p>
              <h3>Plan checkpoints</h3>
            </div>
          </div>
          {/* DEFERRED(later): checkpoints fill from real development plans. */}
          <dl className="pqv-field-rows">
            {[
              'Plans on track',
              'Plans behind',
              'Plans blocked',
              'Reviews due this week',
              'Coach capacity',
            ].map((label) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>—</dd>
              </div>
            ))}
          </dl>
          <p className="coming-later-requirement">
            Checkpoint evidence and trends fill from real development plans and
            real game exposure.
          </p>
        </section>
      )}
    </div>
  )
}

function DisabledTab({
  label,
  requirement,
}: {
  readonly label: string
  readonly requirement: string
}) {
  return (
    <button type="button" className="player-tab" disabled title={requirement}>
      {label} <span className="coming-later-marker">Coming later</span>
    </button>
  )
}

function DisabledToolbarButton({
  label,
  requirement,
}: {
  readonly label: string
  readonly requirement: string
}) {
  return (
    <button
      type="button"
      className="secondary-button pqv-disabled-action"
      disabled
      title={requirement}
    >
      {label} <span className="coming-later-marker">Coming later</span>
    </button>
  )
}
