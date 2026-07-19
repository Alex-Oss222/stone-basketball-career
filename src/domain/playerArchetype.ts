import { deriveAllCategoryScores } from './detailedRatings'
import type { DetailedPlayerRatings } from './detailedRatings'
import type { PlayerMeasurements } from './league'
import { deriveFunctionalSize } from './playerDerivations'

/**
 * §8 derived-label layer (display-only, never stored, **never read by the
 * sim** — the tag is a summary *of* the ratings, never a constraint *on* what
 * the player does when games simulate).
 *
 * **Tactical tag** — the player's on-court style (Playmaker, Scorer, …), the
 * single best-fit of eight from the 26 category scores. Shown on the rotation
 * board next to each player. A versioned v1 heuristic tuned by weights.
 *
 * NOTE: the headline **Player type** (e.g. a named profile per position) is
 * deliberately NOT here — it comes from Alex's authored Excel profiles + the
 * position-weighted matching criteria, which are not yet in the repo.
 */
export const TACTICAL_TAG_VERSION = 1 as const

export const TACTICAL_TAGS = [
  'Playmaker',
  'Scorer',
  'Shooter',
  'Wing Defender',
  'Rim Protector',
  'Rebounder',
  'Energy',
  'Closer',
] as const
export type TacticalTag = (typeof TACTICAL_TAGS)[number]

/**
 * The best-fit tactical tag: a weighted score per tag over the category scores,
 * highest wins (ties break by the canonical tag order). Each weight set sums to
 * 1 so the scores stay on the same 0–100 scale.
 */
export function deriveTacticalTag(
  ratings: DetailedPlayerRatings,
  measurements: PlayerMeasurements,
): TacticalTag {
  const s = deriveAllCategoryScores(ratings)
  const size = deriveFunctionalSize(measurements)

  const scores: Record<TacticalTag, number> = {
    Playmaker: 0.5 * s.passing + 0.3 * s.ballHandling + 0.2 * s.offensiveIQ,
    Scorer:
      0.32 * s.rimFinishing +
      0.26 * s.midRangeShooting +
      0.24 * s.threePointShooting +
      0.18 * s.postScoring,
    Shooter:
      0.55 * s.threePointShooting +
      0.2 * s.midRangeShooting +
      0.15 * s.freeThrowShooting +
      0.1 * s.offBallOffense,
    'Wing Defender':
      0.4 * s.perimeterDefense +
      0.2 * s.offBallDefense +
      0.2 * s.agility +
      0.2 * s.stealing,
    'Rim Protector':
      0.42 * s.interiorDefense + 0.34 * s.blocking + 0.24 * size,
    Rebounder:
      0.5 * s.defensiveRebounding +
      0.3 * s.offensiveRebounding +
      0.2 * s.strength,
    Energy:
      0.4 * s.competitiveMakeup +
      0.22 * s.conditioning +
      0.19 * s.offensiveRebounding +
      0.19 * s.defensiveRebounding,
    Closer:
      0.3 * s.midRangeShooting +
      0.25 * s.threePointShooting +
      0.25 * s.competitiveMakeup +
      0.2 * s.offensiveIQ,
  }

  let best: TacticalTag = TACTICAL_TAGS[0]
  let bestScore = Number.NEGATIVE_INFINITY
  for (const tag of TACTICAL_TAGS) {
    if (scores[tag] > bestScore) {
      bestScore = scores[tag]
      best = tag
    }
  }
  return best
}
