import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  LeagueCreationScreen,
  RestoreRecoveryScreen,
  VersionMismatchScreen,
} from '../../src/ui/setupPages'
import type { SeasonSetupFormValues } from '../../src/ui/setupPages'

const SEASON_VALUES = Object.freeze({
  startingYear: '2026',
  regularSeasonStartDate: '2026-10-06',
  calendarDaySpacing: '3',
  scheduleSeed: 'visible-schedule-seed',
}) satisfies SeasonSetupFormValues

describe('LeagueCreationScreen season setup', () => {
  it('renders every controlled suggestion with an accessible label', () => {
    const markup = renderToStaticMarkup(
      <LeagueCreationScreen
        seed="visible-league-seed"
        seedError={null}
        seasonValues={SEASON_VALUES}
        seasonError={null}
        isBusy={false}
        onSeedChange={() => undefined}
        onSeasonValueChange={() => undefined}
        onSubmit={() => undefined}
        onMainMenu={() => undefined}
      />,
    )

    expect(markup).toContain('League seed')
    expect(markup).toContain('value="visible-league-seed"')
    expect(markup).toContain('Starting year')
    expect(markup).toContain('value="2026"')
    expect(markup).toContain('Regular-season start date')
    expect(markup).toContain('value="2026-10-06"')
    expect(markup).toContain('Days between game days')
    expect(markup).toContain('min="1"')
    expect(markup).toContain('value="3"')
    expect(markup).toContain('Schedule seed')
    expect(markup).toContain('value="visible-schedule-seed"')
    expect(markup).toContain(
      'These visible values become authoritative season creation metadata.',
    )
  })

  it('associates a season validation error with every season field', () => {
    const markup = renderToStaticMarkup(
      <LeagueCreationScreen
        seed="visible-league-seed"
        seedError={null}
        seasonValues={SEASON_VALUES}
        seasonError="Season inputs are invalid."
        isBusy={false}
        onSeedChange={() => undefined}
        onSeasonValueChange={() => undefined}
        onSubmit={() => undefined}
        onMainMenu={() => undefined}
      />,
    )

    expect(markup.match(/aria-invalid="true"/g)).toHaveLength(4)
    expect(markup).toContain('role="alert"')
    expect(markup).toContain('Season inputs are invalid.')
  })
})

describe('VersionMismatchScreen', () => {
  it('offers only an explicit start-new-league action for an older-build save', () => {
    const markup = renderToStaticMarkup(
      <VersionMismatchScreen
        actionError={null}
        isBusy={false}
        onStartNewLeague={() => undefined}
      />,
    )

    expect(markup).toContain('This league can')
    expect(markup).toContain(
      'This league was saved by an older build and can',
    )
    expect(markup).toContain('Start a new league')
    expect(markup).toContain('danger-button')
    expect(markup).toContain('permanently removes the incompatible saved')
    expect(markup).not.toContain('Migrate')
    expect(markup).not.toContain('leagueId')
    expect(markup).not.toContain('managedTeamId')
  })

  it('surfaces an action error and does not expose the corrupt-storage purge', () => {
    const markup = renderToStaticMarkup(
      <VersionMismatchScreen
        actionError="The league could not be removed in local browser storage. The last confirmed league was kept."
        isBusy={false}
        onStartNewLeague={() => undefined}
      />,
    )

    expect(markup).toContain('role="alert"')
    expect(markup).toContain(
      'The league could not be removed in local browser storage. The last confirmed league was kept.',
    )
    expect(markup).not.toContain('Permanently delete local league save')
  })
})

describe('RestoreRecoveryScreen', () => {
  it('exposes an explicit destructive purge only on the recovery screen', () => {
    const markup = renderToStaticMarkup(
      <RestoreRecoveryScreen
        kind="invalid-save"
        message="The authoritative save is invalid."
        actionError="The local league save could not be permanently deleted. Existing records remain, and you can retry."
        isBusy={false}
        onTryAgain={() => undefined}
        onPurgeCorruptStorage={() => undefined}
      />,
    )

    expect(markup).toContain('The authoritative save is invalid.')
    expect(markup).toContain('Try again')
    expect(markup).toContain('Permanently delete local league save')
    expect(markup).toContain('danger-button')
    expect(markup).toContain('the active local league record')
    expect(markup).toContain('cannot be undone')
    expect(markup).toContain('never falls back to an older save')
    expect(markup).toContain(
      'The local league save could not be permanently deleted. Existing records remain, and you can retry.',
    )
    expect(markup).toContain('role="alert"')
  })

  it('does not expose the corrupt-storage purge on non-recovery setup screens', () => {
    const creationMarkup = renderToStaticMarkup(
      <LeagueCreationScreen
        seed="visible-league-seed"
        seedError={null}
        seasonValues={SEASON_VALUES}
        seasonError={null}
        isBusy={false}
        onSeedChange={() => undefined}
        onSeasonValueChange={() => undefined}
        onSubmit={() => undefined}
        onMainMenu={() => undefined}
      />,
    )
    const mismatchMarkup = renderToStaticMarkup(
      <VersionMismatchScreen
        actionError={null}
        isBusy={false}
        onStartNewLeague={() => undefined}
      />,
    )

    expect(creationMarkup).not.toContain(
      'Permanently delete local league save',
    )
    expect(mismatchMarkup).not.toContain(
      'Permanently delete local league save',
    )
  })
})
