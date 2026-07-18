import { useEffect, useRef, useState } from 'react'
import type { PlayerId } from '../domain/ids'
import type { Player, Position, Team } from '../domain/league'
import { POSITIONS, formatTeamName } from '../domain/league'
import { getCategoryDefinition } from '../domain/detailedRatings'
import type {
  DetailedCategoryGroup,
  DetailedCategoryKey,
} from '../domain/detailedRatings'
import { ratingToGrade } from '../domain/ratings'
import {
  derivePositionProfile,
  deriveVersionedOverall,
} from '../domain/playerDerivations'
import {
  createRatingDisplayRows,
  formatPlayerName,
} from './leagueViewModel'
import type { RatingDisplayRow } from './leagueViewModel'
import { ComingLaterAction } from './playerSections'

export type PlayerPageTab = 'overview' | 'skills'

export interface PlayerPageContentProps {
  readonly player: Player
  readonly team: Team
  /** The player's team roster, for the left rail; clicking switches player. */
  readonly roster: readonly Player[]
  readonly busy: boolean
  readonly onBack: () => void
  readonly onSelectPlayer: (playerId: PlayerId) => void
  /** Dev/test convenience only; the tab is transient UI state. */
  readonly initialTab?: PlayerPageTab
}

/**
 * Display grouping of the 18 derived categories, from the taxonomy registry.
 * Overview shows letters only; the Skills tab is the letter accordion whose
 * real sub-ratings drop down on click.
 */
const SKILL_GROUPS: readonly DetailedCategoryGroup[] = [
  'scoring',
  'creation',
  'rebounding',
  'defense',
]
const PHYSICAL_GROUPS: readonly DetailedCategoryGroup[] = ['physical']
const MENTAL_GROUPS: readonly DetailedCategoryGroup[] = ['mental']

/**
 * The full player page — Alex's Court Dynasty reference imposed whole
 * (2026-07-17), in the hover quick view's visual language. Deltas from the
 * reference: **no badges** (we don't use badges — the Shooting Zones court
 * spans that whole area), **no Potential anywhere** (the stat cards shift
 * left), and every panel whose system doesn't exist yet shows an honest
 * "Coming later" absence instead of invented values. Real today: identity,
 * the roster rail, derived OVR + letter, the 18 letter grades, position fit,
 * and the derived Strengths/Concerns.
 */
