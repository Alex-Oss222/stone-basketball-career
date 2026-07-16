export type SerializedRecord = Record<string, unknown>

export type RejectSerializedValue = (
  path: string,
  message: string,
) => never

/**
 * Rejects values whose JSON round trip would lose information or execute an
 * accessor. Schema-specific parsing still verifies every exact key set.
 */
export function assertJsonSafeValue(
  value: unknown,
  path: string,
  reject: RejectSerializedValue,
): void {
  assertJsonSafeValueWithAncestors(value, path, reject, new Set<object>())
}

export function expectExactRecord(
  value: unknown,
  expectedKeys: readonly string[],
  path: string,
  reject: RejectSerializedValue,
): SerializedRecord {
  if (!isPlainRecord(value)) {
    reject(path, 'Expected a plain record')
  }

  const expectedKeySet = new Set(expectedKeys)
  const actualKeys = Reflect.ownKeys(value)
  for (const expectedKey of expectedKeys) {
    if (!Object.prototype.hasOwnProperty.call(value, expectedKey)) {
      reject(`${path}.${expectedKey}`, 'Required property is missing')
    }
  }
  for (const actualKey of actualKeys) {
    if (typeof actualKey !== 'string') {
      reject(path, 'Symbol properties are not allowed')
    }
    if (!expectedKeySet.has(actualKey)) {
      reject(`${path}.${actualKey}`, 'Unexpected property')
    }
    expectEnumerableDataDescriptor(value, actualKey, `${path}.${actualKey}`, reject)
  }
  return value
}

export function parseDenseArray<T>(
  value: unknown,
  path: string,
  parseItem: (item: unknown, itemPath: string) => T,
  reject: RejectSerializedValue,
): readonly T[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    reject(path, 'Expected a plain array')
  }

  const actualKeys = Reflect.ownKeys(value)
  if (actualKeys.length !== value.length + 1) {
    reject(path, 'Array must be dense and contain no custom properties')
  }
  for (const key of actualKeys) {
    if (typeof key !== 'string') {
      reject(path, 'Array symbol properties are not allowed')
    }
    if (key === 'length') {
      continue
    }
    const index = Number(key)
    if (
      !Number.isInteger(index) ||
      index < 0 ||
      index >= value.length ||
      String(index) !== key
    ) {
      reject(path, 'Array contains a custom property')
    }
  }

  const parsed: T[] = []
  for (let index = 0; index < value.length; index += 1) {
    const itemPath = `${path}[${index}]`
    if (!Object.prototype.hasOwnProperty.call(value, index)) {
      reject(itemPath, 'Array item is missing')
    }
    const descriptor = expectEnumerableDataDescriptor(
      value,
      String(index),
      itemPath,
      reject,
    )
    parsed.push(parseItem(descriptor.value, itemPath))
  }
  return parsed
}

export function expectString(
  value: unknown,
  path: string,
  reject: RejectSerializedValue,
): string {
  if (typeof value !== 'string') {
    reject(path, 'Expected a string')
  }
  return value
}

export function expectSafeInteger(
  value: unknown,
  path: string,
  reject: RejectSerializedValue,
): number {
  if (
    typeof value !== 'number' ||
    !Number.isSafeInteger(value) ||
    Object.is(value, -0)
  ) {
    reject(path, 'Expected a JSON-stable safe integer')
  }
  return value
}

export function expectPositiveSafeInteger(
  value: unknown,
  path: string,
  reject: RejectSerializedValue,
): number {
  const integer = expectSafeInteger(value, path, reject)
  if (integer <= 0) {
    reject(path, 'Expected a positive safe integer')
  }
  return integer
}

export function expectLiteral<T extends string | number>(
  value: unknown,
  expected: T,
  path: string,
  reject: RejectSerializedValue,
): T {
  if (value !== expected) {
    reject(path, `Expected literal ${JSON.stringify(expected)}`)
  }
  return expected
}

export function expectOneOf<const Values extends readonly string[]>(
  value: unknown,
  allowed: Values,
  path: string,
  reject: RejectSerializedValue,
): Values[number] {
  if (
    typeof value !== 'string' ||
    !allowed.some((candidate) => candidate === value)
  ) {
    reject(path, `Expected one of ${allowed.join(', ')}`)
  }
  return value as Values[number]
}

function assertJsonSafeValueWithAncestors(
  value: unknown,
  path: string,
  reject: RejectSerializedValue,
  ancestors: Set<object>,
): void {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'boolean'
  ) {
    return
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || Object.is(value, -0)) {
      reject(path, 'Number cannot survive an exact JSON round trip')
    }
    return
  }
  if (typeof value !== 'object') {
    reject(path, `Unsupported JSON value type ${typeof value}`)
  }
  if (ancestors.has(value)) {
    reject(path, 'Circular references are not allowed')
  }

  ancestors.add(value)
  try {
    if (Array.isArray(value)) {
      assertJsonSafeArray(value, path, reject, ancestors)
      return
    }
    if (!isPlainRecord(value)) {
      reject(path, 'Expected a plain record')
    }
    for (const key of Reflect.ownKeys(value)) {
      if (typeof key !== 'string') {
        reject(path, 'Symbol properties are not allowed')
      }
      const descriptor = expectEnumerableDataDescriptor(
        value,
        key,
        `${path}.${key}`,
        reject,
      )
      assertJsonSafeValueWithAncestors(
        descriptor.value,
        `${path}.${key}`,
        reject,
        ancestors,
      )
    }
  } finally {
    ancestors.delete(value)
  }
}

function assertJsonSafeArray(
  value: unknown[],
  path: string,
  reject: RejectSerializedValue,
  ancestors: Set<object>,
): void {
  if (Object.getPrototypeOf(value) !== Array.prototype) {
    reject(path, 'Expected a plain array')
  }
  const keys = Reflect.ownKeys(value)
  if (keys.length !== value.length + 1) {
    reject(path, 'Array must be dense and contain no custom properties')
  }
  for (const key of keys) {
    if (typeof key !== 'string') {
      reject(path, 'Array symbol properties are not allowed')
    }
    if (key === 'length') {
      continue
    }
    const index = Number(key)
    if (
      !Number.isInteger(index) ||
      index < 0 ||
      index >= value.length ||
      String(index) !== key
    ) {
      reject(path, 'Array contains a custom property')
    }
  }
  for (let index = 0; index < value.length; index += 1) {
    const itemPath = `${path}[${index}]`
    if (!Object.prototype.hasOwnProperty.call(value, index)) {
      reject(itemPath, 'Array item is missing')
    }
    const descriptor = expectEnumerableDataDescriptor(
      value,
      String(index),
      itemPath,
      reject,
    )
    assertJsonSafeValueWithAncestors(
      descriptor.value,
      itemPath,
      reject,
      ancestors,
    )
  }
}

function isPlainRecord(value: unknown): value is SerializedRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return false
  }
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

function expectEnumerableDataDescriptor(
  value: object,
  key: string,
  path: string,
  reject: RejectSerializedValue,
): PropertyDescriptor & { readonly value: unknown } {
  const descriptor = Object.getOwnPropertyDescriptor(value, key)
  if (
    descriptor === undefined ||
    !descriptor.enumerable ||
    !Object.prototype.hasOwnProperty.call(descriptor, 'value')
  ) {
    reject(path, 'Properties must be enumerable data values')
  }
  return descriptor as PropertyDescriptor & { readonly value: unknown }
}
