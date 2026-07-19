import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  TACTICAL_TAGS,
  deriveTacticalTag,
} from '../../src/domain/playerArchetype'

const league = generateLeague('tactical-tag-seed')

describe('deriveTacticalTag', () => {
  it('assigns every player exactly one valid, deterministic tag', () => {
    for (const player of league.players) {
      const tag = deriveTacticalTag(player.ratings, player.measurements)
      expect(TACTICAL_TAGS).toContain(tag)
      // Deterministic: the same ratings always resolve to the same tag.
      expect(deriveTacticalTag(player.ratings, player.measurements)).toBe(tag)
    }
  })

  it('covers more than one tag across a generated league', () => {
    const tags = new Set(
      league.players.map((player) =>
        deriveTacticalTag(player.ratings, player.measurements),
      ),
    )
    expect(tags.size).toBeGreaterThan(1)
  })
})
