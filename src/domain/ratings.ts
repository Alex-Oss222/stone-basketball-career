export const STORED_RATING_MIN = 0
export const STORED_RATING_MAX = 100

export const RATING_KEYS = [
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
] as const

export type RatingKey = (typeof RATING_KEYS)[number]

export type PlayerRatings = Readonly<Record<RatingKey, number>>

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

const RATING_KEY_SET: ReadonlySet<string> = new Set(RATING_KEYS)

export function isStoredRating(value: unknown): value is number {
  return (
    typeof value === 'number' &&
    Number.isFinite(value) &&
    Number.isInteger(value) &&
    value >= STORED_RATING_MIN &&
    value <= STORED_RATING_MAX
  )
}

/** Validates one persisted rating without coercing or clamping it. */
export function parseStoredRating(value: unknown): number {
  if (typeof value !== 'number') {
    throw new TypeError('Stored rating must be a number')
  }
  if (!isStoredRating(value)) {
    throw new RangeError(
      `Stored rating must be a finite integer from ${STORED_RATING_MIN} through ${STORED_RATING_MAX}`,
    )
  }
  return value
}

/** Validates the exact persisted 16-rating record and rejects extra fields. */
export function parsePlayerRatings(value: unknown): PlayerRatings {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Player ratings must be an object')
  }

  const ownKeys = Reflect.ownKeys(value)
  if (
    ownKeys.length !== RATING_KEYS.length ||
    ownKeys.some((key) => typeof key !== 'string' || !RATING_KEY_SET.has(key))
  ) {
    throw new TypeError('Player ratings must contain exactly the stored rating keys')
  }

  const source = value as Record<RatingKey, unknown>
  return Object.fromEntries(
    RATING_KEYS.map((key) => [key, parseStoredRating(source[key])]),
  ) as PlayerRatings
}

/** Converts a numeric rating or future decimal category score to a derived grade. */
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
