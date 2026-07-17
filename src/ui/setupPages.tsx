import { useEffect, useRef } from 'react'
import type { FormEvent } from 'react'
import type { TeamId } from '../domain/ids'
import type { League, Team } from '../domain/league'
import { formatTeamName } from './leagueViewModel'

export function RestoreLoadingScreen() {
  return (
    <main className="standalone-state" aria-busy="true">
      <section className="state-panel" aria-labelledby="restore-loading-heading">
        <p className="eyebrow">Local league</p>
        <h1 id="restore-loading-heading">Opening your front office</h1>
        <p className="lede" role="status">
          Checking this browser for a saved league…
        </p>
      </section>
    </main>
  )
}

export interface RestoreRecoveryScreenProps {
  readonly kind: 'invalid-save' | 'storage-error'
  readonly message: string
  readonly actionError: string | null
  readonly isBusy: boolean
  readonly onTryAgain: () => void
  readonly onPurgeCorruptStorage: () => void
}

export function RestoreRecoveryScreen({
  kind,
  message,
  actionError,
  isBusy,
  onTryAgain,
  onPurgeCorruptStorage,
}: RestoreRecoveryScreenProps) {
  const headingRef = useFocusOnMount()
  const isInvalidSave = kind === 'invalid-save'

  return (
    <main className="standalone-state" aria-busy={isBusy}>
      <section
        className="state-panel recovery-panel"
        aria-labelledby="restore-recovery-heading"
      >
        <p className="eyebrow">Local save needs attention</p>
        <h1 id="restore-recovery-heading" ref={headingRef} tabIndex={-1}>
          {isInvalidSave
            ? 'We could not open your saved league'
            : 'Local storage is not available'}
        </h1>
        <p className="lede">{message}</p>
        {actionError !== null && (
          <p className="recovery-error" role="alert">
            {actionError}
          </p>
        )}
        <div className="recovery-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={onTryAgain}
            disabled={isBusy}
          >
            Try again
          </button>
          <button
            type="button"
            className="danger-button"
            onClick={onPurgeCorruptStorage}
            disabled={isBusy}
          >
            {isBusy
              ? 'Deleting local league save…'
              : 'Permanently delete local league save'}
          </button>
        </div>
        <p className="recovery-note">
          This destructive recovery action permanently removes the active local
          league record. It cannot be undone and never falls back to an older
          save.
        </p>
      </section>
    </main>
  )
}

export interface SeasonSetupFormValues {
  readonly startingYear: string
  readonly regularSeasonStartDate: string
  readonly calendarDaySpacing: string
  readonly scheduleSeed: string
}

export type SeasonSetupFormField = keyof SeasonSetupFormValues

interface SeasonSetupFieldsProps {
  readonly idPrefix: string
  readonly values: SeasonSetupFormValues
  readonly error: string | null
  readonly isBusy: boolean
  readonly onChange: (field: SeasonSetupFormField, value: string) => void
}

export interface LeagueCreationScreenProps {
  readonly seed: string
  readonly seedError: string | null
  readonly seasonValues: SeasonSetupFormValues
  readonly seasonError: string | null
  readonly isBusy: boolean
  readonly onSeedChange: (seed: string) => void
  readonly onSeasonValueChange: (
    field: SeasonSetupFormField,
    value: string,
  ) => void
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
  readonly onMainMenu: () => void
}

