import { useMemo, useState } from 'react'
import type { League, Player, Team } from '../domain/league'
import { POSITIONS, formatTeamName } from '../domain/league'
import type { PlayerId } from '../domain/ids'
import { MILESTONE_1_LEAGUE_RULES } from '../domain/leagueRules'
import { deriveOverall } from '../domain/playerDerivations'
import { deriveTacticalTag } from '../domain/playerArchetype'
import type { TacticalTag } from '../domain/playerArchetype'
import {
  MAX_PLAYER_REGULATION_MINUTES,
  STARTERS_REQUIRED,
  generateRotationPlan,
  regulationMinutes,
  validateRotationPlan,
} from '../domain/rotationPlan'
import type { RotationPlanV1 } from '../domain/rotationPlan'
import {
  deriveRotationTier,
  displayOrder,
  draftFromPlan,
  draftsEqual,
  minutesByPeriod,
  planFromDraft,
  reorder,
  resolveRotationPlan,
  rotationPlanSignature,
  rotationPlayerCount,
  totalDraftMinutes,
} from '../app/rotationGameplanViewModel'
import type { RotationDraft, RotationTier } from '../app/rotationGameplanViewModel'
import { DepthRolesContent } from './depthRolesPage'
import { formatPlayerName, getTeamRoster } from './leagueViewModel'

const RULES = MILESTONE_1_LEAGUE_RULES
const PERIOD_COUNT = RULES.regulation.periodCount

export interface RotationGameplanContentProps {
  readonly league: League | null
  readonly team: Team | null
  readonly savedPlan: RotationPlanV1 | null
  readonly busy: boolean
  readonly onSaveRotationPlan: (plan: RotationPlanV1) => void
}

/**
 * Rotation & Gameplan — the §8 rotation editor. The board is a functional depth
 * chart over `RotationPlanV1`: the top five players are the starters (set by
 * moving players up, not a toggle), minutes are edited inline, the plan
 * validates live (blocking errors + non-blocking warnings), and Save persists a
 * protected `user-edited` plan. Each player shows a derived rotation tier and a
 * display-only tactical tag (never read by the sim). The 48-Minute Map and
 * 6-Minute Splits tabs project the planned minutes; live per-block lineups are
 * the game engine's job (§9).
 */
export function RotationGameplanContent({
  league,
  team,
  savedPlan,
  busy,
  onSaveRotationPlan,
}: RotationGameplanContentProps) {
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

  return (
    <RotationEditor
      key={`${team.id}:${rotationPlanSignature(savedPlan)}`}
      league={league}
      team={team}
      savedPlan={savedPlan}
      busy={busy}
      onSaveRotationPlan={onSaveRotationPlan}
    />
  )
}

type RotationTab = 'board' | 'depth' | 'quarter' | 'splits'

interface RotationEditorProps {
  readonly league: League
  readonly team: Team
  readonly savedPlan: RotationPlanV1 | null
  readonly busy: boolean
  readonly onSaveRotationPlan: (plan: RotationPlanV1) => void
}

