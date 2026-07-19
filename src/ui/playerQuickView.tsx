import { useEffect, useState } from 'react'
import type { Player, Team } from '../domain/league'
import { formatTeamName } from '../domain/league'
import { deriveOverall } from '../domain/playerDerivations'
import { formatPlayerName } from './leagueViewModel'
import {
  ContractSection,
  KeyStatsSection,
  PositionCoverageSection,
  TargetRoleSection,
} from './playerSections'

export type PlayerQuickViewTab = 'overview' | 'health' | 'development'

export interface PlayerQuickViewProps {
  readonly player: Player
  readonly team: Team
  /**
   * Pinned mode: after the hover dwells, the card sticks and becomes
   * interactive — a close button appears and Escape closes it. The Overview /
   * Health / Development tab strip is always present in both modes; pinning
   * only adds the close affordance.
   */
  readonly pinned?: boolean
  readonly onClose?: () => void
  /** Dev/test convenience only; the tab is transient UI state. */
  readonly initialTab?: PlayerQuickViewTab
}

/**
 * Player Quick View — the hover preview on the roster. It renders only while a
 * player is hovered (or keyboard-focused) and clicking the player opens the
 * full player page. The card shows identity + the Headline OVR, an always-
 * present Overview / Health / Development tab strip, then (on Overview) the
 * left-to-right Key Stats row and the Target Role, Contract, and Position &
 * Role Coverage blocks. The Health and Development tabs are always available
 * (honest Coming-later slots), not gated behind pinning; dwelling only pins the
 * card and reveals the close button. Every value is one of two honest states —
 * real today, or a plainly-labelled "Coming later" slot. Headline OVR is a
 * transparent display value, never stored and never read by the simulation;
 * Potential is not shown.
 */
export function PlayerQuickView({
  player,
  team,
  pinned = false,
  onClose,
  initialTab = 'overview',
}: PlayerQuickViewProps) {
  const [activeTab, setActiveTab] = useState<PlayerQuickViewTab>(initialTab)
  const name = formatPlayerName(player)
  const overall = deriveOverall(player)
  const positionLabel =
    player.secondaryPosition === null
      ? player.primaryPosition
      : `${player.primaryPosition} / ${player.secondaryPosition}`

  useEffect(() => {
    setActiveTab('overview')
  }, [player.id])

  return (
    <aside
      id="player-details"
      className="player-quick-view"
      aria-labelledby="player-quick-view-heading"
    >
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Quick view for {name}
      </p>

      <div className="pqv-pinned-bar">
        <nav className="pqv-pinned-tabs" aria-label="Quick view sections">
          {(
            [
              ['overview', 'Overview'],
              ['health', 'Health'],
              ['development', 'Development'],
            ] as const
          ).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              className="pqv-pinned-tab"
              aria-current={activeTab === tab}
              onClick={() => setActiveTab(tab)}
            >
              {label}
            </button>
          ))}
        </nav>
        {pinned && onClose !== undefined && (
          <button
            type="button"
            className="pqv-pinned-close"
            aria-label="Close quick view"
            onClick={onClose}
          >
            ✕
          </button>
        )}
      </div>

      <header className="pqv-header">
        <div className="pqv-identity">
          <p className="panel-kicker">Player Quick View</p>
          <h3 id="player-quick-view-heading">{name}</h3>
          <p className="pqv-meta">
            #{player.jerseyNumber} · {positionLabel} · Age {player.age} ·{' '}
            {formatTeamName(team)}
          </p>
        </div>
        <div
          className="pqv-overall"
          title="Headline OVR (model v3) — the reward-peaks score across the player's eligible positions, derived from the stored base ratings and never stored itself"
        >
          <span className="pqv-overall-value">{overall}</span>
          <span className="pqv-overall-label">OVR</span>
        </div>
      </header>

      {activeTab === 'overview' ? (
        <>
          <KeyStatsSection />
          <TargetRoleSection />
          <ContractSection />
          <PositionCoverageSection player={player} />
        </>
      ) : activeTab === 'health' ? (
        <QuickViewHealthTab />
      ) : (
        <QuickViewDevelopmentTab />
      )}
    </aside>
  )
}

/** DEFERRED(later): availability, restrictions, and caps need the medical system. */
function QuickViewHealthTab() {
  return (
    <section className="pqv-section" aria-label="Health">
      <h4>
        Health <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="pqv-field-rows">
        {[
          'Status',
          'Practice',
          'Restriction',
          'Minutes Cap',
          'Next Review',
        ].map((label) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">
        Availability, restrictions, and minute caps arrive with the medical
        system.
      </p>
    </section>
  )
}

/** DEFERRED(later): plans, coaches, and progress need the development system. */
function QuickViewDevelopmentTab() {
  return (
    <section className="pqv-section" aria-label="Development">
      <h4>
        Development <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="pqv-field-rows">
        {[
          'Primary Focus',
          'Assigned Coach',
          'Intensity',
          'Progress',
          'Next Review',
        ].map((label) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">
        Player plans, coaching assignments, and progress arrive with the
        development system.
      </p>
    </section>
  )
}
