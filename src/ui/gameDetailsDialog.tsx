import { useEffect, useId, useRef } from 'react'
import type { RefObject } from 'react'
import type { GameId } from '../domain/ids'
import type {
  GameDetailsTeamViewModel,
  GameDetailsViewModel,
} from '../app/teamScheduleViewModel'
import {
  formatScheduleDateLong,
  formatScheduledGameStatus,
  formatScheduleStage,
} from './scheduleFormatting'

export interface GameDetailsDialogProps {
  readonly details: GameDetailsViewModel | null
  readonly returnFocusRef: RefObject<HTMLButtonElement | null>
  readonly onSelectGame: (gameId: GameId) => void
  readonly onRequestClose: () => void
}

/**
 * Shared schedule-only game surface. It intentionally consumes the M2.6
 * GameDetailsViewModel so future Calendar entry points can reuse it without
 * interpreting ScheduledGame records in React.
 */
export function GameDetailsDialog({
  details,
  returnFocusRef,
  onSelectGame,
  onRequestClose,
}: GameDetailsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const wasOpenRef = useRef(false)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog === null) return

    if (details !== null) {
      wasOpenRef.current = true
      if (!dialog.open) dialog.showModal()
      return
    }

    if (dialog.open) dialog.close()
    if (wasOpenRef.current) {
      wasOpenRef.current = false
      const returnTarget = returnFocusRef.current
      window.requestAnimationFrame(() => returnTarget?.focus())
    }
  }, [details, returnFocusRef])

  useEffect(
    () => () => {
      const dialog = dialogRef.current
      if (dialog?.open) dialog.close()
    },
    [],
  )

  if (details === null) {
    return <dialog ref={dialogRef} className="game-details-dialog" />
  }

  const opponent = resolvePerspectiveOpponent(details)
  const previousGameId = details.previousPerspectiveGameId
  const nextGameId = details.nextPerspectiveGameId
  const perspectiveSite =
    details.perspectiveSite === null
      ? null
      : details.perspectiveSite === 'home'
        ? 'Home'
        : 'Away'

  return (
    <dialog
      ref={dialogRef}
      className="game-details-dialog"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      aria-modal="true"
      data-game-details={details.gameId}
      onCancel={(event) => {
        event.preventDefault()
        onRequestClose()
      }}
    >
      <div className="game-details-dialog-frame">
        <header className="game-details-header">
          <div>
            <p className="page-status">Game details</p>
            <h2 id={titleId}>
              {details.awayTeam.name} at {details.homeTeam.name}
            </h2>
            <p id={descriptionId}>
              Game day {details.gameDaySequence} · Meeting{' '}
              {details.meetingNumber}
            </p>
          </div>
          <button
            type="button"
            className="game-details-close"
            onClick={onRequestClose}
            autoFocus
            aria-label="Close game details"
          >
            Close
          </button>
        </header>

        <div className="game-details-body">
          <div className="game-details-matchup" aria-label="Matchup">
            <TeamIdentityCard label="Away team" team={details.awayTeam} />
            <span aria-hidden="true">at</span>
            <TeamIdentityCard label="Home team" team={details.homeTeam} />
          </div>

          <dl className="game-details-facts">
            <div>
              <dt>Status</dt>
              <dd>{formatScheduledGameStatus(details.status)}</dd>
            </div>
            <div>
              <dt>Competition stage</dt>
              <dd>{formatScheduleStage(details.competitionStage)}</dd>
            </div>
            <div>
              <dt>Placement date</dt>
              <dd>
                {details.placementDate === null ? (
                  'TBA'
                ) : (
                  <time dateTime={details.placementDate}>
                    {formatScheduleDateLong(details.placementDate)}
                  </time>
                )}
              </dd>
            </div>
            <div>
              <dt>Original scheduled date</dt>
              <dd>
                <time dateTime={details.originalScheduledDate}>
                  {formatScheduleDateLong(details.originalScheduledDate)}
                </time>
              </dd>
            </div>
            {details.currentScheduledDate !== null &&
              details.currentScheduledDate !==
                details.originalScheduledDate && (
                <div>
                  <dt>Current scheduled date</dt>
                  <dd>
                    <time dateTime={details.currentScheduledDate}>
                      {formatScheduleDateLong(
                        details.currentScheduledDate,
                      )}
                    </time>
                  </dd>
                </div>
              )}
            {details.actualDate !== null && (
              <div>
                <dt>Actual date</dt>
                <dd>
                  <time dateTime={details.actualDate}>
                    {formatScheduleDateLong(details.actualDate)}
                  </time>
                </dd>
              </div>
            )}
            {perspectiveSite !== null && (
              <div>
                <dt>Inspected-team site</dt>
                <dd>{perspectiveSite}</dd>
              </div>
            )}
            {opponent !== null && (
              <div>
                <dt>Opponent</dt>
                <dd>
                  {opponent.name} ({opponent.abbreviation})
                </dd>
              </div>
            )}
          </dl>

          {(details.isManagedTeamGame ||
            details.isPerspectiveTeamManaged) && (
            <div className="game-details-context" aria-label="Managed team context">
              {details.isPerspectiveTeamManaged
                ? 'Viewing from your managed team’s perspective.'
                : 'Your managed team participates in this game.'}
            </div>
          )}
        </div>

        <footer className="game-details-navigation">
          {previousGameId === null ? (
            <span className="game-details-boundary">
              First game in this team schedule
            </span>
          ) : (
            <button
              type="button"
              onClick={() => onSelectGame(previousGameId)}
            >
              Previous inspected-team game
            </button>
          )}
          {nextGameId === null ? (
            <span className="game-details-boundary">
              Final game in this team schedule
            </span>
          ) : (
            <button
              type="button"
              onClick={() => onSelectGame(nextGameId)}
            >
              Next inspected-team game
            </button>
          )}
        </footer>
      </div>
    </dialog>
  )
}

function TeamIdentityCard({
  label,
  team,
}: {
  readonly label: string
  readonly team: GameDetailsTeamViewModel
}) {
  return (
    <div className="game-details-team">
      <span>{label}</span>
      <strong>{team.name}</strong>
      <small>{team.abbreviation}</small>
    </div>
  )
}

function resolvePerspectiveOpponent(
  details: GameDetailsViewModel,
): GameDetailsTeamViewModel | null {
  if (details.opponentTeamId === null) return null
  if (details.homeTeam.teamId === details.opponentTeamId) {
    return details.homeTeam
  }
  if (details.awayTeam.teamId === details.opponentTeamId) {
    return details.awayTeam
  }
  throw new RangeError(
    `Game details opponent ${details.opponentTeamId} is not a participant`,
  )
}