export function LeagueCreationScreen({
  seed,
  seedError,
  seasonValues,
  seasonError,
  isBusy,
  onSeedChange,
  onSeasonValueChange,
  onSubmit,
  onMainMenu,
}: LeagueCreationScreenProps) {
  const headingRef = useFocusOnMount()
  const seedDescriptionId =
    seedError === null ? 'seed-help' : 'seed-help seed-error'

  return (
    <section className="setup-page creation-layout" aria-labelledby="creation-heading">
      <div className="creation-copy">
        <button
          type="button"
          className="text-button"
          onClick={onMainMenu}
          disabled={isBusy}
        >
          ← Dashboard overview
        </button>
        <p className="eyebrow">League setup</p>
        <h1 id="creation-heading" ref={headingRef} tabIndex={-1}>
          Create a fictional league
        </h1>
        <p className="lede">
          One seed creates eight fictional clubs and 96 explicit players. You
          also approve the exact inputs used to create the initial regular
          season before anything is saved.
        </p>

        <form
          id="league-creation-form"
          className="seed-form"
          onSubmit={onSubmit}
          aria-busy={isBusy}
          noValidate
        >
          <div className="setup-field">
            <label htmlFor="league-seed">League seed</label>
            <input
              id="league-seed"
              name="leagueSeed"
              type="text"
              value={seed}
              onChange={(event) => onSeedChange(event.currentTarget.value)}
              aria-describedby={seedDescriptionId}
              aria-invalid={seedError !== null}
              autoComplete="off"
              spellCheck={false}
              disabled={isBusy}
            />
            <p id="seed-help" className="field-help">
              The displayed seed deterministically creates the fictional league.
              No account or internet connection is used.
            </p>
            {seedError !== null && (
              <p id="seed-error" className="field-error" role="alert">
                {seedError}
              </p>
            )}
          </div>

          <SeasonSetupFields
            idPrefix="new-league-season"
            values={seasonValues}
            error={seasonError}
            isBusy={isBusy}
            onChange={onSeasonValueChange}
          />

          <div className="setup-submit-row">
            <button
              type="submit"
              className="form-submit-button"
              disabled={isBusy}
            >
              {isBusy ? 'Saving league…' : 'Generate league'}
            </button>
          </div>
        </form>
      </div>

      <aside className="creation-summary" aria-label="Generated league contents">
        <div className="court-mark" aria-hidden="true">
          <span>8</span>
        </div>
        <p className="summary-kicker">Generated locally</p>
        <dl className="league-facts">
          <div>
            <dt>Teams</dt>
            <dd>8 fictional clubs</dd>
          </div>
          <div>
            <dt>Players</dt>
            <dd>12 per roster</dd>
          </div>
          <div>
            <dt>Ratings</dt>
            <dd>16 stored skills</dd>
          </div>
        </dl>
      </aside>
    </section>
  )
}

export interface VersionMismatchScreenProps {
  readonly actionError: string | null
  readonly isBusy: boolean
  readonly onStartNewLeague: () => void
}

/**
 * Shown when local storage holds a league written by an older build. There are
 * no migrations before 1.0, so the only path forward is an explicit,
 * confirmed clear followed by the normal create-league flow. The stale record
 * is never overwritten silently — the player must click the button.
 */
export function VersionMismatchScreen({
  actionError,
  isBusy,
  onStartNewLeague,
}: VersionMismatchScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <main className="standalone-state" aria-busy={isBusy}>
      <section
        className="state-panel version-mismatch-panel"
        aria-labelledby="version-mismatch-heading"
      >
        <p className="eyebrow">Local save incompatible</p>
        <h1 id="version-mismatch-heading" ref={headingRef} tabIndex={-1}>
          This league can&rsquo;t be opened
        </h1>
        <p className="lede">
          This league was saved by an older build and can&rsquo;t be opened.
          Start a new league to continue.
        </p>
        {actionError !== null && (
          <p className="recovery-error" role="alert">
            {actionError}
          </p>
        )}
        <div className="recovery-actions">
          <button
            type="button"
            className="danger-button"
            onClick={onStartNewLeague}
            disabled={isBusy}
          >
            {isBusy
              ? 'Removing the old league…'
              : 'Start a new league'}
          </button>
        </div>
        <p className="recovery-note">
          Starting a new league permanently removes the incompatible saved
          record. It cannot be undone.
        </p>
      </section>
    </main>
  )
}