export function PlayerPageContent({
  player,
  team,
  roster,
  busy,
  onBack,
  onSelectPlayer,
  initialTab = 'overview',
}: PlayerPageContentProps) {
  const [activeTab, setActiveTab] = useState<PlayerPageTab>(initialTab)
  const name = formatPlayerName(player)
  const overall = deriveVersionedOverall(player.ratings, player.primaryPosition)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const positionLabel =
    player.secondaryPosition === null
      ? player.primaryPosition
      : `${player.primaryPosition} / ${player.secondaryPosition}`

  useEffect(() => {
    headingRef.current?.focus()
  }, [player.id])

  return (
    <div className="player-page-shell">
      <PlayerPageRail
        roster={roster}
        team={team}
        currentPlayerId={player.id}
        busy={busy}
        onSelectPlayer={onSelectPlayer}
      />

      <section
        className="player-page"
        aria-labelledby="player-page-heading"
        aria-busy={busy}
      >
        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={busy}
        >
          Back to roster
        </button>

        <header className="player-page-hero">
          <div className="player-hero-identity">
            <span className="player-hero-jersey" aria-hidden="true">
              #{player.jerseyNumber}
            </span>
            <div>
              <p className="panel-kicker">Player</p>
              <h1 id="player-page-heading" ref={headingRef} tabIndex={-1}>
                {name}
              </h1>
              <p className="pqv-meta">
                {formatTeamName(team)} · {positionLabel} · Age {player.age}
              </p>
              {/* DEFERRED(later): height/weight/wingspan/handedness need player bio fields. */}
              <p className="pqv-meta player-hero-bio">
                Height — · Weight — · Wingspan — · Handedness —{' '}
                <span className="coming-later-marker">Coming later</span>
              </p>
            </div>
          </div>

          {/* DEFERRED(later): status/draft/college/agent/personality need their systems. */}
          <dl
            className="player-hero-profile"
            aria-label="Player profile details"
          >
            {[
              'Status',
              'Team Status',
              'Draft',
              'College',
              'Agent',
              'Personality',
              'Work Ethic',
            ].map((label) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>—</dd>
              </div>
            ))}
          </dl>

          {/* DEFERRED(later): the scouting quick summary needs a scouting/report system. */}
          <aside className="player-hero-summary" aria-label="Quick summary">
            <h4>
              Quick Summary{' '}
              <span className="coming-later-marker">Coming later</span>
            </h4>
            <p>A scouting summary arrives with the scouting system.</p>
          </aside>
        </header>

        <dl className="player-stat-cards">
          <div className="player-stat-card player-stat-card-real">
            <dt>OVR</dt>
            <dd>
              <span className="player-stat-card-value">{overall}</span>
              <span
                className={`grade-badge grade-${gradeClass(overall)}`}
                aria-label={`Overall letter grade ${ratingToGrade(overall)}`}
              >
                {ratingToGrade(overall)}
              </span>
            </dd>
          </div>
          {/* DEFERRED(later): the contract summary (years · total value) needs the financial model. */}
          <DeferredStatCard
            label="Contract"
            requirement="Years and total value arrive with the financial model."
          />
          {/* DEFERRED(later): health/morale/fatigue need the medical + morale systems. */}
          <DeferredStatCard
            label="Health"
            requirement="Availability arrives with the medical system."
          />
          <DeferredStatCard
            label="Morale"
            requirement="Morale arrives with the morale system."
          />
          <DeferredStatCard
            label="Fatigue"
            requirement="Fatigue arrives with the medical system."
          />
        </dl>

        <nav className="player-page-tabs" aria-label="Player page sections">
          <button
            type="button"
            className="player-tab"
            aria-current={activeTab === 'overview'}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            type="button"
            className="player-tab"
            aria-current={activeTab === 'skills'}
            onClick={() => setActiveTab('skills')}
          >
            Skills
          </button>
          {/* DEFERRED(§11): the Performance tab needs real per-game statistics. */}
          <DisabledTab
            label="Performance"
            requirement="Needs season statistics (§11)."
          />
          {/* DEFERRED(§8): the Role tab needs the rotation plan. */}
          <DisabledTab label="Role" requirement="Needs the rotation plan (§8)." />
          {/* DEFERRED(later): Contract and Career need their systems. */}
          <DisabledTab label="Contract" requirement="Needs the financial model." />
          <DisabledTab label="Career" requirement="Needs multi-season history." />
        </nav>

        {activeTab === 'overview' ? (
          <div className="player-overview-grid">
            <div className="player-overview-column">
              <PositionProfilesSection player={player} />
              <GradeListSection
                title="Physicals"
                player={player}
                groups={PHYSICAL_GROUPS}
              />
              <GradeListSection
                title="Mental"
                player={player}
                groups={MENTAL_GROUPS}
              />
            </div>
            <div className="player-overview-column">
              <SeasonStatsSection />
              <ShootingZonesSection />
            </div>
            <div className="player-overview-column">
              <GradeListSection
                title="Skill Breakdown"
                player={player}
                groups={SKILL_GROUPS}
              />
              <ConcernsStrengthsSection player={player} />
            </div>
          </div>
        ) : (
          <SkillsBreakdownTab player={player} />
        )}

        {/* DEFERRED(later): Compare / Trade Center / Watch / Edit need their systems. */}
        <div className="pqv-actions player-page-actions">
          <ComingLaterAction
            label="Compare Player"
            requirement="Player comparison arrives later."
          />
          <ComingLaterAction
            label="Trade Center"
            requirement="Trades arrive with the transaction system."
          />
          <ComingLaterAction
            label="Watch Player"
            requirement="The watchlist arrives later."
          />
          <ComingLaterAction
            label="Edit Player"
            requirement="Player editing arrives later."
          />
        </div>
      </section>
    </div>
  )
}

