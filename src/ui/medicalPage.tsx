import { useState } from 'react'
import type { League, Team } from '../domain/league'
import { formatTeamName } from '../domain/league'
import { formatPlayerName, getTeamRoster } from './leagueViewModel'

export interface MedicalDepartmentContentProps {
  readonly league: League | null
  readonly team: Team | null
}

type MedicalTab = 'availability' | 'return-to-play'

/**
 * Medical Department — availability, workload, rehab, and return decisions in
 * one workspace, built UI-first from Alex's reference (2026-07-17). The roster
 * is real; every status, reason, practice level, recommendation, and decision
 * is an honest Coming-later slot until the medical system exists. Health is
 * deliberately presented as plain words (status + reason + decision) — no
 * invented risk scores or readiness gauges.
 * DEFERRED(later): the whole board fills from the medical system.
 */
export function MedicalDepartmentContent({
  league,
  team,
}: MedicalDepartmentContentProps) {
  const [activeTab, setActiveTab] = useState<MedicalTab>('availability')

  if (league === null || team === null) {
    return (
      <section className="medical-content empty-state" aria-label="No team">
        <h2>No team selected</h2>
        <p>Create a league and choose a team to open the Medical Department.</p>
      </section>
    )
  }

  const roster = getTeamRoster(league, team.id)

  return (
    <div className="medical-content">
      <div className="page-toolbar">
        <p className="section-intro">
          Availability, risk, workload, rehab, and return decisions for{' '}
          {formatTeamName(team)}.
        </p>
        <div className="page-toolbar-actions">
          <DisabledToolbarButton
            label="Publish availability report"
            requirement="Availability reports arrive with the medical system."
          />
          <DisabledToolbarButton
            label="Apply decisions"
            requirement="Participation decisions arrive with the medical system."
          />
        </div>
      </div>

      <nav className="player-page-tabs" aria-label="Medical sections">
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'availability'}
          onClick={() => setActiveTab('availability')}
        >
          Availability
        </button>
        <DisabledTab
          label="Workload"
          requirement="Cumulative load tracking needs the medical system and real minutes."
        />
        <DisabledTab
          label="Injuries & Rehab"
          requirement="Injury cases need the medical system."
        />
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'return-to-play'}
          onClick={() => setActiveTab('return-to-play')}
        >
          Return to Play
        </button>
      </nav>

      {activeTab === 'availability' ? (
        <section
          className="player-page-card"
          aria-label="Participation and availability board"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Next game</p>
              <h3>Participation and availability board</h3>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>
          <div
            className="table-scroll"
            role="region"
            aria-label="Availability board table"
            tabIndex={0}
          >
            <table className="roster-table medical-board-table">
              <caption className="visually-hidden">
                Availability board for {formatTeamName(team)}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">Status</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Practice</th>
                  <th scope="col">Staff Recommendation</th>
                  <th scope="col">Your Decision</th>
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
                        #{player.jerseyNumber} · {player.primaryPosition}
                      </span>
                    </th>
                    {/* DEFERRED(later): all availability fields need the medical system. */}
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
            Statuses, reasons, practice levels, staff recommendations, and your
            decisions arrive with the medical system — presented as plain words,
            never as invented risk scores.
          </p>
        </section>
      ) : (
        <section
          className="player-page-card"
          aria-label="Return to play continuum"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Return continuum</p>
              <h3>
                Return to participation → return to sport → return to
                performance
              </h3>
            </div>
          </div>
          {/* DEFERRED(later): stages and checkpoints fill from real injury cases. */}
          <div className="return-stage-grid">
            <ReturnStageCard
              stage="Stage 1"
              title="Return to participation"
              detail="Modified individual and team activities while restrictions remain."
              items={[
                'Symptom-free daily activity',
                'Strength symmetry',
                'Submax court work',
                'High-speed running',
              ]}
            />
            <ReturnStageCard
              stage="Stage 2"
              title="Return to sport"
              detail="Full practice exposure with controlled game-like demand."
              items={[
                'Full-speed change of direction',
                'Live five-on-five practice',
                'Back-to-back practice tolerance',
                'Medical clearance',
              ]}
            />
            <ReturnStageCard
              stage="Stage 3"
              title="Return to performance"
              detail="Available for competition and progressing toward pre-injury output."
              items={[
                'Game minutes ramp completed',
                'Performance baseline restored',
                'No symptom response a day later',
                'Case closure',
              ]}
            />
          </div>
          <p className="coming-later-requirement">
            A range, evidence, and repeated sign-offs replace a misleading
            single return date. Stages fill from real injury cases with the
            medical system.
          </p>
        </section>
      )}
    </div>
  )
}

function ReturnStageCard({
  stage,
  title,
  detail,
  items,
}: {
  readonly stage: string
  readonly title: string
  readonly detail: string
  readonly items: readonly string[]
}) {
  return (
    <article className="return-stage-card">
      <p className="panel-kicker">{stage}</p>
      <h4>{title}</h4>
      <p className="return-stage-detail">{detail}</p>
      <dl className="pqv-field-rows">
        {items.map((item) => (
          <div key={item}>
            <dt>{item}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
    </article>
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
