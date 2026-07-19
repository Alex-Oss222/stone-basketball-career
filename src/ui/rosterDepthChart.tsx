import type { Player, Position } from '../domain/league'
import { POSITIONS } from '../domain/league'
import { deriveOverall } from '../domain/playerDerivations'

export interface RosterDepthChartProps {
  readonly roster: readonly Player[]
}

/**
 * Depth Chart — the half-court panel at the top right of the roster screen.
 * Each position zone lists its natural players. The numbers shown are the
 * player's Headline OVR (real, ratings-based), not simulated results.
 * DEFERRED(§8): today the order within a zone is by Headline OVR; the
 * rotation plan replaces it with real depth ordering when §8 lands.
 */
export function RosterDepthChart({ roster }: RosterDepthChartProps) {
  return (
    <section className="depth-chart-panel" aria-label="Depth chart">
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">Position coverage</p>
          <h3>Depth Chart</h3>
        </div>
      </div>

      <div className="depth-chart-court">
        <div className="depth-chart-court-lines" aria-hidden="true" />
        {POSITIONS.map((position) => (
          <div
            key={position}
            className={`depth-zone depth-zone-${position.toLowerCase()}`}
          >
            <h4>{position}</h4>
            <ol className="depth-zone-players">
              {naturalPlayersByOverall(roster, position).map((player) => (
                <li key={player.id}>
                  <span className="depth-player-name">
                    {abbreviatePlayerName(player)}
                  </span>{' '}
                  <span className="depth-player-overall">
                    ({deriveOverall(player)})
                  </span>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>

      <p className="coming-later-requirement">
        Ordered by the derived Overall until the rotation plan (§8) sets real
        depth.
      </p>
    </section>
  )
}

function naturalPlayersByOverall(
  roster: readonly Player[],
  position: Position,
): readonly Player[] {
  return roster
    .filter((player) => player.primaryPosition === position)
    .slice()
    .sort((first, second) => deriveOverall(second) - deriveOverall(first))
}

function abbreviatePlayerName(player: Player): string {
  return `${player.firstName.charAt(0)}. ${player.lastName}`
}
