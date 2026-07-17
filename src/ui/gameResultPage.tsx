import { useState } from 'react'
import type { GameResult, PlayerBoxScoreLine } from '../domain/gameResult'
import type { PlayerId } from '../domain/ids'
import type { Position, Team } from '../domain/league'
import { formatTeamName } from '../domain/league'
import {
  DNP_REASON_LABELS,
  deriveFourFactors,
  deriveTeamStatTotals,
  deriveTopPerformers,
  derivePercentage,
  formatFinalStatus,
  formatMinutes,
  formatPercentage,
  formatPeriodLabel,
  formatPlusMinus,
  formatShootingLine,
  groupBoxScoreLines,
} from '../app/gameResultViewModel'
import { ComingLaterPanel } from './comingLaterPanel'
import { SegmentedTabs } from './segmentedTabs'
import type { SegmentedTabOption } from './segmentedTabs'

export interface GameResultPlayerInfo {
  readonly name: string
  readonly position: Position
  readonly jerseyNumber: number
}

export interface GameResultPageProps {
  readonly result: GameResult
  readonly homeTeam: Team
  readonly awayTeam: Team
  readonly playerInfo: ReadonlyMap<PlayerId, GameResultPlayerInfo>
  /** Where this result came from, e.g. a design-fixture label. */
  readonly contextLabel: string
  readonly onBack?: () => void
}

type GameResultTab = 'overview' | 'team_stats' | 'play_by_play'

const GAME_RESULT_TABS: readonly SegmentedTabOption<GameResultTab>[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'team_stats', label: 'Team Stats' },
  { value: 'play_by_play', label: 'Play-by-Play', comingLater: true },
]

type BoxScoreView = 'both' | 'home' | 'away'

/**
 * The post-game workspace (§6). A pure function of one validated GameResult —
 * every number on screen is a fold over its box score. Anything that needs
 * play-by-play events, season context, or venue systems renders a Coming
 * later state instead of an invented value.
 *
 * DEFERRED(§11): team records next to the score header fill from standings.
 * DEFERRED(§14): the possession event log unlocks, all at once — the Game
 * Flow and Key Moments panels on Overview, the Play-by-Play tab (which also
 * carries the game summary), and largest lead / lead changes / times tied /
 * points off turnovers / points in paint on Team Stats.
 * DEFERRED(later): the Game Info panel (venue, attendance, referees, game
 * time) needs venue/officials systems not yet on the roadmap — schedule them
 * or consciously cut at §19. No fabricated value renders there until then.
 */
