/**
 * The shared rating scale and derived letter-grade boundaries. The stored
 * player model itself is the detailed 67-sub-rating record in
 * `detailedRatings.ts` (ADR 0008) — the legacy 16-macro-rating model was
 * removed with the §8B R4 version break.
 */
export const STORED_RATING_MIN = 0
export const STORED_RATING_MAX = 100

export type Grade =
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

/** Converts a numeric rating or decimal derived category score to a grade. */
export function ratingToGrade(rating: number): Grade {
  if (typeof rating !== 'number' || !Number.isFinite(rating)) {
    throw new TypeError('Rating must be a finite number')
  }
  if (rating < STORED_RATING_MIN || rating > STORED_RATING_MAX) {
    throw new RangeError(
      `Rating must be from ${STORED_RATING_MIN} through ${STORED_RATING_MAX}`,
    )
  }

  if (rating >= 95) return 'A+'
  if (rating >= 90) return 'A'
  if (rating >= 85) return 'A-'
  if (rating >= 80) return 'B+'
  if (rating >= 75) return 'B'
  if (rating >= 70) return 'B-'
  if (rating >= 65) return 'C+'
  if (rating >= 60) return 'C'
  if (rating >= 55) return 'C-'
  if (rating >= 50) return 'D+'
  if (rating >= 45) return 'D'
  if (rating >= 40) return 'D-'
  return 'F'
}
