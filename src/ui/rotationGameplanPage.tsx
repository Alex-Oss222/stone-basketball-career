import { useState } from 'react'
import type { League, Team } from '../domain/league'
import { POSITIONS, formatTeamName } from '../domain/league'
import {
  MILESTONE_1_LEAGUE_RULES,
  deriveRegulationTeamSeconds,
} from '../domain/leagueRules'
import { formatPlayerName, getTeamRoster } from './leagueViewModel'

export interface RotationGameplanContentProps {
  readonly league: League | null
  readonly team: Team | null
}

type RotationTab = 'board' | 'map'

const QUARTER_BLOCKS = [
  'Q1 · 12–6',
  'Q1 · 6–0',
  'Q2 · 12–6',
  'Q2 · 6–0',
  'Q3 · 12–6',
  'Q3 · 6–0',
  'Q4 · 12–6',
  'Q4 · 6–0',
] as const

/**
 * Rotation & Gameplan — the §8 rotation editor's screen, built UI-first from
 * Alex's reference (2026-07-17). The roster, allowed positions, and the
 * derived 240-minute target are real today; every minute value, role, starter
 * toggle, and map assignment is an honest Coming-later slot until
 * `RotationPlanV1` and its editor land.
 * DEFERRED(§8): the board and 48-minute map become the functional editor —
 * a visual mockup does not clear this tag.
 */
export function RotationGameplanContent({
  league,
  team,
}: RotationGameplanContentProps) {
  const [activeTab, setActiveTab] = useState<RotationTab>('board')

  if (league === null || team === null) {
    return (
      <section
        className="rotation-gameplan-content empty-state"
        aria-label="No team"
      >
        <h2>No team selected</h2>
        <p>Create a league and choose a team to open Rotation &amp; Gameplan.</p>
      </section>
    )
  }

  const roster = getTeamRoster(league, team.id)
  const regulationMinutes =
    deriveRegulationTeamSeconds(MILESTONE_1_LEAGUE_RULES) / 60

  return (
    <div className="rotation-gameplan-content">
      <div className="page-toolbar">
        <p className="section-intro">
          Set the normal plan, the exceptions, and how much the staff may
          improvise — for {formatTeamName(team)}.
        </p>
        <div className="page-toolbar-actions">
          <DisabledToolbarButton
            label="Auto-balance"
            requirement="Deterministic plan generation arrives with §8."
          />
          <DisabledToolbarButton
            label="Apply rotation"
            requirement="Saving a validated plan arrives with §8."
          />
        </div>
      </div>

      <dl className="player-stat-cards">
        <div className="player-stat-card player-stat-card-real">
          <dt>Target Minutes</dt>
          <dd>
            <span className="player-stat-card-value">
              — / {regulationMinutes}
            </span>
          </dd>
        </div>
        <DeferredKpiCard
          label="Active Rotation"
          requirement="The rotation size comes from the saved plan (§8)."
        />
        <DeferredKpiCard
          label="Starters"
          requirement="Starters come from the saved plan (§8)."
        />
        <DeferredKpiCard
          label="Medical Conflicts"
          requirement="Conflicts need the medical system."
        />
        <DeferredKpiCard
          label="Coach Freedom"
          requirement="Coach freedom comes from the coach profile (§8A)."
        />
      </dl>

      <nav className="player-page-tabs" aria-label="Rotation sections">
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'board'}
          onClick={() => setActiveTab('board')}
        >
          Rotation Board
        </button>
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'map'}
          onClick={() => setActiveTab('map')}
        >
          48-Minute Map
        </button>
        <DisabledTab
          label="Lineup Lab"
          requirement="Lineup projections need the simulation."
        />
        <DisabledTab
          label="Situations"
          requirement="Situational lineups arrive after the base editor (§8)."
        />
        <DisabledTab
          label="Gameplan"
          requirement="Gameplan settings arrive with the coaching systems."
        />
      </nav>

      {activeTab === 'board' ? (
        <section
          className="player-page-card rotation-board"
          aria-label="Normal rotation"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Normal rotation</p>
              <h3>Minutes, roles, positions, starters, and closing status</h3>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>
          <div
            className="table-scroll"
            role="region"
            aria-label="Rotation board table"
            tabIndex={0}
          >
            <table className="roster-table rotation-board-table">
              <caption className="visually-hidden">
                Rotation board for {formatTeamName(team)}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">Allowed Positions</th>
                  <th scope="col">Minutes</th>
                  <th scope="col">Role</th>
                  <th scope="col">Medical</th>
                  <th scope="col">Start</th>
                  <th scope="col">Close</th>
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
                        #{player.jerseyNumber}
                      </span>
                    </th>
                    <td>
                      <span className="position-chip-row">
                        {POSITIONS.map((position) => (
                          <span
                            key={position}
                            className={
                              position === player.primaryPosition ||
                              position === player.secondaryPosition
                                ? 'position-chip position-chip-eligible'
                                : 'position-chip'
                            }
                          >
                            {position}
                          </span>
                        ))}
                      </span>
                    </td>
                    {/* DEFERRED(§8): minutes, role, and start/close come from the plan. */}
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    {/* DEFERRED(later): medical clearance needs the medical system. */}
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                    <td className="deferred-cell">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="coming-later-requirement">
            Minutes, roles, starter and closing toggles become editable with the
            §8 rotation plan; the plan must total exactly {regulationMinutes}{' '}
            minutes.
          </p>
        </section>
      ) : (
        <section
          className="player-page-card rotation-map"
          aria-label="48-minute map"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Game sequence</p>
              <h3>Eight six-minute blocks make the substitution logic visible</h3>
            </div>
          </div>
          {/* DEFERRED(§8): block assignments compile from the saved rotation plan. */}
          <div className="rotation-map-grid">
            {QUARTER_BLOCKS.map((block) => (
              <div key={block} className="rotation-map-block">
                <p className="rotation-map-block-title">{block}</p>
                <dl>
                  {POSITIONS.map((position) => (
                    <div key={position}>
                      <dt>{position}</dt>
                      <dd>—</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
          <p className="coming-later-requirement">
            Block assignments fill from the saved rotation plan (§8); live
            substitutions belong to the simulation (§9/§14).
          </p>
        </section>
      )}
    </div>
  )
}

function DeferredKpiCard({
  label,
  requirement,
}: {
  readonly label: string
  readonly requirement: string
}) {
  return (
    <div className="player-stat-card" title={requirement}>
      <dt>
        {label} <span className="coming-later-marker">Coming later</span>
      </dt>
      <dd>—</dd>
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
