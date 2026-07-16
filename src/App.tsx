import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { PlayerId, TeamId } from './domain/ids'
import type { League, Player, Team } from './domain/league'
import { generateLeague } from './generation/generateLeague'
import { normalizeSeed } from './random/seed'
import {
  createRatingDisplayRows,
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from './ui/leagueViewModel'
import './App.css'

const DEFAULT_LEAGUE_SEED = 'stone-league-1'

function App() {
  const [seed, setSeed] = useState(DEFAULT_LEAGUE_SEED)
  const [league, setLeague] = useState<League | null>(null)
  const [selectedTeamId, setSelectedTeamId] = useState<TeamId | null>(null)
  const [selectedPlayerId, setSelectedPlayerId] = useState<PlayerId | null>(null)
  const [seedError, setSeedError] = useState<string | null>(null)

  const selectedTeam =
    league?.teams.find((team) => team.id === selectedTeamId) ?? null
  const roster =
    league !== null && selectedTeam !== null
      ? getTeamRoster(league, selectedTeam.id)
      : []
  const selectedPlayer =
    roster.find((player) => player.id === selectedPlayerId) ?? roster[0] ?? null

  function handleGenerate(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()

    try {
      const normalizedSeed = normalizeSeed(seed)
      const generatedLeague = generateLeague(normalizedSeed)
      setSeed(normalizedSeed)
      setLeague(generatedLeague)
      setSelectedTeamId(null)
      setSelectedPlayerId(null)
      setSeedError(null)
    } catch (error) {
      setSeedError(
        error instanceof Error
          ? error.message
          : 'The league could not be generated from that seed.',
      )
    }
  }

  function handleSeedChange(nextSeed: string): void {
    setSeed(nextSeed)
    setSeedError(null)
  }

  function handleTeamSelection(team: Team): void {
    if (league === null) return

    const teamRoster = getTeamRoster(league, team.id)
    setSelectedTeamId(team.id)
    setSelectedPlayerId(teamRoster[0]?.id ?? null)
  }

  function handleBackToTeams(): void {
    setSelectedTeamId(null)
    setSelectedPlayerId(null)
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            S
          </span>
          <span>
            <span className="brand-name">Stone Basketball GM</span>
            <span className="brand-subtitle">Fictional league workshop</span>
          </span>
        </div>
        <span className="mode-badge">Read-only preview</span>
      </header>

      <main>
        {league === null ? (
          <LeagueCreationScreen
            seed={seed}
            seedError={seedError}
            onSeedChange={handleSeedChange}
            onSubmit={handleGenerate}
          />
        ) : selectedTeam === null ? (
          <TeamSelectionScreen
            league={league}
            seed={seed}
            onSelectTeam={handleTeamSelection}
          />
        ) : (
          <RosterScreen
            team={selectedTeam}
            roster={roster}
            selectedPlayer={selectedPlayer}
            onSelectPlayer={setSelectedPlayerId}
            onBack={handleBackToTeams}
          />
        )}
      </main>

      <footer className="site-footer">
        Generated locally from a deterministic seed. Nothing is saved yet.
      </footer>
    </div>
  )
}

interface LeagueCreationScreenProps {
  readonly seed: string
  readonly seedError: string | null
  readonly onSeedChange: (seed: string) => void
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

function LeagueCreationScreen({
  seed,
  seedError,
  onSeedChange,
  onSubmit,
}: LeagueCreationScreenProps) {
  const seedDescriptionId = seedError === null ? 'seed-help' : 'seed-help seed-error'

  return (
    <section className="creation-layout" aria-labelledby="creation-heading">
      <div className="creation-copy">
        <p className="eyebrow">Milestone 1 · League lab</p>
        <h1 id="creation-heading">Build a league worth scouting.</h1>
        <p className="lede">
          One seed creates eight fictional clubs and 96 players. Reuse the seed
          whenever you want the exact same league again.
        </p>

        <form className="seed-form" onSubmit={onSubmit} noValidate>
          <label htmlFor="league-seed">League seed</label>
          <div className="seed-controls">
            <input
              id="league-seed"
              name="leagueSeed"
              type="text"
              value={seed}
              onChange={(event) => onSeedChange(event.target.value)}
              aria-describedby={seedDescriptionId}
              aria-invalid={seedError !== null}
              autoComplete="off"
              spellCheck={false}
            />
            <button type="submit" className="primary-button">
              Generate league
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
        <p className="summary-kicker">Every generated league includes</p>
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
            <dd>16 skills per player</dd>
          </div>
        </dl>
      </aside>
    </section>
  )
}

interface TeamSelectionScreenProps {
  readonly league: League
  readonly seed: string
  readonly onSelectTeam: (team: Team) => void
}

function TeamSelectionScreen({
  league,
  seed,
  onSelectTeam,
}: TeamSelectionScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <section className="content-section" aria-labelledby="team-selection-heading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">League generated · {league.seedFingerprint}</p>
          <h1 id="team-selection-heading" ref={headingRef} tabIndex={-1}>
            Choose your front office.
          </h1>
          <p className="section-intro">
            Eight fictional teams were generated from <strong>{seed}</strong>.
            Select one to inspect its roster.
          </p>
        </div>
        <span className="count-badge">8 teams</span>
      </div>

      <ul className="team-grid" aria-label="Generated teams">
        {league.teams.map((team) => (
          <li key={team.id}>
            <button
              type="button"
              className="team-card"
              onClick={() => onSelectTeam(team)}
              aria-label={`Manage ${formatTeamName(team)}`}
              style={{ borderTopColor: team.colors.secondary }}
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
                <span className="team-action">Inspect roster →</span>
              </span>
              <span className="team-swatches" aria-hidden="true">
                <span style={{ backgroundColor: team.colors.primary }} />
                <span style={{ backgroundColor: team.colors.secondary }} />
                <span style={{ backgroundColor: team.colors.accent }} />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

interface RosterScreenProps {
  readonly team: Team
  readonly roster: readonly Player[]
  readonly selectedPlayer: Player | null
  readonly onSelectPlayer: (playerId: PlayerId) => void
  readonly onBack: () => void
}

function RosterScreen({
  team,
  roster,
  selectedPlayer,
  onSelectPlayer,
  onBack,
}: RosterScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <section className="content-section roster-section" aria-labelledby="roster-heading">
      <button type="button" className="back-button" onClick={onBack}>
        ← Back to team selection
      </button>

      <div className="team-identity-panel">
        <span
          className="large-team-mark"
          aria-hidden="true"
          style={{
            backgroundColor: team.colors.primary,
            borderColor: team.colors.secondary,
          }}
        >
          {team.mark.text}
        </span>
        <div>
          <p className="eyebrow">Your selected team · {team.abbreviation}</p>
          <h1 id="roster-heading" ref={headingRef} tabIndex={-1}>
            {formatTeamName(team)}
          </h1>
          <p className="section-intro">
            Review the 12-player roster. Select a player to inspect every stored
            rating and its derived grade.
          </p>
        </div>
      </div>

      <div className="roster-layout">
        <div className="roster-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Active roster</p>
              <h2>Players</h2>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>

          <div className="table-scroll">
            <table className="roster-table">
              <caption className="visually-hidden">
                {formatTeamName(team)} player roster
              </caption>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">Position</th>
                  <th scope="col">Age</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((player) => {
                  const isSelected = player.id === selectedPlayer?.id
                  const playerName = formatPlayerName(player)

                  return (
                    <tr key={player.id} className={isSelected ? 'is-selected' : undefined}>
                      <th scope="row">
                        <span className="player-name">{playerName}</span>
                        <span className="jersey-number">#{player.jerseyNumber}</span>
                      </th>
                      <td>{player.primaryPosition}</td>
                      <td>{player.age}</td>
                      <td>
                        <button
                          type="button"
                          className="player-detail-button"
                          onClick={() => onSelectPlayer(player.id)}
                          aria-pressed={isSelected}
                          aria-controls="player-details"
                        >
                          {isSelected ? 'Viewing' : 'View ratings'}
                          <span className="visually-hidden"> for {playerName}</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {selectedPlayer !== null && <PlayerDetails player={selectedPlayer} />}
      </div>
    </section>
  )
}

function PlayerDetails({ player }: { readonly player: Player }) {
  const ratingRows = createRatingDisplayRows(player.ratings)

  return (
    <aside
      id="player-details"
      className="player-details"
      aria-labelledby="player-details-heading"
    >
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Showing ratings for {formatPlayerName(player)}
      </p>
      <div className="player-details-header">
        <div>
          <p className="panel-kicker">Player ratings</p>
          <h2 id="player-details-heading">{formatPlayerName(player)}</h2>
          <p>
            #{player.jerseyNumber} · {player.primaryPosition} · Age {player.age}
          </p>
        </div>
        <span className="rating-scale">0–100</span>
      </div>

      <div className="table-scroll">
        <table className="ratings-table">
          <caption className="visually-hidden">
            All stored ratings for {formatPlayerName(player)}
          </caption>
          <thead>
            <tr>
              <th scope="col">Rating</th>
              <th scope="col">Value</th>
              <th scope="col">Grade</th>
            </tr>
          </thead>
          <tbody>
            {ratingRows.map((rating) => (
              <tr key={rating.key}>
                <th scope="row">{rating.label}</th>
                <td className="rating-value">{rating.value}</td>
                <td>
                  <span
                    className={`grade-badge grade-${rating.grade.charAt(0).toLowerCase()}`}
                    aria-label={`Letter grade ${rating.grade}`}
                  >
                    {rating.grade}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="derived-note">
        Letter grades are derived from the numeric rating and are never stored.
      </p>
    </aside>
  )
}

function useFocusOnMount() {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return headingRef
}

export default App
