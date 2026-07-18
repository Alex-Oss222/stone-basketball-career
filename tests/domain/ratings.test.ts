import { describe, expect, expectTypeOf, it } from 'vitest'
import { ratingToGrade } from '../../src/domain/ratings'
import type { Grade } from '../../src/domain/ratings'

/**
 * The legacy 16-macro-rating model was removed with the §8B R4 version break;
 * the stored model and its strict parser live in detailedRatings.ts and are
 * covered by tests/domain/detailedRatings.test.ts. This file pins what
 * remains here: the shared grade scale.
 */
describe('grade union', () => {
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
