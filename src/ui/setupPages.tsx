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
  readonly onDiscard?: () => void
}

export function RestoreRecoveryScreen({
  kind,
  message,
  actionError,
  isBusy,
  onTryAgain,
  onDiscard,
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
          {isInvalidSave && onDiscard !== undefined && (
            <button
              type="button"
              className="danger-button"
              onClick={onDiscard}
              disabled={isBusy}
            >
              {isBusy
                ? 'Removing saved league…'
                : 'Discard save and start new league'}
            </button>
          )}
        </div>
        {isInvalidSave && (
          <p className="recovery-note">
            The unreadable save remains untouched unless you explicitly discard
            it.
          </p>
        )}
      </section>
    </main>
  )
}

export interface LeagueCreationScreenProps {
  readonly seed: string
  readonly seedError: string | null
  readonly isBusy: boolean
  readonly onSeedChange: (seed: string) => void
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
  readonly onMainMenu: () => void
}

export function LeagueCreationScreen({
  seed,
  seedError,
  isBusy,
  onSeedChange,
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
          One seed creates eight fictional clubs and 96 explicit players. The
          generated league is saved locally before team selection begins.
        </p>

        <form
          id="league-creation-form"
          className="seed-form"
          onSubmit={onSubmit}
          aria-busy={isBusy}
          noValidate
        >
          <label htmlFor="league-seed">League seed</label>
          <div className="seed-controls">
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
            <button
              type="submit"
              className="form-submit-button"
              disabled={isBusy}
            >
              {isBusy ? 'Saving league…' : 'Generate league'}
            </button>
          </div>
          <p id="seed-help" className="field-help">
            Seeds are case-sensitive. No account or internet connection is used.
          </p>
          {seedError !== null && (
            <p id="seed-error" className="field-error" role="alert">
              {seedError}
            </p>
          )}
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
