import { useMemo, useRef, useState } from 'react'
import type { DragEvent } from 'react'
import type { PlayerId } from '../domain/ids'
import type { Player, Position, Team } from '../domain/league'
import { POSITIONS, formatTeamName } from '../domain/league'
import { deriveOverall } from '../domain/playerDerivations'
import { deriveTacticalTag } from '../domain/playerArchetype'
import {
  deriveDepthAlerts,
  deriveDepthChart,
  derivePositionCoverage,
  depthTierLabel,
  reorderDepth,
} from '../app/depthRolesViewModel'
import type { DepthChart } from '../app/depthRolesViewModel'
import { formatPlayerName } from './leagueViewModel'

const POSITION_LABELS: Record<Position, string> = {
  PG: 'Point Guard',
  SG: 'Shooting Guard',
  SF: 'Small Forward',
  PF: 'Power Forward',
  C: 'Center',
}

export interface DepthRolesContentProps {
  readonly team: Team
  readonly roster: readonly Player[]
}

/**
 * §8 Depth & Roles — the per-position depth chart (a tab inside Rotation &
 * Gameplan). Drag a player to reorder a position's depth; click the position
 * chips to change where a player is eligible (natural positions are gold, added
 * ones light gold). Display-only v1: not persisted, never read by the sim; the
 * profile "type", exact role fit, chemistry, and expected minutes arrive with
 * their systems.
 */
