import { expect, vi } from 'vitest'

/**
 * Generation and seeded-randomness modules that read-side (app / UI /
 * persistence) code must never pull in for their runtime value. Kept as one
 * canonical list so every no-regeneration tripwire guards the same surface and
 * the guarded set cannot drift between test files.
 *
 * Paths are relative to this file. `tests/helpers` sits at the same `../../src`
 * depth as `tests/app`, `tests/ui`, and `tests/persistence`, and Vitest
 * resolves `vi.doMock` / `vi.doUnmock` specifiers relative to the file that
 * calls them — so these strings resolve to the same modules a consuming test
 * would mock inline.
 */
export const BANNED_GENERATION_MODULES = [
  '../../src/app/commands/createSeasonFoundation',
  '../../src/generation/generateSchedule',
  '../../src/generation/generateLeague',
  '../../src/domain/schedule',
  '../../src/random/xoshiro128ss',
] as const

type BannedModule = (typeof BANNED_GENERATION_MODULES)[number]

export type GenerationImportSpies = Record<BannedModule, ReturnType<typeof vi.fn>>

/**
 * Mocks every banned module with a spy that throws if the module is imported
 * for its runtime value, turning a purity regression into a hard failure.
 * (Type-only imports are erased and never trip it, which is intended.) Returns
 * the spies keyed by specifier. Call inside the test body, before importing the
 * module under test, and pair with {@link removeGenerationTripwires} in
 * afterEach.
 */
export function installGenerationTripwires(
  context: string,
): GenerationImportSpies {
  vi.resetModules()
  const spies = {} as GenerationImportSpies
  for (const specifier of BANNED_GENERATION_MODULES) {
    const spy = vi.fn()
    spies[specifier] = spy
    vi.doMock(specifier, () => {
      spy()
      throw new Error(`${context} imported ${specifier}`)
    })
  }
  return spies
}

/** Asserts that none of the tripwire spies fired. */
export function expectNoGenerationImports(spies: GenerationImportSpies): void {
  for (const specifier of BANNED_GENERATION_MODULES) {
    expect(spies[specifier]).not.toHaveBeenCalled()
  }
}

/**
 * Undoes the tripwires and resets the module registry. Call in afterEach. Also
 * usable by the importActual-style persistence guards, which mock the same
 * banned module set.
 */
export function removeGenerationTripwires(): void {
  for (const specifier of BANNED_GENERATION_MODULES) {
    vi.doUnmock(specifier)
  }
  vi.resetModules()
}
