import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  LeagueCreationScreen,
  MigrationRequiredScreen,
  RestoreRecoveryScreen,
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

describe('MigrationRequiredScreen', () => {
  it('requests explicit inputs while promising to preserve V1', () => {
    const markup = renderToStaticMarkup(
      <MigrationRequiredScreen
        seasonValues={SEASON_VALUES}
        seasonError={null}
        actionError={null}
        isBusy={false}
        onSeasonValueChange={() => undefined}
        onMigrate={() => undefined}
        onTryAgain={() => undefined}
        onDiscard={() => undefined}
      />,
    )

    expect(markup).toContain('Complete the season foundation')
    expect(markup).toContain('valid version 1 league save')
    expect(markup).toContain('No year, date, spacing, or schedule seed')
    expect(markup).toContain('value="2026"')
    expect(markup).toContain('value="2026-10-06"')
    expect(markup).toContain('value="3"')
    expect(markup).toContain('value="visible-schedule-seed"')
    expect(markup).toContain('Migrate saved league')
    expect(markup).toContain('Try reading save again')
    expect(markup).toContain(
      'Discard version 1 save and start new league',
    )
    expect(markup).toContain('does not overwrite or delete the version 1 save')
    expect(markup).not.toContain('leagueId')
    expect(markup).not.toContain('managedTeamId')
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
    expect(markup).toContain('version 1 and version 2')
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
    const migrationMarkup = renderToStaticMarkup(
      <MigrationRequiredScreen
        seasonValues={SEASON_VALUES}
        seasonError={null}
        actionError={null}
        isBusy={false}
        onSeasonValueChange={() => undefined}
        onMigrate={() => undefined}
        onTryAgain={() => undefined}
        onDiscard={() => undefined}
      />,
    )

    expect(creationMarkup).not.toContain(
      'Permanently delete local league save',
    )
    expect(migrationMarkup).not.toContain(
      'Permanently delete local league save',
    )
  })
})
