import type { RandomSource } from './randomSource'
import { seedToState } from './seed'

export const RANDOM_SOURCE_VERSION = 'xoshiro128ss-v1' as const

const UINT32_RANGE = 0x1_0000_0000

export class Xoshiro128StarStar implements RandomSource {
  private state0: number
  private state1: number
  private state2: number
  private state3: number

  constructor(seed: string) {
    const [state0, state1, state2, state3] = seedToState(seed)
    this.state0 = state0
    this.state1 = state1
    this.state2 = state2
    this.state3 = state3
  }

  nextUint32(): number {
    const result = Math.imul(rotateLeft(Math.imul(this.state1, 5), 7), 9)
    const shifted = this.state1 << 9

    this.state2 ^= this.state0
    this.state3 ^= this.state1
    this.state1 ^= this.state2
    this.state0 ^= this.state3
    this.state2 ^= shifted
    this.state3 = rotateLeft(this.state3, 11)

    this.state0 >>>= 0
    this.state1 >>>= 0
    this.state2 >>>= 0
    this.state3 >>>= 0

    return result >>> 0
  }

  nextFloat(): number {
    return this.nextUint32() / UINT32_RANGE
  }

  nextInt(maxExclusive: number): number {
    if (
      !Number.isSafeInteger(maxExclusive) ||
      maxExclusive <= 0 ||
      maxExclusive > UINT32_RANGE
    ) {
      throw new RangeError(
        `maxExclusive must be a positive integer no greater than ${UINT32_RANGE}`,
      )
    }

    const acceptanceLimit =
      UINT32_RANGE - (UINT32_RANGE % maxExclusive)
    let value = this.nextUint32()

    while (value >= acceptanceLimit) {
      value = this.nextUint32()
    }

    return value % maxExclusive
  }

  chance(probability: number): boolean {
    if (!Number.isFinite(probability) || probability < 0 || probability > 1) {
      throw new RangeError('Probability must be a finite number in [0, 1]')
    }

    return this.nextFloat() < probability
  }

  pickWeighted<T>(
    choices: readonly T[],
    weight: (choice: T) => number,
  ): T {
    if (choices.length === 0) {
      throw new RangeError('Weighted choices must not be empty')
    }

    const weights: number[] = []
    let totalWeight = 0
    let lastPositiveIndex = -1

    for (let index = 0; index < choices.length; index += 1) {
      const choiceWeight = weight(choices[index])

      if (!Number.isFinite(choiceWeight) || choiceWeight < 0) {
        throw new RangeError('Weights must be finite, non-negative numbers')
      }

      weights.push(choiceWeight)
      totalWeight += choiceWeight

      if (!Number.isFinite(totalWeight)) {
        throw new RangeError('Total weight must be finite')
      }

      if (choiceWeight > 0) {
        lastPositiveIndex = index
      }
    }

    if (lastPositiveIndex === -1) {
      throw new RangeError('At least one weight must be greater than zero')
    }

    const target = this.nextFloat() * totalWeight
    let cumulativeWeight = 0

    for (let index = 0; index < choices.length; index += 1) {
      cumulativeWeight += weights[index]

      if (target < cumulativeWeight) {
        return choices[index]
      }
    }

    return choices[lastPositiveIndex]
  }
}

export function createRandomSource(seed: string): RandomSource {
  return new Xoshiro128StarStar(seed)
}

function rotateLeft(value: number, bits: number): number {
  return ((value << bits) | (value >>> (32 - bits))) >>> 0
}
