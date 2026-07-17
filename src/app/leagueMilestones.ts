import {
  addDays,
  compareLocalDates,
  differenceInDays,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type { CalendarEventKind } from '../domain/seasonCalendar'

/**
 * A deterministically placed league-timeline event. These are derived, in the
 * app layer, from the authoritative regular-season opening and conclusion dates
 * — no simulation and no persistence. They can be promoted to authoritative
 * SeasonCalendar generation later without changing this contract.
 */
export interface LeagueMilestone {
  readonly kind: CalendarEventKind
  readonly title: string
  readonly date: LocalDate
}

interface MilestoneSpec {
  readonly kind: CalendarEventKind
  readonly title: string
  readonly anchor: 'season_fraction' | 'after_conclusion'
  readonly value: number
}

const MILESTONE_SPECS: readonly MilestoneSpec[] = [
  {
    kind: 'all_star_break',
    title: 'All-Star break',
    anchor: 'season_fraction',
    value: 0.5,
  },
  {
    kind: 'trade_deadline',
    title: 'Trade deadline',
    anchor: 'season_fraction',
    value: 0.62,
  },
  {
    kind: 'play_in_event',
    title: 'Play-In tournament',
    anchor: 'after_conclusion',
    value: 2,
  },
  {
    kind: 'playoffs_start',
    title: 'Playoffs begin',
    anchor: 'after_conclusion',
    value: 5,
  },
  {
    kind: 'finals_start',
    title: 'Finals begin',
    anchor: 'after_conclusion',
    value: 38,
  },
  {
    kind: 'draft_event',
    title: 'Draft',
    anchor: 'after_conclusion',
    value: 60,
  },
  {
    kind: 'free_agency_event',
    title: 'Free agency opens',
    anchor: 'after_conclusion',
    value: 66,
  },
]

/**
 * Places the league-timeline events between the regular-season opening and
 * conclusion, and in the following off-season, keeping every date inside the
 * supported LocalDate bounds. The result is sorted by date and frozen.
 */
export function deriveLeagueMilestones(
  regularSeasonOpening: LocalDate,
  regularSeasonConclusion: LocalDate,
): readonly LeagueMilestone[] {
  const opening = parseLocalDate(regularSeasonOpening)
  const conclusion = parseLocalDate(regularSeasonConclusion)
  const span = differenceInDays(opening, conclusion)
  if (span <= 0) return Object.freeze([])

  const milestones = MILESTONE_SPECS.flatMap((spec) => {
    const date =
      spec.anchor === 'season_fraction'
        ? safeAddDays(opening, Math.round(span * spec.value))
        : safeAddDays(conclusion, spec.value)
    return date === null
      ? []
      : [Object.freeze({ kind: spec.kind, title: spec.title, date })]
  })

  return Object.freeze(
    milestones.sort((left, right) => compareLocalDates(left.date, right.date)),
  )
}

/** The first milestone on or after the current date, or null if none remain. */
export function nextLeagueMilestone(
  milestones: readonly LeagueMilestone[],
  currentDate: LocalDate,
): LeagueMilestone | null {
  const validCurrentDate = parseLocalDate(currentDate)
  return (
    milestones.find(
      (milestone) => compareLocalDates(milestone.date, validCurrentDate) >= 0,
    ) ?? null
  )
}

function safeAddDays(date: LocalDate, amount: number): LocalDate | null {
  try {
    return addDays(date, amount)
  } catch {
    return null
  }
}