export function GameResultPage({
  result,
  homeTeam,
  awayTeam,
  playerInfo,
  contextLabel,
  onBack,
}: GameResultPageProps) {
  const [activeTab, setActiveTab] = useState<GameResultTab>('overview')
  const [boxScoreView, setBoxScoreView] = useState<BoxScoreView>('both')

  const homeTotals = deriveTeamStatTotals(result, result.homeTeamId)
  const awayTotals = deriveTeamStatTotals(result, result.awayTeamId)

  const boxScoreViewOptions: readonly SegmentedTabOption<BoxScoreView>[] = [
    { value: 'both', label: 'Both Teams' },
    { value: 'away', label: awayTeam.abbreviation },
    { value: 'home', label: homeTeam.abbreviation },
  ]

  return (
    <div className="game-result-page">
      <header className="game-result-header">
        {onBack !== undefined && (
          <button type="button" className="back-button" onClick={onBack}>
            Back
          </button>
        )}
        <p className="game-result-context">{contextLabel}</p>
        <div className="game-result-scoreline">
          <TeamScoreBlock
            team={awayTeam}
            points={result.away.totalPoints}
            winner={result.winnerTeamId === result.awayTeamId}
            side="away"
          />
          <div className="game-result-status">
            <strong>{formatFinalStatus(result.overtimePeriods)}</strong>
            <span className="home-card-deferred">
              Records &amp; venue{' '}
              <span className="coming-later-marker">Coming later</span>
            </span>
          </div>
          <TeamScoreBlock
            team={homeTeam}
            points={result.home.totalPoints}
            winner={result.winnerTeamId === result.homeTeamId}
            side="home"
          />
        </div>
        <PeriodLineTable
          result={result}
          homeTeam={homeTeam}
          awayTeam={awayTeam}
        />
      </header>

      <SegmentedTabs
        legend="Game views"
        name="game-result-tab"
        value={activeTab}
        options={GAME_RESULT_TABS}
        onChange={setActiveTab}
      />

      {activeTab === 'overview' && (
        <div className="game-result-overview">
          <section
            className="game-result-panel"
            aria-label="Top performers"
          >
            <h3>Top Performers</h3>
            <div className="game-result-performers">
              <TopPerformerList
                result={result}
                team={awayTeam}
                playerInfo={playerInfo}
              />
              <TopPerformerList
                result={result}
                team={homeTeam}
                playerInfo={playerInfo}
              />
            </div>
          </section>

          <div className="game-result-panel-row">
            <ComingLaterPanel
              title="Game Flow"
              requirement="Requires the scoring-run timeline from the simulation's event log."
            />
            <section className="game-result-panel" aria-label="Four factors">
              <h3>Four Factors</h3>
              <table className="league-table game-result-factors">
                <caption className="visually-hidden">
                  Four-factor comparison
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Factor</th>
                    <th scope="col">{awayTeam.abbreviation}</th>
                    <th scope="col">{homeTeam.abbreviation}</th>
                  </tr>
                </thead>
                <tbody>
                  {deriveFourFactors(homeTotals, awayTotals).map((row) => (
                    <tr key={row.label}>
                      <th scope="row">{row.label}</th>
                      <td
                        className={
                          row.leader === 'away' ? 'is-factor-leader' : undefined
                        }
                      >
                        {row.away}
                      </td>
                      <td
                        className={
                          row.leader === 'home' ? 'is-factor-leader' : undefined
                        }
                      >
                        {row.home}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <ComingLaterPanel
              title="Key Moments"
              requirement="Requires the simulation's play-by-play event log."
            />
            <ComingLaterPanel
              title="Game Info"
              requirement="Requires venue and officials systems."
            />
          </div>

          <section className="game-result-box-scores" aria-label="Box score">
            <SegmentedTabs
              legend="Box score teams"
              name="box-score-view"
              value={boxScoreView}
              options={boxScoreViewOptions}
              onChange={setBoxScoreView}
            />
            {boxScoreView !== 'home' && (
              <TeamBoxScoreTable
                result={result}
                team={awayTeam}
                playerInfo={playerInfo}
              />
            )}
            {boxScoreView !== 'away' && (
              <TeamBoxScoreTable
                result={result}
                team={homeTeam}
                playerInfo={playerInfo}
              />
            )}
          </section>
        </div>
      )}

      {activeTab === 'team_stats' && (
        <TeamStatsComparison
          homeTeam={homeTeam}
          awayTeam={awayTeam}
          homeTotals={homeTotals}
          awayTotals={awayTotals}
        />
      )}

      {activeTab === 'play_by_play' && (
        <ComingLaterPanel
          title="Play-by-Play, key moments, and game summary"
          requirement="Requires the simulation's possession event log."
        />
      )}
    </div>
  )
}

function TeamScoreBlock({
  team,
  points,
  winner,
  side,
}: {
  readonly team: Team
  readonly points: number
  readonly winner: boolean
  readonly side: 'home' | 'away'
}) {
  return (
    <div
      className={`game-result-team ${winner ? 'is-winner' : ''}`}
      data-side={side}
    >
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
      <div className="game-result-team-name">
        <strong>{formatTeamName(team)}</strong>
        <span>
          {team.abbreviation} · {side === 'home' ? 'Home' : 'Away'}
        </span>
      </div>
      <p className="game-result-points" data-winner={winner}>
        {points}
        {winner && <span className="visually-hidden"> (winner)</span>}
      </p>
    </div>
  )
}

function PeriodLineTable({
  result,
  homeTeam,
  awayTeam,
}: {
  readonly result: GameResult
  readonly homeTeam: Team
  readonly awayTeam: Team
}) {
  const periodCount = result.home.periodPoints.length

  return (
    <table className="league-table game-result-period-line">
      <caption className="visually-hidden">Scoring by period</caption>
      <thead>
        <tr>
          <th scope="col">Team</th>
          {Array.from({ length: periodCount }, (_, index) => (
            <th scope="col" key={index}>
              {formatPeriodLabel(index)}
            </th>
          ))}
          <th scope="col">T</th>
        </tr>
      </thead>
      <tbody>
        {(
          [
            [awayTeam, result.away] as const,
            [homeTeam, result.home] as const,
          ]
        ).map(([team, scoring]) => (
          <tr key={team.id}>
            <th scope="row">{team.abbreviation}</th>
            {scoring.periodPoints.map((points, index) => (
              <td key={index}>{points}</td>
            ))}
            <td className="game-result-period-total">{scoring.totalPoints}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function TopPerformerList({
  result,
  team,
  playerInfo,
}: {
  readonly result: GameResult
  readonly team: Team
  readonly playerInfo: ReadonlyMap<PlayerId, GameResultPlayerInfo>
}) {
  const performers = deriveTopPerformers(result, team.id, 2)

  return (
    <div className="game-result-performer-team">
      <h4>{formatTeamName(team)}</h4>
      <ul>
        {performers.map((line) => {
          const info = playerInfo.get(line.playerId)
          return (
            <li key={line.playerId}>
              <strong>{info?.name ?? line.playerId}</strong>
              <span>
                {line.points} PTS ·{' '}
                {line.offensiveRebounds + line.defensiveRebounds} REB ·{' '}
                {line.assists} AST ·{' '}
                {formatShootingLine(
                  line.fieldGoalsMade,
                  line.fieldGoalsAttempted,
                )}{' '}
                FG
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

const BOX_SCORE_COLUMNS = [
  'MIN',
  'FG',
  '3PT',
  'FT',
  'OREB',
  'DREB',
  'REB',
  'AST',
  'STL',
  'BLK',
  'TO',
  'PF',
  '+/-',
  'PTS',
] as const

function TeamBoxScoreTable({
  result,
  team,
  playerInfo,
}: {
  readonly result: GameResult
  readonly team: Team
  readonly playerInfo: ReadonlyMap<PlayerId, GameResultPlayerInfo>
}) {
  const groups = groupBoxScoreLines(result, team.id)
  const totals = deriveTeamStatTotals(result, team.id)

  return (
    <section
      className="game-result-box-score"
      aria-label={`${formatTeamName(team)} box score`}
    >
      <h3>{formatTeamName(team)}</h3>
      <div
        className="table-scroll"
        role="region"
        aria-label={`${formatTeamName(team)} box score table`}
        tabIndex={0}
      >
        <table className="league-table box-score-table">
          <caption className="visually-hidden">
            {formatTeamName(team)} player box score
          </caption>
          <thead>
            <tr>
              <th scope="col" className="box-score-player-column">
                Player
              </th>
              {BOX_SCORE_COLUMNS.map((column) => (
                <th scope="col" key={column}>
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <BoxScoreGroupRows
              label="Starters"
              lines={groups.starters}
              playerInfo={playerInfo}
            />
            <BoxScoreGroupRows
              label="Bench"
              lines={groups.bench}
              playerInfo={playerInfo}
            />
            {groups.didNotPlay.map((line) => {
              const info = playerInfo.get(line.playerId)
              return (
                <tr key={line.playerId} className="box-score-dnp-row">
                  <th scope="row" className="box-score-player-column">
                    <span className="player-name">
                      {info?.name ?? line.playerId}
                    </span>
                    {info !== undefined && (
                      <span className="box-score-position">
                        {info.position}
                      </span>
                    )}
                  </th>
                  <td colSpan={BOX_SCORE_COLUMNS.length}>
                    DNP —{' '}
                    {line.dnpReason === null
                      ? ''
                      : DNP_REASON_LABELS[line.dnpReason]}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="box-score-totals-row">
              <th scope="row" className="box-score-player-column">
                Totals
              </th>
              <td />
              <td>
                {formatShootingLine(
                  totals.fieldGoalsMade,
                  totals.fieldGoalsAttempted,
                )}
              </td>
              <td>
                {formatShootingLine(
                  totals.threePointersMade,
                  totals.threePointersAttempted,
                )}
              </td>
              <td>
                {formatShootingLine(
                  totals.freeThrowsMade,
                  totals.freeThrowsAttempted,
                )}
              </td>
              <td>{totals.offensiveRebounds}</td>
              <td>{totals.defensiveRebounds}</td>
              <td>{totals.totalRebounds}</td>
              <td>{totals.assists}</td>
              <td>{totals.steals}</td>
              <td>{totals.blocks}</td>
              <td>{totals.turnovers}</td>
              <td>{totals.personalFouls}</td>
              <td />
              <td className="game-result-period-total">{totals.points}</td>
            </tr>
            <tr className="box-score-shooting-row">
              <th scope="row" className="box-score-player-column">
                Shooting
              </th>
              <td />
              <td>
                {formatPercentage(
                  derivePercentage(
                    totals.fieldGoalsMade,
                    totals.fieldGoalsAttempted,
                  ),
                )}
              </td>
              <td>
                {formatPercentage(
                  derivePercentage(
                    totals.threePointersMade,
                    totals.threePointersAttempted,
                  ),
                )}
              </td>
              <td>
                {formatPercentage(
                  derivePercentage(
                    totals.freeThrowsMade,
                    totals.freeThrowsAttempted,
                  ),
                )}
              </td>
              <td colSpan={11} />
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}

function BoxScoreGroupRows({
  label,
  lines,
  playerInfo,
}: {
  readonly label: string
  readonly lines: readonly PlayerBoxScoreLine[]
  readonly playerInfo: ReadonlyMap<PlayerId, GameResultPlayerInfo>
}) {
  if (lines.length === 0) {
    return null
  }

  return (
    <>
      <tr className="box-score-group-row">
        <th
          scope="rowgroup"
          colSpan={BOX_SCORE_COLUMNS.length + 1}
          className="box-score-group-label"
        >
          {label}
        </th>
      </tr>
      {lines.map((line) => {
        const info = playerInfo.get(line.playerId)
        return (
          <tr key={line.playerId}>
            <th scope="row" className="box-score-player-column">
              <span className="player-name">{info?.name ?? line.playerId}</span>
              {info !== undefined && (
                <span className="box-score-position">{info.position}</span>
              )}
            </th>
            <td>{formatMinutes(line.secondsPlayed)}</td>
            <td>
              {formatShootingLine(
                line.fieldGoalsMade,
                line.fieldGoalsAttempted,
              )}
            </td>
            <td>
              {formatShootingLine(
                line.threePointersMade,
                line.threePointersAttempted,
              )}
            </td>
            <td>
              {formatShootingLine(line.freeThrowsMade, line.freeThrowsAttempted)}
            </td>
            <td>{line.offensiveRebounds}</td>
            <td>{line.defensiveRebounds}</td>
            <td>{line.offensiveRebounds + line.defensiveRebounds}</td>
            <td>{line.assists}</td>
            <td>{line.steals}</td>
            <td>{line.blocks}</td>
            <td>{line.turnovers}</td>
            <td>{line.personalFouls}</td>
            <td>{formatPlusMinus(line.plusMinus)}</td>
            <td className="box-score-points">{line.points}</td>
          </tr>
        )
      })}
    </>
  )
}

function TeamStatsComparison({
  homeTeam,
  awayTeam,
  homeTotals,
  awayTotals,
}: {
  readonly homeTeam: Team
  readonly awayTeam: Team
  readonly homeTotals: ReturnType<typeof deriveTeamStatTotals>
  readonly awayTotals: ReturnType<typeof deriveTeamStatTotals>
}) {
  const rows: readonly {
    readonly label: string
    readonly away: string
    readonly home: string
  }[] = [
    {
      label: 'Field goals',
      away: formatShootingLine(
        awayTotals.fieldGoalsMade,
        awayTotals.fieldGoalsAttempted,
      ),
      home: formatShootingLine(
        homeTotals.fieldGoalsMade,
        homeTotals.fieldGoalsAttempted,
      ),
    },
    {
      label: 'FG%',
      away: formatPercentage(
        derivePercentage(
          awayTotals.fieldGoalsMade,
          awayTotals.fieldGoalsAttempted,
        ),
      ),
      home: formatPercentage(
        derivePercentage(
          homeTotals.fieldGoalsMade,
          homeTotals.fieldGoalsAttempted,
        ),
      ),
    },
    {
      label: 'Three pointers',
      away: formatShootingLine(
        awayTotals.threePointersMade,
        awayTotals.threePointersAttempted,
      ),
      home: formatShootingLine(
        homeTotals.threePointersMade,
        homeTotals.threePointersAttempted,
      ),
    },
    {
      label: '3PT%',
      away: formatPercentage(
        derivePercentage(
          awayTotals.threePointersMade,
          awayTotals.threePointersAttempted,
        ),
      ),
      home: formatPercentage(
        derivePercentage(
          homeTotals.threePointersMade,
          homeTotals.threePointersAttempted,
        ),
      ),
    },
    {
      label: 'Free throws',
      away: formatShootingLine(
        awayTotals.freeThrowsMade,
        awayTotals.freeThrowsAttempted,
      ),
      home: formatShootingLine(
        homeTotals.freeThrowsMade,
        homeTotals.freeThrowsAttempted,
      ),
    },
    {
      label: 'FT%',
      away: formatPercentage(
        derivePercentage(
          awayTotals.freeThrowsMade,
          awayTotals.freeThrowsAttempted,
        ),
      ),
      home: formatPercentage(
        derivePercentage(
          homeTotals.freeThrowsMade,
          homeTotals.freeThrowsAttempted,
        ),
      ),
    },
    {
      label: 'Rebounds',
      away: String(awayTotals.totalRebounds),
      home: String(homeTotals.totalRebounds),
    },
    {
      label: 'Offensive rebounds',
      away: String(awayTotals.offensiveRebounds),
      home: String(homeTotals.offensiveRebounds),
    },
    {
      label: 'Assists',
      away: String(awayTotals.assists),
      home: String(homeTotals.assists),
    },
    {
      label: 'Steals',
      away: String(awayTotals.steals),
      home: String(homeTotals.steals),
    },
    {
      label: 'Blocks',
      away: String(awayTotals.blocks),
      home: String(homeTotals.blocks),
    },
    {
      label: 'Turnovers',
      away: String(awayTotals.turnovers),
      home: String(homeTotals.turnovers),
    },
    {
      label: 'Personal fouls',
      away: String(awayTotals.personalFouls),
      home: String(homeTotals.personalFouls),
    },
    {
      label: 'Points',
      away: String(awayTotals.points),
      home: String(homeTotals.points),
    },
  ]

  return (
    <section className="game-result-panel" aria-label="Team comparison">
      <h3>Team Comparison</h3>
      <table className="league-table game-result-team-stats">
        <caption className="visually-hidden">Team statistics comparison</caption>
        <thead>
          <tr>
            <th scope="col">Statistic</th>
            <th scope="col">{awayTeam.abbreviation}</th>
            <th scope="col">{homeTeam.abbreviation}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{row.away}</td>
              <td>{row.home}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="home-card-deferred">
        Largest lead, lead changes, and points off turnovers{' '}
        <span className="coming-later-marker">Coming later</span>
      </p>
    </section>
  )
}
