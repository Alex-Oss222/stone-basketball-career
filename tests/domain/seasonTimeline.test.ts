import { describe, expect, it } from 'vitest'
import { differenceInDays, parseLocalDate } from '../../src/domain/localDate'
import { getSundayFirstWeekdayIndex } from '../../src/domain/yearMonth'
import { buildSeasonTimeline } from '../../src/domain/seasonTimeline'

const SUNDAY = 0
const TUESDAY = 2
const THURSDAY = 4
const SATURDAY = 6

describe('buildSeasonTimeline', () => {
  it('matches the real 2025-26 anchor dates', () => {
    const timeline = buildSeasonTimeline(2025)

    // Verified against the NBA's published 2025-26 calendar.
    expect(timeline.openingNight).toBe('2025-10-21')
    expect(timeline.regularSeasonEnd).toBe('2026-04-12')
    expect(timeline.allStarSunday).toBe('2026-02-15')
    expect(timeline.tradeDeadline).toBe('2026-02-05')
    expect(timeline.playInStart).toBe('2026-04-14')
    expect(timeline.playInEnd).toBe('2026-04-17')
    expect(timeline.playoffsStart).toBe('2026-04-18')
    expect(timeline.freeAgencyNegotiations).toBe('2026-06-30')
    expect(timeline.freeAgencySignings).toBe('2026-07-06')
  })

  it('places every anchor on its required weekday', () => {
    const timeline = buildSeasonTimeline(2025)
    const weekday = (date: string) =>
      getSundayFirstWeekdayIndex(parseLocalDate(date))

    expect(weekday(timeline.openingNight)).toBe(TUESDAY)
    expect(weekday(timeline.tradeDeadline)).toBe(THURSDAY)
    expect(weekday(timeline.allStarSunday)).toBe(SUNDAY)
    expect(weekday(timeline.allStarBreakStart)).toBe(THURSDAY)
    expect(weekday(timeline.regularSeasonResumes)).toBe(THURSDAY)
    expect(weekday(timeline.playInStart)).toBe(TUESDAY)
    expect(weekday(timeline.playoffsStart)).toBe(SATURDAY)
    expect(weekday(timeline.draftLottery)).toBe(SUNDAY)
  })

  it('runs the regular season for 174 inclusive days', () => {
    const timeline = buildSeasonTimeline(2026)
    expect(
      differenceInDays(timeline.openingNight, timeline.regularSeasonEnd),
    ).toBe(173)
  })

  it('supports the latest timeline that remains inside calendar year 9999', () => {
    const timeline = buildSeasonTimeline(9998)

    expect(timeline.startingYear).toBe(9998)
    expect(timeline.endingYear).toBe(9999)
    expect(timeline.summerLeagueStart).toBe('9999-07-08')
  })

  it('keeps the whole timeline in chronological order', () => {
    const timeline = buildSeasonTimeline(2030)
    const order = [
      timeline.trainingCampOpens,
      timeline.preseasonStart,
      timeline.preseasonEnd,
      timeline.openingNight,
      timeline.cupKnockout,
      timeline.tradeDeadline,
      timeline.allStarBreakStart,
      timeline.allStarSunday,
      timeline.regularSeasonResumes,
      timeline.regularSeasonEnd,
      timeline.playInStart,
      timeline.playInEnd,
      timeline.playoffsStart,
      timeline.draftLottery,
      timeline.finalsStart,
      timeline.latestFinalsGame7,
      timeline.draftNightOne,
      timeline.draftNightTwo,
      timeline.freeAgencyNegotiations,
      timeline.freeAgencySignings,
      timeline.summerLeagueStart,
    ]
    for (let index = 1; index < order.length; index += 1) {
      expect(order[index] >= order[index - 1]).toBe(true)
    }
    expect(Object.isFrozen(timeline)).toBe(true)
  })

  it('rejects out-of-range starting years', () => {
    expect(() => buildSeasonTimeline(9999)).toThrow(RangeError)
    expect(() => buildSeasonTimeline(-1)).toThrow(RangeError)
    expect(() => buildSeasonTimeline(2025.5)).toThrow(RangeError)
  })
})
