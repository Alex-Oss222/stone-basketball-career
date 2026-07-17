import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  DEFAULT_PAGE_ID,
  NAVIGATION_SECTIONS,
  getPageById,
  getSectionById,
  getSectionForPage,
} from '../../src/app/navigation'
import type {
  NavigationPage,
  NavigationPageId,
  NavigationSectionId,
} from '../../src/app/navigation'

const EXPECTED_HIERARCHY = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    pages: [{ id: 'dashboard-overview', label: 'Overview' }],
  },
  {
    id: 'organization',
    label: 'Organization',
    pages: [
      { id: 'organization-overview', label: 'Overview' },
      { id: 'organization-ownership', label: 'Ownership' },
      {
        id: 'organization-staff-facilities',
        label: 'Staff & Facilities',
      },
    ],
  },
  {
    id: 'team',
    label: 'Team',
    pages: [
      { id: 'team-roster', label: 'Roster' },
      { id: 'team-rotation-gameplan', label: 'Rotation & Gameplan' },
      { id: 'team-health', label: 'Health' },
      { id: 'team-development', label: 'Development' },
    ],
  },
  {
    id: 'front-office',
    label: 'Front Office',
    pages: [
      { id: 'front-office-overview', label: 'Overview' },
      { id: 'front-office-scouting', label: 'Scouting' },
      { id: 'front-office-draft', label: 'Draft' },
      { id: 'front-office-free-agency', label: 'Free Agency' },
      { id: 'front-office-transactions', label: 'Transactions' },
      { id: 'front-office-market', label: 'Market' },
    ],
  },
  {
    id: 'schedule',
    label: 'Schedule',
    pages: [
      { id: 'schedule-team-schedule', label: 'Team Schedule' },
      { id: 'schedule-calendar', label: 'Calendar' },
      { id: 'schedule-results', label: 'Results' },
      { id: 'schedule-postseason', label: 'Postseason' },
    ],
  },
  {
    id: 'finances',
    label: 'Finances',
    pages: [
      { id: 'finances-overview', label: 'Overview' },
      { id: 'finances-cap-sheet', label: 'Cap Sheet' },
      { id: 'finances-contract-planning', label: 'Contract Planning' },
    ],
  },
  {
    id: 'league',
    label: 'League',
    pages: [
      { id: 'league-overview', label: 'Overview' },
      { id: 'league-standings', label: 'Standings' },
      { id: 'league-teams', label: 'Teams' },
      { id: 'league-players', label: 'Players' },
      { id: 'league-leaders', label: 'Leaders' },
      { id: 'league-transactions', label: 'Transactions' },
    ],
  },
  {
    id: 'inbox',
    label: 'Inbox',
    pages: [
      { id: 'inbox-decision-queue', label: 'Decision Queue' },
      { id: 'inbox-messages', label: 'Messages' },
    ],
  },
  {
    id: 'history',
    label: 'History',
    pages: [
      { id: 'history-career-overview', label: 'Career Overview' },
      { id: 'history-season-history', label: 'Season History' },
      { id: 'history-records', label: 'Records' },
      { id: 'history-championships', label: 'Championships' },
      { id: 'history-awards', label: 'Awards' },
    ],
  },
] as const

const EXPECTED_SECTION_IDS = EXPECTED_HIERARCHY.map((section) => section.id)
const EXPECTED_PAGE_IDS = EXPECTED_HIERARCHY.flatMap((section) =>
  section.pages.map((page) => page.id),
)

const AVAILABLE_PAGE_IDS = [
  'dashboard-overview',
  'team-roster',
  'schedule-team-schedule',
  'schedule-calendar',
  'league-overview',
  'league-teams',
  'league-players',
] as const

describe('central navigation registry', () => {
  it('defines the exact nine-section page hierarchy and labels', () => {
    expect(
      NAVIGATION_SECTIONS.map((section) => ({
        id: section.id,
        label: section.label,
        pages: section.pages.map((page) => ({
          id: page.id,
          label: page.label,
        })),
      })),
    ).toEqual(EXPECTED_HIERARCHY)
  })

  it('keeps section and page IDs unique and URL-stable', () => {
    expect(new Set(EXPECTED_SECTION_IDS).size).toBe(EXPECTED_SECTION_IDS.length)
    expect(new Set(EXPECTED_PAGE_IDS).size).toBe(EXPECTED_PAGE_IDS.length)

    for (const id of [...EXPECTED_SECTION_IDS, ...EXPECTED_PAGE_IDS]) {
      expect(id).toMatch(/^[a-z]+(?:-[a-z]+)*$/)
    }
  })

  it('marks exactly the seven implemented pages available', () => {
    const pages = allPages()

    expect(
      pages
        .filter((page) => page.availability === 'available')
        .map((page) => page.id),
    ).toEqual(AVAILABLE_PAGE_IDS)
    expect(
      pages
        .filter((page) => page.availability === 'planned')
        .map((page) => page.id),
    ).toEqual(
      EXPECTED_PAGE_IDS.filter(
        (pageId) => !AVAILABLE_PAGE_IDS.some((available) => available === pageId),
      ),
    )
  })

  it('keeps results and postseason planned with honest dependency explanations', () => {
    expect(getPageById('schedule-results')).toEqual({
      id: 'schedule-results',
      label: 'Results',
      availability: 'planned',
      requiredSystem: 'Requires game simulation and completed game results.',
    })
    expect(getPageById('schedule-postseason')).toEqual({
      id: 'schedule-postseason',
      label: 'Postseason',
      availability: 'planned',
      requiredSystem: 'Requires qualification and playoff bracket systems.',
    })
  })

  it('gives every planned page a short required-system explanation only', () => {
    const pages = allPages()

    for (const page of pages) {
      if (page.availability === 'planned') {
        expect(page.requiredSystem.trim().length).toBeGreaterThan(10)
        expect(page.requiredSystem.length).toBeLessThanOrEqual(80)
        expect(page.requiredSystem).toMatch(/^Requires /)
      } else {
        expect('requiredSystem' in page).toBe(false)
      }
    }
  })

  it('exposes the overview as the stable default page', () => {
    expect(DEFAULT_PAGE_ID).toBe('dashboard-overview')
    expect(getPageById(DEFAULT_PAGE_ID)?.label).toBe('Overview')
  })

  it('looks up sections, pages, and page ownership from one registry', () => {
    expect(getSectionById('front-office')?.label).toBe('Front Office')
    expect(getPageById('team-roster')).toMatchObject({
      label: 'Roster',
      availability: 'available',
    })
    expect(getSectionForPage('league-players')?.id).toBe('league')
  })

  it('derives closed literal ID unions instead of widening to string', () => {
    expectTypeOf<NavigationSectionId>().toEqualTypeOf<
      (typeof EXPECTED_SECTION_IDS)[number]
    >()
    expectTypeOf<NavigationPageId>().toEqualTypeOf<
      (typeof EXPECTED_PAGE_IDS)[number]
    >()
    expectTypeOf<string>().not.toMatchTypeOf<NavigationSectionId>()
    expectTypeOf<string>().not.toMatchTypeOf<NavigationPageId>()
  })
})

function allPages(): readonly NavigationPage[] {
  return NAVIGATION_SECTIONS.flatMap(
    (section): readonly NavigationPage[] => section.pages,
  )
}