export function DepthRolesContent({ team, roster }: DepthRolesContentProps) {
  const byId = useMemo(
    () => new Map<PlayerId, Player>(roster.map((p) => [p.id, p])),
    [roster],
  )
  const overallById = useMemo(
    () => new Map<PlayerId, number>(roster.map((p) => [p.id, deriveOverall(p)])),
    [roster],
  )
  const tagById = useMemo(
    () =>
      new Map<PlayerId, string>(
        roster.map((p) => [p.id, deriveTacticalTag(p.ratings, p.measurements)]),
      ),
    [roster],
  )

  const initialChart = useMemo(() => deriveDepthChart(roster), [roster])
  const [chart, setChart] = useState<DepthChart>(initialChart)
  const [selectedId, setSelectedId] = useState<PlayerId | null>(
    chart.PG[0] ?? roster[0]?.id ?? null,
  )
  const dragged = useRef<{ playerId: PlayerId; position: Position } | null>(null)

  const coverage = derivePositionCoverage(chart)
  const alerts = deriveDepthAlerts(chart)
  const selected = selectedId === null ? null : (byId.get(selectedId) ?? null)

  const roleBalance = useMemo(() => {
    const counts = new Map<string, number>()
    for (const player of roster) {
      const tag = tagById.get(player.id) ?? 'Unknown'
      counts.set(tag, (counts.get(tag) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [roster, tagById])

  const handleDrop = (position: Position, index: number): void => {
    const source = dragged.current
    dragged.current = null
    if (source === null || source.position !== position) {
      return
    }
    setChart((current) =>
      reorderDepth(current, position, source.playerId, index),
    )
  }

  const toggleEligibility = (playerId: PlayerId, position: Position): void => {
    setChart((current) => {
      const list = current[position]
      if (list.includes(playerId)) {
        return { ...current, [position]: list.filter((id) => id !== playerId) }
      }
      return { ...current, [position]: [...list, playerId] }
    })
  }

  const autoFill = (): void => {
    setChart(deriveDepthChart(roster))
  }

  return (
    <div className="depth-roles">
      <div className="page-toolbar">
        <p className="section-intro">
          Set the depth at each position for {formatTeamName(team)} — drag to
          reorder, click a position to change where a player is eligible.
        </p>
        <div className="page-toolbar-actions">
          <button type="button" className="secondary-button" onClick={autoFill}>
            Auto Fill Depth
          </button>
          <button
            type="button"
            className="secondary-button pqv-disabled-action"
            disabled
            title="Saving a depth plan arrives when it is persisted (§8 follow-up)."
          >
            Save Depth Plan{' '}
            <span className="coming-later-marker">Coming later</span>
          </button>
        </div>
      </div>

      <dl className="player-stat-cards">
        <div className="player-stat-card player-stat-card-real">
          <dt>Position Coverage</dt>
          <dd>
            <span className="player-stat-card-value">
              {coverage.strong} / {POSITIONS.length}
            </span>
            <span className="depth-coverage-detail">
              {coverage.strong} strong · {coverage.average} avg · {coverage.weak}{' '}
              weak
            </span>
          </dd>
        </div>
        <DeferredDepthCard label="Team Chemistry" note="the morale system" />
        <DeferredDepthCard label="Roster Balance" note="the analytics system" />
        <DeferredDepthCard label="Development Focus" note="the development system" />
      </dl>

      <div className="depth-roles-layout">
        <section className="player-page-card depth-grid" aria-label="Depth chart">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Depth chart</p>
              <h3>1st · 2nd · 3rd choice by position</h3>
            </div>
          </div>
          <div className="depth-grid-rows">
            {POSITIONS.map((position) => (
              <div key={position} className="depth-grid-row">
                <div className="depth-grid-position">
                  <span className="depth-grid-position-code">{position}</span>
                  <span className="depth-grid-position-name">
                    {POSITION_LABELS[position]}
                  </span>
                </div>
                <div
                  className="depth-grid-slots"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => handleDrop(position, chart[position].length)}
                >
                  {chart[position].length === 0 && (
                    <p className="depth-grid-empty">No eligible player</p>
                  )}
                  {chart[position].map((playerId, index) => {
                    const player = byId.get(playerId)
                    if (player === undefined) {
                      return null
                    }
                    return (
                      <DepthCard
                        key={playerId}
                        player={player}
                        rank={index}
                        overall={overallById.get(playerId) ?? 0}
                        tag={tagById.get(playerId) ?? ''}
                        selected={playerId === selectedId}
                        onSelect={() => setSelectedId(playerId)}
                        onDragStart={() => {
                          dragged.current = { playerId, position }
                        }}
                        onDrop={() => handleDrop(position, index)}
                      />
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
          <p className="coming-later-requirement">
            Drag a player to change depth order. Depth is not saved yet and never
            reaches the sim — persistence and lineups follow.
          </p>
        </section>

        <DepthPlayerPanel
          player={selected}
          overall={selected === null ? 0 : (overallById.get(selected.id) ?? 0)}
          tag={selected === null ? '' : (tagById.get(selected.id) ?? '')}
          chart={chart}
          onToggleEligibility={toggleEligibility}
        />
      </div>

      <div className="depth-roles-summary">
        <section className="player-page-card" aria-label="Depth alerts">
          <p className="panel-kicker">Depth alerts</p>
          {alerts.length === 0 ? (
            <p className="depth-alert-ok">Every position has usable depth.</p>
          ) : (
            <ul className="depth-alert-list">
              {alerts.map((alert) => (
                <li key={alert}>{alert}</li>
              ))}
            </ul>
          )}
        </section>
        <section className="player-page-card" aria-label="Role balance">
          <p className="panel-kicker">Role balance</p>
          <ul className="depth-role-balance">
            {roleBalance.map(([tag, count]) => (
              <li key={tag}>
                <span>{tag}</span>
                <span className="depth-role-count">{count}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}

function DepthCard({
  player,
  rank,
  overall,
  tag,
  selected,
  onSelect,
  onDragStart,
  onDrop,
}: {
  readonly player: Player
  readonly rank: number
  readonly overall: number
  readonly tag: string
  readonly selected: boolean
  readonly onSelect: () => void
  readonly onDragStart: () => void
  readonly onDrop: () => void
}) {
  return (
    <div
      className={selected ? 'depth-card depth-card-selected' : 'depth-card'}
      draggable
      onClick={onSelect}
      onDragStart={(event: DragEvent) => {
        event.dataTransfer.effectAllowed = 'move'
        onDragStart()
      }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault()
        event.stopPropagation()
        onDrop()
      }}
    >
      <div className="depth-card-head">
        <span className="depth-card-rank">{rank + 1}</span>
        <span className="depth-card-ovr">{overall}</span>
      </div>
      <span className="depth-card-name">{formatPlayerName(player)}</span>
      <span className="depth-card-tier">{depthTierLabel(rank)}</span>
      {tag !== '' && <span className="depth-card-tag">{tag}</span>}
    </div>
  )
}

function DepthPlayerPanel({
  player,
  overall,
  tag,
  chart,
  onToggleEligibility,
}: {
  readonly player: Player | null
  readonly overall: number
  readonly tag: string
  readonly chart: DepthChart
  readonly onToggleEligibility: (playerId: PlayerId, position: Position) => void
}) {
  if (player === null) {
    return (
      <section className="player-page-card depth-player-panel" aria-label="Player">
        <p className="depth-panel-empty">Select a player to see their roles.</p>
      </section>
    )
  }

  return (
    <section className="player-page-card depth-player-panel" aria-label="Player">
      <div className="depth-panel-identity">
        <h3>{formatPlayerName(player)}</h3>
        <p className="pqv-meta">
          #{player.jerseyNumber} · {player.primaryPosition}
          {player.secondaryPosition === null
            ? ''
            : ` / ${player.secondaryPosition}`}{' '}
          · OVR {overall}
        </p>
        <p className="player-hero-type">
          Player Type <span className="coming-later-marker">Coming later</span>
        </p>
      </div>

      <div className="depth-panel-section">
        <p className="panel-kicker">Position eligibility</p>
        <div className="position-chip-row depth-eligibility">
          {POSITIONS.map((position) => {
            const eligible = chart[position].includes(player.id)
            const natural = player.primaryPosition === position
            const className = !eligible
              ? 'position-chip depth-chip-off'
              : natural
                ? 'position-chip depth-chip-natural'
                : 'position-chip depth-chip-added'
            return (
              <button
                key={position}
                type="button"
                className={className}
                aria-pressed={eligible}
                onClick={() => onToggleEligibility(player.id, position)}
              >
                {position}
              </button>
            )
          })}
        </div>
        <p className="depth-panel-hint">
          Gold = natural position · light gold = added. Click to change where he
          can play.
        </p>
      </div>

      <div className="depth-panel-section">
        <p className="panel-kicker">Roles</p>
        <p className="depth-panel-role">
          <span className="depth-role-label">Featured</span>
          <span className="rotation-tag-badge">{tag}</span>
        </p>
        <p className="depth-panel-hint">
          {/* DEFERRED(later): offensive/defensive roles + role fit come with the tactical-tag redesign. */}
          Separate offensive and defensive roles (with role fit) arrive with the
          tactical-role system.
        </p>
      </div>
    </section>
  )
}

function DeferredDepthCard({
  label,
  note,
}: {
  readonly label: string
  readonly note: string
}) {
  return (
    <div className="player-stat-card" title={`Arrives with ${note}.`}>
      <dt>
        {label} <span className="coming-later-marker">Coming later</span>
      </dt>
      <dd>—</dd>
    </div>
  )
}