/** Left rail — the team roster (real data); clicking switches the open player. */
function PlayerPageRail({
  roster,
  team,
  currentPlayerId,
  busy,
  onSelectPlayer,
}: {
  readonly roster: readonly Player[]
  readonly team: Team
  readonly currentPlayerId: PlayerId
  readonly busy: boolean
  readonly onSelectPlayer: (playerId: PlayerId) => void
}) {
  return (
    <aside className="player-page-rail" aria-label="Team roster">
      <section className="player-page-card player-rail-roster">
        <p className="panel-kicker">{formatTeamName(team)}</p>
        <h4>Roster</h4>
        <ul className="player-rail-list">
          {roster.map((rosterPlayer) => {
            const overall = deriveVersionedOverall(
              rosterPlayer.ratings,
              rosterPlayer.primaryPosition,
            )
            const isCurrent = rosterPlayer.id === currentPlayerId

            return (
              <li key={rosterPlayer.id}>
                <button
                  type="button"
                  className="player-rail-button"
                  aria-current={isCurrent}
                  onClick={() => onSelectPlayer(rosterPlayer.id)}
                  disabled={busy}
                >
                  <span className="player-rail-pos">
                    {rosterPlayer.primaryPosition}
                  </span>
                  <span className="player-rail-name">
                    {formatPlayerName(rosterPlayer)}
                  </span>
                  <span
                    className={`grade-badge grade-${gradeClass(overall)}`}
                    aria-hidden="true"
                  >
                    {ratingToGrade(overall)}
                  </span>
                  <span className="player-rail-ovr">{overall}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      {/* DEFERRED(later): team chemistry needs a chemistry/morale system. */}
      <section className="player-page-card player-rail-chemistry">
        <h4>
          Team Chemistry <span className="coming-later-marker">Coming later</span>
        </h4>
        <p className="pqv-meta">
          Chemistry and its factors arrive with the morale system.
        </p>
      </section>
    </aside>
  )
}

function DeferredStatCard({
  label,
  requirement,
}: {
  readonly label: string
  readonly requirement: string
}) {
  return (
    <div className="player-stat-card" title={requirement}>
      <dt>
        {label} <span className="coming-later-marker">Coming later</span>
      </dt>
      <dd>—</dd>
    </div>
  )
}

function DisabledTab({
  label,
  requirement,
}: {
  readonly label: string
  readonly requirement: string
}) {
  return (
    <button type="button" className="player-tab" disabled title={requirement}>
      {label} <span className="coming-later-marker">Coming later</span>
    </button>
  )
}

/**
 * Position Profiles — all real (§8B R5): per-position Offense / Defense /
 * Overall letters derive from the versioned position-profile model; the fit
 * label comes from the player's natural/secondary positions. Letters only;
 * exact numbers live in each cell's title.
 */
function PositionProfilesSection({ player }: { readonly player: Player }) {
  return (
    <section
      className="pqv-section player-page-card"
      aria-label="Position profiles"
    >
      <h4>Position Profiles</h4>
      <div
        className="table-scroll"
        role="region"
        aria-label="Position profiles table"
        tabIndex={0}
      >
        <table className="ratings-table position-profiles-table">
          <caption className="visually-hidden">
            Per-position fit for {formatPlayerName(player)}
          </caption>
          <thead>
            <tr>
              <th scope="col">Pos</th>
              <th scope="col" title="Offense">
                Off
              </th>
              <th scope="col" title="Defense">
                Def
              </th>
              <th scope="col" title="Overall">
                Ovr
              </th>
              <th scope="col">Fit</th>
            </tr>
          </thead>
          <tbody>
            {POSITIONS.map((position) => {
              const profile = derivePositionProfile(player.ratings, position)
              return (
                <tr key={position}>
                  <th scope="row">{position}</th>
                  <ProfileGradeCell score={profile.offense} />
                  <ProfileGradeCell score={profile.defense} />
                  <ProfileGradeCell score={profile.overall} />
                  <td>{fitLabel(player, position)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="derived-note">
        Profiles derive from the versioned position-weight model (v1); never
        stored.
      </p>
    </section>
  )
}

function ProfileGradeCell({ score }: { readonly score: number }) {
  const grade = ratingToGrade(score)
  return (
    <td title={`Score ${score.toFixed(1)}`}>
      <span
        className={`grade-badge grade-${grade.charAt(0).toLowerCase()}`}
        aria-label={`Letter grade ${grade}`}
      >
        {grade}
      </span>
    </td>
  )
}

/** DEFERRED(§11): the season stat grid fills from the season-statistics fold. */
function SeasonStatsSection() {
  return (
    <section className="pqv-section player-page-card" aria-label="Season stats">
      <h4>
        Season Stats <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="season-stats-grid">
        {[
          'MIN',
          'PTS',
          'REB',
          'AST',
          'STL',
          'BLK',
          'FG%',
          '3P%',
          'FT%',
          'TS%',
          'USG%',
          'PER',
        ].map((label) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">
        Per-game stats arrive with the simulation and season statistics.
      </p>
    </section>
  )
}

/**
 * DEFERRED(§14): zone FG% needs shot locations from the possession event log.
 * The court spans the full area (no badges panel — we don't use badges).
 */
function ShootingZonesSection() {
  const zones = [
    { key: 'left-wing-3', label: 'Left 3' },
    { key: 'top-3', label: 'Top 3' },
    { key: 'right-wing-3', label: 'Right 3' },
    { key: 'left-mid', label: 'Left Mid' },
    { key: 'paint', label: 'Paint' },
    { key: 'right-mid', label: 'Right Mid' },
    { key: 'left-corner-3', label: 'Left Corner 3' },
    { key: 'free-throw', label: 'Free Throw' },
    { key: 'right-corner-3', label: 'Right Corner 3' },
  ] as const

  return (
    <section
      className="pqv-section player-page-card"
      aria-label="Shooting zones"
    >
      <h4>
        Shooting Zones (FG%){' '}
        <span className="coming-later-marker">Coming later</span>
      </h4>
      <dl className="shooting-zones-court">
        {zones.map((zone) => (
          <div key={zone.key} className="shooting-zone">
            <dd>—</dd>
            <dt>{zone.label}</dt>
          </div>
        ))}
      </dl>
      <p className="coming-later-requirement">
        Zone shooting fills from the shot locations in the possession event log
        (§14).
      </p>
    </section>
  )
}

/** Letters only — the numbers live in the Skills tab drilldown. */
function GradeListSection({
  title,
  player,
  groups,
}: {
  readonly title: string
  readonly player: Player
  readonly groups: readonly DetailedCategoryGroup[]
}) {
  const rows = gradeRows(player, groups)

  return (
    <section className="pqv-section player-page-card" aria-label={title}>
      <h4>{title}</h4>
      <ul className="grade-list">
        {rows.map((row) => (
          <li key={row.key}>
            <span className="grade-list-label">{row.label}</span>
            <span
              className={`grade-badge grade-${row.grade.charAt(0).toLowerCase()}`}
              aria-label={`Letter grade ${row.grade}`}
            >
              {row.grade}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * Strengths & Concerns — real today: derived from the stored ratings (the
 * best and worst graded categories). Display-only, never stored.
 */
function ConcernsStrengthsSection({ player }: { readonly player: Player }) {
  const ranked = [...createRatingDisplayRows(player.ratings)].sort(
    (first, second) => second.value - first.value,
  )
  const strengths = ranked.slice(0, 4)
  const concerns = ranked.slice(-4).reverse()

  return (
    <section
      className="pqv-section player-page-card"
      aria-label="Strengths and concerns"
    >
      <h4 className="concerns-heading">Concerns</h4>
      <ul className="grade-list concerns-list">
        {concerns.map((row) => (
          <li key={row.key}>
            <span className="grade-list-label">{row.label}</span>
            <span
              className={`grade-badge grade-${row.grade.charAt(0).toLowerCase()}`}
              aria-label={`Letter grade ${row.grade}`}
            >
              {row.grade}
            </span>
          </li>
        ))}
      </ul>
      <h4 className="strengths-heading">Strengths</h4>
      <ul className="grade-list strengths-list">
        {strengths.map((row) => (
          <li key={row.key}>
            <span className="grade-list-label">{row.label}</span>
            <span
              className={`grade-badge grade-${row.grade.charAt(0).toLowerCase()}`}
              aria-label={`Letter grade ${row.grade}`}
            >
              {row.grade}
            </span>
          </li>
        ))}
      </ul>
      <p className="coming-later-requirement">
        Derived from the current ratings; never stored.
      </p>
    </section>
  )
}

/**
 * The complete breakdown: every derived category as a letter; clicking a
 * letter drops its real stored sub-ratings down (the shared Rebound Reading
 * appears under both rebounding categories — 68 display slots for 67 stored
 * fields, per ADR 0008). Expansion is transient React state — never
 * persisted, never a save revision.
 */
function SkillsBreakdownTab({ player }: { readonly player: Player }) {
  const [expandedKeys, setExpandedKeys] = useState<
    ReadonlySet<DetailedCategoryKey>
  >(() => new Set())

  function toggle(key: DetailedCategoryKey): void {
    setExpandedKeys((current) => {
      const next = new Set(current)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  const groups = [
    { title: 'Skills', groups: SKILL_GROUPS },
    { title: 'Physicals', groups: PHYSICAL_GROUPS },
    { title: 'Mental', groups: MENTAL_GROUPS },
  ] as const

  return (
    <div className="player-page-sections">
      {groups.map((group) => (
        <section
          key={group.title}
          className="pqv-section player-page-card"
          aria-label={`${group.title} breakdown`}
        >
          <h4>{group.title}</h4>
          <ul className="grade-accordion">
            {gradeRows(player, group.groups).map((row) => {
              const isExpanded = expandedKeys.has(row.key)
              const panelId = `skill-panel-${row.key}`

              return (
                <li key={row.key}>
                  <button
                    type="button"
                    className="grade-accordion-toggle"
                    aria-expanded={isExpanded}
                    aria-controls={panelId}
                    onClick={() => toggle(row.key)}
                  >
                    <span className="grade-list-label">{row.label}</span>
                    <span
                      className={`grade-badge grade-${row.grade
                        .charAt(0)
                        .toLowerCase()}`}
                      aria-label={`Letter grade ${row.grade}`}
                    >
                      {row.grade}
                    </span>
                  </button>
                  {isExpanded && (
                    <dl
                      id={panelId}
                      className="grade-accordion-panel sub-rating-rows"
                    >
                      {getCategoryDefinition(row.key).subRatings.map(
                        (subRating) => (
                          <div key={subRating.key}>
                            <dt>{subRating.label}</dt>
                            <dd className="rating-value">
                              {player.ratings[subRating.key]}
                            </dd>
                          </div>
                        ),
                      )}
                    </dl>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}
      <p className="derived-note">
        Grades and category scores derive from the 67 stored sub-ratings and
        are never stored themselves.
      </p>
    </div>
  )
}

function gradeRows(
  player: Player,
  groups: readonly DetailedCategoryGroup[],
): readonly RatingDisplayRow[] {
  const wanted = new Set<DetailedCategoryGroup>(groups)
  return createRatingDisplayRows(player.ratings).filter((row) =>
    wanted.has(row.group),
  )
}

function gradeClass(rating: number): string {
  return ratingToGrade(rating).charAt(0).toLowerCase()
}

function fitLabel(player: Player, position: Position): string {
  if (position === player.primaryPosition) {
    return 'Natural'
  }
  if (position === player.secondaryPosition) {
    return 'Secondary'
  }
  return '—'
}
