declare const stableIdBrand: unique symbol

type StableId<Kind extends string> = string & {
  readonly [stableIdBrand]: Kind
}

export type LeagueId = StableId<'LeagueId'>
export type TeamId = StableId<'TeamId'>
export type PlayerId = StableId<'PlayerId'>
export type GameId = StableId<'GameId'>
export type SaveId = StableId<'SaveId'>
