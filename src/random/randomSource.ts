/**
 * Injected source for every random decision in generation and simulation code.
 */
export interface RandomSource {
  /** Returns an unsigned integer in [0, 2^32 - 1]. */
  nextUint32(): number

  /** Returns a floating-point value in [0, 1). */
  nextFloat(): number

  /** Returns an integer in [0, maxExclusive). */
  nextInt(maxExclusive: number): number

  /** Returns true with the supplied probability in [0, 1]. */
  chance(probability: number): boolean

  /** Selects one choice in proportion to its finite, non-negative weight. */
  pickWeighted<T>(
    choices: readonly T[],
    weight: (choice: T) => number,
  ): T
}
