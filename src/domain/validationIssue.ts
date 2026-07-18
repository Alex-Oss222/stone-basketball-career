import { isLocalDate } from './localDate'

/**
 * The shared shape every domain aggregate uses to report a validation problem:
 * a stable machine `code`, a JSON-path-like `path` to the offending value, and
 * a human-readable `message`. Each aggregate re-exports this under its own name
 * (e.g. SeasonValidationIssue) so its public surface is unchanged.
 */
export interface ValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function isPositiveSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) > 0
}

export function addIssue(
  issues: ValidationIssue[],
  code: string,
  path: string,
  message: string,
): void {
  issues.push({ code, path, message })
}

/**
 * Records the supplied `code`/`message` when a nullable field is neither null
 * nor a valid LocalDate. The code and message are passed in because they are
 * aggregate-specific, keeping every emitted issue byte-identical to the inline
 * checks this replaced.
 */
export function validateNullableLocalDate(
  value: unknown,
  path: string,
  issues: ValidationIssue[],
  code: string,
  message: string,
): void {
  if (value !== null && !isLocalDate(value)) {
    addIssue(issues, code, path, message)
  }
}