function RotationEditor({
  league,
  team,
  savedPlan,
  busy,
  onSaveRotationPlan,
}: RotationEditorProps) {
  const roster = useMemo(() => getTeamRoster(league, team.id), [league, team.id])
  const baseline = useMemo(
    () => resolveRotationPlan(roster, team.id, savedPlan, RULES),
    [roster, team.id, savedPlan],
  )
  const baselineDraft = useMemo(
    () => draftFromPlan(baseline, roster),
    [baseline, roster],
  )

  const [draft, setDraft] = useState<RotationDraft>(() => baselineDraft)
  const [activeTab, setActiveTab] = useState<RotationTab>('board')

  const tagsByPlayer = useMemo(
    () =>
      new Map<PlayerId, TacticalTag>(
        roster.map((player) => [
          player.id,
          deriveTacticalTag(player.ratings, player.measurements),
        ]),
      ),
    [roster],
  )
  const overallByPlayer = useMemo(
    () => new Map<PlayerId, number>(roster.map((p) => [p.id, deriveOverall(p)])),
    [roster],
  )

  const regulation = regulationMinutes(RULES)
  const totalMinutes = totalDraftMinutes(draft, roster)
  const activeRotation = rotationPlayerCount(draft, roster)
  const currentPlan = planFromDraft(draft, team.id, roster, 'user-edited')
  const validation = validateRotationPlan(currentPlan, roster, RULES)
  const isDirty = !draftsEqual(draft, baselineDraft, roster)
  const canSave =
    !busy &&
    validation.errors.length === 0 &&
    (isDirty || baseline.source !== 'user-edited')

  const orderedRoster = displayOrder(draft, roster)

  const setMinutes = (playerId: PlayerId, next: number): void => {
    const clamped = Math.max(0, Math.min(MAX_PLAYER_REGULATION_MINUTES, next))
    setDraft((current) => ({
      ...current,
      minutesByPlayer: { ...current.minutesByPlayer, [playerId]: clamped },
    }))
  }

  const movePlayer = (playerId: PlayerId, direction: -1 | 1): void => {
    setDraft((current) => ({
      ...current,
      order: reorder(current.order, playerId, direction),
    }))
  }

  const handleAuto = (): void => {
    if (
      isDirty &&
      !window.confirm(
        'Replace your unsaved changes with a fresh auto-generated rotation?',
      )
    ) {
      return
    }
    setDraft(
      draftFromPlan(
        generateRotationPlan({ teamId: team.id, roster, rules: RULES }),
        roster,
      ),
    )
  }

  const handleReset = (): void => setDraft(baselineDraft)

  const handleSave = (): void => {
    if (!canSave) {
      return
    }
    onSaveRotationPlan(planFromDraft(draft, team.id, roster, 'user-edited'))
  }

  return (
    <div className="rotation-gameplan-content">
      <div className="page-toolbar">
        <p className="section-intro">
          The top five are your starters — move players up to start them. The plan
          must total exactly {regulation} minutes for {formatTeamName(team)}.
        </p>
        <div className="page-toolbar-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={handleAuto}
            disabled={busy}
          >
            Auto Rotation
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={handleReset}
            disabled={busy || !isDirty}
          >
            Reset
          </button>
          <button
            type="button"
            className="primary-button"
            onClick={handleSave}
            disabled={!canSave}
          >
            {savedPlan === null ? 'Save Rotation' : 'Save Changes'}
          </button>
        </div>
      </div>

      <dl className="player-stat-cards">
        <div
          className={
            totalMinutes === regulation
              ? 'player-stat-card player-stat-card-real'
              : 'player-stat-card player-stat-card-warning'
          }
        >
          <dt>Target Minutes</dt>
          <dd>
            <span className="player-stat-card-value">
              {totalMinutes} / {regulation}
            </span>
          </dd>
        </div>
        <div className="player-stat-card player-stat-card-real">
          <dt>Active Rotation</dt>
          <dd>
            <span className="player-stat-card-value">{activeRotation}</span>
          </dd>
        </div>
        <div className="player-stat-card">
          <dt>
            Plan Status{' '}
            {savedPlan !== null && !isDirty ? (
              <span className="rotation-status-saved">Saved</span>
            ) : (
              <span className="rotation-status-unsaved">Unsaved</span>
            )}
          </dt>
          <dd>
            <span className="player-stat-card-value">
              {baseline.source === 'user-edited' && !isDirty
                ? 'Protected'
                : 'Draft'}
            </span>
          </dd>
        </div>
      </dl>

      <RotationValidationSummary
        errors={validation.errors.map((issue) => issue.message)}
        warnings={validation.warnings.map((issue) => issue.message)}
      />

      <nav className="player-page-tabs" aria-label="Rotation views">
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
          aria-current={activeTab === 'depth'}
          onClick={() => setActiveTab('depth')}
        >
          Depth &amp; Roles
        </button>
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'quarter'}
          onClick={() => setActiveTab('quarter')}
        >
          48-Minute Map
        </button>
        <button
          type="button"
          className="player-tab"
          aria-current={activeTab === 'splits'}
          onClick={() => setActiveTab('splits')}
        >
          6-Minute Splits
        </button>
      </nav>

      {activeTab === 'board' ? (
        <RotationBoard
          team={team}
          orderedRoster={orderedRoster}
          draft={draft}
          tagsByPlayer={tagsByPlayer}
          overallByPlayer={overallByPlayer}
          busy={busy}
          onSetMinutes={setMinutes}
          onMovePlayer={movePlayer}
        />
      ) : activeTab === 'depth' ? (
        <DepthRolesContent team={team} roster={roster} />
      ) : activeTab === 'quarter' ? (
        <RotationMinuteMap
          orderedRoster={orderedRoster}
          draft={draft}
          regulation={regulation}
          segments={PERIOD_COUNT}
          heading="Minutes by quarter"
          labelFor={(index) => `Q${index + 1}`}
        />
      ) : (
        <RotationSplitGrid orderedRoster={orderedRoster} draft={draft} />
      )}
    </div>
  )
}