function SeasonSetupFields({
  idPrefix,
  values,
  error,
  isBusy,
  onChange,
}: SeasonSetupFieldsProps) {
  const helpId = `${idPrefix}-help`
  const errorId = `${idPrefix}-error`
  const describedBy = error === null ? helpId : `${helpId} ${errorId}`

  return (
    <fieldset className="season-setup-fields" disabled={isBusy}>
      <legend>Regular-season setup</legend>
      <p id={helpId} className="field-help">
        These visible values become authoritative season creation metadata.
      </p>
      <div className="season-setup-grid">
        <div className="setup-field">
          <label htmlFor={`${idPrefix}-starting-year`}>Starting year</label>
          <input
            id={`${idPrefix}-starting-year`}
            name="startingYear"
            type="number"
            min="0"
            max="9998"
            step="1"
            inputMode="numeric"
            value={values.startingYear}
            onChange={(event) =>
              onChange('startingYear', event.currentTarget.value)
            }
            aria-describedby={describedBy}
            aria-invalid={error !== null}
          />
        </div>
        <div className="setup-field">
          <label htmlFor={`${idPrefix}-start-date`}>
            Regular-season start date
          </label>
          <input
            id={`${idPrefix}-start-date`}
            name="regularSeasonStartDate"
            type="date"
            value={values.regularSeasonStartDate}
            onChange={(event) =>
              onChange('regularSeasonStartDate', event.currentTarget.value)
            }
            aria-describedby={describedBy}
            aria-invalid={error !== null}
          />
        </div>
        <div className="setup-field">
          <label htmlFor={`${idPrefix}-day-spacing`}>
            Days between game days
          </label>
          <input
            id={`${idPrefix}-day-spacing`}
            name="calendarDaySpacing"
            type="number"
            min="1"
            step="1"
            inputMode="numeric"
            value={values.calendarDaySpacing}
            onChange={(event) =>
              onChange('calendarDaySpacing', event.currentTarget.value)
            }
            aria-describedby={describedBy}
            aria-invalid={error !== null}
          />
        </div>
        <div className="setup-field">
          <label htmlFor={`${idPrefix}-schedule-seed`}>Schedule seed</label>
          <input
            id={`${idPrefix}-schedule-seed`}
            name="scheduleSeed"
            type="text"
            value={values.scheduleSeed}
            onChange={(event) =>
              onChange('scheduleSeed', event.currentTarget.value)
            }
            aria-describedby={describedBy}
            aria-invalid={error !== null}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
      </div>
      {error !== null && (
        <p id={errorId} className="field-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  )
}

export interface TeamSelectionScreenProps {
  readonly league: League
  readonly seed: string
  readonly controlledTeamId: TeamId | null
  readonly isBusy: boolean
  readonly onSelectTeam: (team: Team) => void
  readonly onMainMenu: () => void
}

export function TeamSelectionScreen({
  league,
  seed,
  controlledTeamId,
  isBusy,
  onSelectTeam,
  onMainMenu,
}: TeamSelectionScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <section
      className="setup-page team-selection-page"
      aria-labelledby="team-selection-heading"
      aria-busy={isBusy}
    >
      <button
        type="button"
        className="text-button"
        onClick={onMainMenu}
        disabled={isBusy}
      >
        ← Dashboard overview
      </button>
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">League setup · {league.seedFingerprint}</p>
          <h1 id="team-selection-heading" ref={headingRef} tabIndex={-1}>
            Choose your front office
          </h1>
          <p className="section-intro">
            Eight fictional teams were generated from <strong>{seed}</strong>.
            Choose the team you control; the selection is saved locally.
          </p>
        </div>
        <span className="count-badge">{league.teams.length} teams</span>
      </div>

      <ul className="team-grid" aria-label="Generated teams">
        {league.teams.map((team) => {
          const isControlled = team.id === controlledTeamId

          return (
            <li key={team.id}>
              <button
                type="button"
                className="team-card"
                data-team-choice
                onClick={() => onSelectTeam(team)}
                aria-label={`${isControlled ? 'Continue with' : 'Manage'} ${formatTeamName(team)}`}
                style={{ borderTopColor: team.colors.secondary }}
                disabled={isBusy}
              >
                <span
                  className="team-card-mark"
                  aria-hidden="true"
                  style={{ backgroundColor: team.colors.primary }}
                >
                  {team.mark.text}
                </span>
                <span className="team-card-copy">
                  <span className="team-city">{team.city}</span>
                  <span className="team-nickname">{team.nickname}</span>
                  <span className="team-action">
                    {isControlled ? 'Current team · Open roster' : 'Choose team'}
                  </span>
                </span>
                <span className="team-swatches" aria-hidden="true">
                  <span style={{ backgroundColor: team.colors.primary }} />
                  <span style={{ backgroundColor: team.colors.secondary }} />
                  <span style={{ backgroundColor: team.colors.accent }} />
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function useFocusOnMount() {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return headingRef
}
