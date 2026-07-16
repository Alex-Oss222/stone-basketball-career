import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
  isRatingKey,
  isStoredRating,
  parsePlayerRatings,
  parseStoredRating,
  ratingToGrade,
} from '../../src/domain/ratings'
import type {
  Grade,
  PlayerRatings,
  RatingKey,
} from '../../src/domain/ratings'

const VALID_PLAYER_RATINGS = {
  insideScoring: 0,
  midRangeShooting: 7,
  threePointShooting: 14,
  freeThrowShooting: 21,
  passing: 28,
  ballHandling: 35,
  offensiveRebounding: 42,
  defensiveRebounding: 49,
  perimeterDefense: 56,
  interiorDefense: 63,
  stealing: 70,
  blocking: 77,
  speed: 84,
  strength: 91,
  endurance: 98,
  basketballIQ: 100,
} satisfies PlayerRatings

describe('stored rating keys and types', () => {
  it('exports the exact sixteen unique stored rating keys', () => {
    expect(RATING_KEYS).toEqual([
      'insideScoring',
      'midRangeShooting',
      'threePointShooting',
      'freeThrowShooting',
      'passing',
      'ballHandling',
      'offensiveRebounding',
      'defensiveRebounding',
      'perimeterDefense',
      'interiorDefense',
      'stealing',
      'blocking',
      'speed',
      'strength',
      'endurance',
      'basketballIQ',
    ])
    expect(RATING_KEYS).toHaveLength(16)
    expect(new Set(RATING_KEYS).size).toBe(16)
    expect(RATING_KEYS.every(isRatingKey)).toBe(true)
    expect(isRatingKey('finishing')).toBe(false)
  })

  it('pins the initial rating generation version', () => {
    expect(RATING_GENERATION_VERSION).toBe(1)
  })

  it('defines PlayerRatings as a closed readonly record', () => {
    expectTypeOf<RatingKey>().toEqualTypeOf<keyof PlayerRatings>()
    expectTypeOf<
      string extends keyof PlayerRatings ? true : false
    >().toEqualTypeOf<false>()
    expectTypeOf<PlayerRatings>().toEqualTypeOf<
      Readonly<Record<RatingKey, number>>
    >()
  })

  it('defines the exact grade union', () => {
    expectTypeOf<Grade>().toEqualTypeOf<
      | 'A+'
      | 'A'
      | 'A-'
      | 'B+'
      | 'B'
      | 'B-'
      | 'C+'
      | 'C'
      | 'C-'
      | 'D+'
      | 'D'
      | 'D-'
      | 'F'
    >()
  })
})

describe('stored rating parsing', () => {
  it.each([0, 1, 50, 99, 100])('accepts integer rating %s unchanged', (rating) => {
    expect(isStoredRating(rating)).toBe(true)
    expect(parseStoredRating(rating)).toBe(rating)
  })

  it.each([
    '50',
    null,
    undefined,
    {},
    [],
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    50.5,
    -1,
    101,
  ])('rejects invalid stored rating %#', (rating) => {
    expect(isStoredRating(rating)).toBe(false)
    expect(() => parseStoredRating(rating)).toThrow()
  })

  it('accepts a complete rating record in canonical key order', () => {
    const parsed = parsePlayerRatings(VALID_PLAYER_RATINGS)

    expect(parsed).toEqual(VALID_PLAYER_RATINGS)
    expect(Object.keys(parsed)).toEqual(RATING_KEYS)
  })

  it.each(RATING_KEYS)('rejects a record missing %s', (missingKey) => {
    const incomplete: Record<string, unknown> = { ...VALID_PLAYER_RATINGS }
    delete incomplete[missingKey]

    expect(() => parsePlayerRatings(incomplete)).toThrow(TypeError)
  })

  it('rejects extra fields, including a stored letter grade', () => {
    expect(() =>
      parsePlayerRatings({ ...VALID_PLAYER_RATINGS, grade: 'A' }),
    ).toThrow(TypeError)
  })

  it('rejects an invalid value inside an otherwise complete record', () => {
    expect(() =>
      parsePlayerRatings({ ...VALID_PLAYER_RATINGS, speed: 72.5 }),
    ).toThrow(RangeError)
  })
})

describe('ratingToGrade', () => {
  it.each<[number, Grade]>([
    [0, 'F'],
    [40, 'D-'],
    [45, 'D'],
    [50, 'D+'],
    [55, 'C-'],
    [60, 'C'],
    [65, 'C+'],
    [70, 'B-'],
    [75, 'B'],
    [80, 'B+'],
    [85, 'A-'],
    [90, 'A'],
    [95, 'A+'],
    [100, 'A+'],
  ])('maps boundary %s to %s', (rating, grade) => {
    expect(ratingToGrade(rating)).toBe(grade)
  })

  it.each<[number, Grade]>([
    [99.999, 'A+'],
    [94.999, 'A'],
    [89.999, 'A-'],
    [84.999, 'B+'],
    [79.999, 'B'],
    [74.999, 'B-'],
    [69.999, 'C+'],
    [64.999, 'C'],
    [59.999, 'C-'],
    [54.999, 'D+'],
    [49.999, 'D'],
    [44.999, 'D-'],
    [39.999, 'F'],
  ])('maps decimal %s directly below a boundary to %s', (rating, grade) => {
    expect(ratingToGrade(rating)).toBe(grade)
  })

  it('accepts decimal values inside a grade band', () => {
    expect(ratingToGrade(72.5)).toBe('B-')
  })

  it.each([
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    -0.001,
    100.001,
  ])('rejects invalid grade input %#', (rating) => {
    expect(() => ratingToGrade(rating)).toThrow()
  })
})
