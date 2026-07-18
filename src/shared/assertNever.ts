/**
 * Exhaustiveness guard for a discriminated union. When every variant is handled,
 * the remaining `value` narrows to `never`, so a missed case is a compile-time
 * error at the call site. At runtime it throws, so an unexpected value still
 * fails loudly rather than being silently ignored.
 */
export function assertNever(value: never, label: string): never {
  throw new RangeError(`${label} is unsupported: ${String(value)}`)
}
