import { expectTypeOf, it } from 'vitest'
import type {
  GameId,
  LeagueId,
  PlayerId,
  SaveId,
  TeamId,
} from '../../src/domain/ids'

it('keeps stable entity ID types distinct', () => {
  expectTypeOf<LeagueId>().not.toEqualTypeOf<TeamId>()
  expectTypeOf<TeamId>().not.toEqualTypeOf<PlayerId>()
  expectTypeOf<PlayerId>().not.toEqualTypeOf<GameId>()
  expectTypeOf<GameId>().not.toEqualTypeOf<SaveId>()
})
