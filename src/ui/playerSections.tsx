import type { Player, Position } from '../domain/league'
import { POSITIONS } from '../domain/league'
import { deriveRoleFit } from '../domain/playerDerivations'

/**
 * Shared sections for the Player Quick View (hover preview on the roster) and
 * the full player page. Every deferred slot is tagged once, here, at the exact
 * place its data plugs in — both screens fill together when the data lands.
 */

/** DEFERRED(§11): per-game stats fill from the season-statistics fold. */
export function KeyStatsSection() {
  return (
    <DeferredStatRow
      title="Key Stats"
      labels={['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'TS%']}
      note="Per-game stats arrive with the simulation and season statistics."
    />
  )
}

/** DEFERRED(§8): target/actual role and minutes come from the rotation plan. */
export function TargetRoleSection() {
  return (
    <DeferredFieldRows
      title="Target Role"
      labels={[
        'Target Role',
        'Actual Role',
        'Target MPG',
        'Actual MPG',
        'Usage Rate',
      ]}
      note="Roles and minutes arrive with the rotation plan and simulation."
    />
  )
}

/** DEFERRED(later): contract figures need the financial model. */
export function ContractSection() {
  return (
    <DeferredFieldRows
      title="Contract"
      labels={[
        'Contract',
        'Years Left',
        'Guaranteed',
        'Total Value',
        'Contract Type',
      ]}
      note="Contract details arrive with the financial model."
    />
  )
}

/**
 * Position & Role Coverage — all real (§8B R5): the numeric fit is the Role Fit
 * (position-weighted score) at each position; natural/secondary labels come
 * from the player's positions.
 */
export function PositionCoverageSection({ player }: { readonly player: Player }) {
  return (
    <section className="pqv-section" aria-label="Position and role coverage">
      <h4>Position &amp; Role Coverage</h4>
      <dl className="pqv-field-rows">
        {POSITIONS.map((position) => {
          const fit = deriveRoleFit(
            player.ratings,
            player.measurements,
            position,
          )
          const label = coverageLabel(player, position)
          return (
            <div key={position}>
              <dt>{position}</dt>
              <dd>{label === '—' ? String(fit) : `${fit} · ${label}`}</dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}

export function ComingLaterAction({
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

/** A one-row, left-to-right strip: stat labels across, honest "—" beneath. */
function DeferredStatRow({
  title,
  labels,
  note,
}: {
  readonly title: string
  readonly labels: readonly string[]
  readonly note: string
}) {
  return (
    <section className="pqv-section" aria-label={title}>
      <h4>
        {title} <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="pqv-stat-row">
        {labels.map((label) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">{note}</p>
    </section>
  )
}

/** One full-width block: each row runs label on the left, value flush right. */
function DeferredFieldRows({
  title,
  labels,
  note,
}: {
  readonly title: string
  readonly labels: readonly string[]
  readonly note: string
}) {
  return (
    <section className="pqv-section" aria-label={title}>
      <h4>
        {title} <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="pqv-field-rows">
        {labels.map((label) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">{note}</p>
    </section>
  )
}

function coverageLabel(player: Player, position: Position): string {
  if (position === player.primaryPosition) {
    return 'Natural'
  }
  if (position === player.secondaryPosition) {
    return 'Secondary'
  }
  return '—'
}