const TIER_CLASS: Record<RotationTier, string> = {
  Starter: 'rotation-tier-badge tier-starter',
  'Sixth Man': 'rotation-tier-badge tier-sixth',
  Rotation: 'rotation-tier-badge tier-rotation',
  Bench: 'rotation-tier-badge tier-bench',
  Reserve: 'rotation-tier-badge tier-reserve',
}

function RotationBoard({
  team,
  orderedRoster,
  draft,
  tagsByPlayer,
  overallByPlayer,
  busy,
  onSetMinutes,
  onMovePlayer,
}: {
  readonly team: Team
  readonly orderedRoster: readonly Player[]
  readonly draft: RotationDraft
  readonly tagsByPlayer: ReadonlyMap<PlayerId, TacticalTag>
  readonly overallByPlayer: ReadonlyMap<PlayerId, number>
  readonly busy: boolean
  readonly onSetMinutes: (playerId: PlayerId, next: number) => void
  readonly onMovePlayer: (playerId: PlayerId, direction: -1 | 1) => void
}) {
  return (
    <section
      className="player-page-card rotation-board"
      aria-label="Normal rotation"
    >
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">Depth chart</p>
          <h3>Top five start · move players to set the rotation</h3>
        </div>
        <span className="count-badge">{orderedRoster.length} players</span>
      </div>
      <div
        className="table-scroll"
        role="region"
        aria-label="Rotation board table"
        tabIndex={0}
      >
        <table className="roster-table rotation-board-table">
          <caption className="visually-hidden">
            Rotation depth chart for {formatTeamName(team)}
          </caption>
          <thead>
            <tr>
              <th scope="col">Move</th>
              <th scope="col">Player</th>
              <th scope="col">OVR</th>
              <th scope="col">Allowed Positions</th>
              <th scope="col">Minutes</th>
            </tr>
          </thead>
          <tbody>
            {orderedRoster.map((player, index) => {
              const isStarter = index < STARTERS_REQUIRED
              const minutes = draft.minutesByPlayer[player.id] ?? 0
              const tier = deriveRotationTier(draft, player.id)
              const tag = tagsByPlayer.get(player.id)
              return (
                <tr
                  key={player.id}
                  className={isStarter ? 'rotation-row-starter' : undefined}
                >
                  <td>
                    <div className="reorder-controls">
                      <button
                        type="button"
                        className="reorder-button"
                        aria-label={`Move ${formatPlayerName(player)} up`}
                        onClick={() => onMovePlayer(player.id, -1)}
                        disabled={busy || index === 0}
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        className="reorder-button"
                        aria-label={`Move ${formatPlayerName(player)} down`}
                        onClick={() => onMovePlayer(player.id, 1)}
                        disabled={busy || index === orderedRoster.length - 1}
                      >
                        ▼
                      </button>
                    </div>
                  </td>
                  <th scope="row">
                    <span className="player-name">
                      {formatPlayerName(player)}
                    </span>
                    <span className="jersey-number">#{player.jerseyNumber}</span>
                    <span className="rotation-badges">
                      <span className={TIER_CLASS[tier]}>{tier}</span>
                      {tag !== undefined && (
                        <span className="rotation-tag-badge">{tag}</span>
                      )}
                    </span>
                  </th>
                  <td className="rotation-overall">
                    {overallByPlayer.get(player.id) ?? '—'}
                  </td>
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
                  <td>
                    <div className="minute-stepper">
                      <button
                        type="button"
                        className="minute-stepper-button"
                        aria-label={`Decrease minutes for ${formatPlayerName(player)}`}
                        onClick={() => onSetMinutes(player.id, minutes - 1)}
                        disabled={busy || minutes <= 0}
                      >
                        −
                      </button>
                      <span className="minute-stepper-value" aria-live="polite">
                        {minutes}
                      </span>
                      <button
                        type="button"
                        className="minute-stepper-button"
                        aria-label={`Increase minutes for ${formatPlayerName(player)}`}
                        onClick={() => onSetMinutes(player.id, minutes + 1)}
                        disabled={
                          busy || minutes >= MAX_PLAYER_REGULATION_MINUTES
                        }
                      >
                        +
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function RotationMinuteMap({
  orderedRoster,
  draft,
  regulation,
  segments,
  heading,
  labelFor,
}: {
  readonly orderedRoster: readonly Player[]
  readonly draft: RotationDraft
  readonly regulation: number
  readonly segments: number
  readonly heading: string
  readonly labelFor: (index: number) => string
}) {
  const rotationPlayers = orderedRoster.filter(
    (player) => (draft.minutesByPlayer[player.id] ?? 0) > 0,
  )
  const labels = Array.from({ length: segments }, (_, index) => labelFor(index))

  return (
    <section className="player-page-card rotation-map" aria-label={heading}>
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">48-minute map</p>
          <h3>{heading}</h3>
        </div>
      </div>
      <div className="table-scroll" role="region" aria-label={heading} tabIndex={0}>
        <table className="roster-table rotation-quarter-table">
          <thead>
            <tr>
              <th scope="col">Player</th>
              {labels.map((label) => (
                <th key={label} scope="col">
                  {label}
                </th>
              ))}
              <th scope="col">Tot</th>
            </tr>
          </thead>
          <tbody>
            {rotationPlayers.map((player) => {
              const minutes = draft.minutesByPlayer[player.id] ?? 0
              const perSegment = minutesByPeriod(minutes, segments)
              return (
                <tr key={player.id}>
                  <th scope="row">{formatPlayerName(player)}</th>
                  {perSegment.map((value, index) => (
                    <td key={labels[index] ?? index}>{value}</td>
                  ))}
                  <td className="rotation-quarter-total">{minutes}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="coming-later-requirement">
        {/* DEFERRED(§9): live per-block on-court lineups come from the game engine. */}
        An even projection of the {regulation}-minute plan — the exact split
        follows the coach's stints once games are simulated (§9/§14).
      </p>
    </section>
  )
}

/**
 * The 6-minute splits: two grey blocks per quarter (the "12–6" and "6–0"
 * halves). Each block shows each rotation player's projected minutes for that
 * six-minute window — an even projection; live per-block lineups are §9.
 */
function RotationSplitGrid({
  orderedRoster,
  draft,
}: {
  readonly orderedRoster: readonly Player[]
  readonly draft: RotationDraft
}) {
  const rotationPlayers = orderedRoster.filter(
    (player) => (draft.minutesByPlayer[player.id] ?? 0) > 0,
  )
  const totalBlocks = PERIOD_COUNT * 2
  const blockMinutes = new Map<PlayerId, readonly number[]>(
    rotationPlayers.map((player) => [
      player.id,
      minutesByPeriod(draft.minutesByPlayer[player.id] ?? 0, totalBlocks),
    ]),
  )

  return (
    <section
      className="player-page-card rotation-map"
      aria-label="6-minute splits"
    >
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">48-minute map</p>
          <h3>6-minute splits</h3>
        </div>
      </div>
      <div className="rotation-split-quarters">
        {Array.from({ length: PERIOD_COUNT }, (_, quarter) => (
          <div key={quarter} className="rotation-split-quarter">
            <p className="rotation-split-quarter-title">Quarter {quarter + 1}</p>
            <div className="rotation-split-boxes">
              {[0, 1].map((half) => {
                const blockIndex = quarter * 2 + half
                return (
                  <div key={half} className="rotation-split-box">
                    <p className="rotation-split-box-title">
                      {half === 0 ? '12–6' : '6–0'}
                    </p>
                    <ul>
                      {rotationPlayers.map((player) => {
                        const minutes =
                          blockMinutes.get(player.id)?.[blockIndex] ?? 0
                        if (minutes <= 0) {
                          return null
                        }
                        return (
                          <li key={player.id}>
                            <span className="rotation-split-name">
                              {formatPlayerName(player)}
                            </span>
                            <span className="rotation-split-minutes">
                              {minutes}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <p className="coming-later-requirement">
        {/* DEFERRED(§9): live per-block on-court lineups come from the game engine. */}
        An even projection — the exact 6-minute lineups follow the coach's stints
        once games are simulated (§9/§14).
      </p>
    </section>
  )
}

function RotationValidationSummary({
  errors,
  warnings,
}: {
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
}) {
  if (errors.length === 0 && warnings.length === 0) {
    return null
  }
  return (
    <div className="rotation-validation">
      {errors.length > 0 && (
        <div className="rotation-validation-errors" role="alert">
          <p className="rotation-validation-title">
            Fix before saving ({errors.length})
          </p>
          <ul>
            {errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="rotation-validation-warnings">
          <p className="rotation-validation-title">
            Worth a look ({warnings.length})
          </p>
          <ul>
            {warnings.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
