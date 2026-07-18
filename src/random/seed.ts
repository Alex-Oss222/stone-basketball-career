export const SEED_DERIVATION_VERSION = 'seed-derivation-v1' as const

export type RandomState = readonly [number, number, number, number]

const HASH_INITIAL_STATE: RandomState = [
  1_779_033_703,
  3_144_134_137,
  1_013_904_242,
  2_773_480_762,
]

const HASH_MULTIPLIERS: RandomState = [
  597_399_067,
  2_869_860_233,
  951_274_213,
  2_716_044_179,
]

const UINT32_HEX_LENGTH = 8
const DERIVED_SEED_DIGEST_LENGTH = UINT32_HEX_LENGTH * 4

/**
 * Normalizes a visible root seed without changing its case or interior spacing.
 */
export function normalizeSeed(seed: string): string {
  const normalized = seed.normalize('NFC').trim()

  if (normalized.length === 0) {
    throw new RangeError('Seed must contain at least one non-whitespace character')
  }

  return normalized
}

/**
 * Derives a stable, versioned seed for an independent labeled random stream.
 */
export function deriveSeed(rootSeed: string, label: string): string {
  const normalizedRoot = normalizeSeed(rootSeed)
  const normalizedLabel = label.normalize('NFC')

  if (normalizedLabel.length === 0) {
    throw new RangeError('Seed label must not be empty')
  }

  const input = [
    SEED_DERIVATION_VERSION,
    utf8Length(normalizedRoot),
    normalizedRoot,
    utf8Length(normalizedLabel),
    normalizedLabel,
  ].join(':')

  return `${SEED_DERIVATION_VERSION}:${formatState(hashUtf8ToState(input))}`
}

/**
 * Extracts a stable hexadecimal prefix from a versioned seed produced by
 * `deriveSeed`. Keeping this format check beside seed derivation prevents
 * identity helpers from silently accepting arbitrary colon-delimited strings.
 */
export function fingerprintDerivedSeed(
  derivedSeed: string,
  length: number,
): string {
  if (!Number.isSafeInteger(length) || length <= 0) {
    throw new RangeError('Derived-seed fingerprint length must be positive')
  }

  const prefix = `${SEED_DERIVATION_VERSION}:`
  if (typeof derivedSeed !== 'string' || !derivedSeed.startsWith(prefix)) {
    throw new TypeError(
      `Derived seed must use the ${SEED_DERIVATION_VERSION} format`,
    )
  }

  const digest = derivedSeed.slice(prefix.length)
  if (
    digest.length !== DERIVED_SEED_DIGEST_LENGTH ||
    /[^0-9a-f]/.test(digest)
  ) {
    throw new TypeError(
      `Derived seed must contain exactly ${DERIVED_SEED_DIGEST_LENGTH} lowercase hexadecimal digits`,
    )
  }
  if (length > digest.length) {
    throw new RangeError('Derived-seed fingerprint exceeds the digest length')
  }

  return digest.slice(0, length)
}

/**
 * Maps a normalized seed to the four non-zero-state words used by xoshiro128**.
 * The UTF-8 hashing and namespace are part of the xoshiro128ss-v1 contract.
 */
export function seedToState(seed: string): RandomState {
  const normalized = normalizeSeed(seed)
  const input = `xoshiro128ss-v1:${utf8Length(normalized)}:${normalized}`
  const state = hashUtf8ToState(input)

  if (state.some((word) => word !== 0)) {
    return state
  }

  // xoshiro128** cannot advance from an all-zero state.
  return [0x9e3779b9, 0x243f6a88, 0xb7e15162, 0x8aed2a6b]
}

function formatState(state: RandomState): string {
  return state
    .map((word) => word.toString(16).padStart(UINT32_HEX_LENGTH, '0'))
    .join('')
}

/**
 * A versioned four-lane 32-bit hash. Input is processed as UTF-8 bytes so the
 * same JavaScript string produces identical state in browsers and Node.
 */
function hashUtf8ToState(value: string): RandomState {
  let [h1, h2, h3, h4] = HASH_INITIAL_STATE
  const [m1, m2, m3, m4] = HASH_MULTIPLIERS

  forEachUtf8Byte(value, (byte) => {
    h1 = h2 ^ Math.imul(h1 ^ byte, m1)
    h2 = h3 ^ Math.imul(h2 ^ byte, m2)
    h3 = h4 ^ Math.imul(h3 ^ byte, m3)
    h4 = h1 ^ Math.imul(h4 ^ byte, m4)
  })

  h1 = Math.imul(h3 ^ (h1 >>> 18), m1)
  h2 = Math.imul(h4 ^ (h2 >>> 22), m2)
  h3 = Math.imul(h1 ^ (h3 >>> 17), m3)
  h4 = Math.imul(h2 ^ (h4 >>> 19), m4)

  h1 ^= h2 ^ h3 ^ h4
  h2 ^= h1
  h3 ^= h1
  h4 ^= h1

  return [h1 >>> 0, h2 >>> 0, h3 >>> 0, h4 >>> 0]
}

function utf8Length(value: string): number {
  let length = 0
  forEachUtf8Byte(value, () => {
    length += 1
  })
  return length
}

function forEachUtf8Byte(value: string, visit: (byte: number) => void): void {
  for (let index = 0; index < value.length; index += 1) {
    const firstCodeUnit = value.charCodeAt(index)
    let codePoint = firstCodeUnit

    if (firstCodeUnit >= 0xd800 && firstCodeUnit <= 0xdbff) {
      const secondCodeUnit = value.charCodeAt(index + 1)

      if (secondCodeUnit >= 0xdc00 && secondCodeUnit <= 0xdfff) {
        codePoint =
          0x10000 +
          ((firstCodeUnit - 0xd800) << 10) +
          (secondCodeUnit - 0xdc00)
        index += 1
      } else {
        codePoint = 0xfffd
      }
    } else if (firstCodeUnit >= 0xdc00 && firstCodeUnit <= 0xdfff) {
      codePoint = 0xfffd
    }

    if (codePoint <= 0x7f) {
      visit(codePoint)
    } else if (codePoint <= 0x7ff) {
      visit(0xc0 | (codePoint >>> 6))
      visit(0x80 | (codePoint & 0x3f))
    } else if (codePoint <= 0xffff) {
      visit(0xe0 | (codePoint >>> 12))
      visit(0x80 | ((codePoint >>> 6) & 0x3f))
      visit(0x80 | (codePoint & 0x3f))
    } else {
      visit(0xf0 | (codePoint >>> 18))
      visit(0x80 | ((codePoint >>> 12) & 0x3f))
      visit(0x80 | ((codePoint >>> 6) & 0x3f))
      visit(0x80 | (codePoint & 0x3f))
    }
  }
}
