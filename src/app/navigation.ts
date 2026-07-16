export type NavigationAvailability = 'available' | 'planned'

interface AvailableNavigationPageDefinition {
  readonly id: string
  readonly label: string
  readonly availability: 'available'
}

interface PlannedNavigationPageDefinition {
  readonly id: string
  readonly label: string
  readonly availability: 'planned'
  readonly requiredSystem: string
}

type NavigationPageDefinition =
  | AvailableNavigationPageDefinition
  | PlannedNavigationPageDefinition

interface NavigationSectionDefinition {
  readonly id: string
  readonly label: string
  readonly pages: readonly NavigationPageDefinition[]
}

export const NAVIGATION_SECTIONS = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    pages: [
      {
        id: 'dashboard-overview',
        label: 'Overview',
        availability: 'available',
      },
    ],
  },
  {
    id: 'organization',
    label: 'Organization',
    pages: [
      {
        id: 'organization-overview',
        label: 'Overview',
        availability: 'planned',
        requiredSystem: 'Requires organization management data.',
      },
      {
        id: 'organization-ownership',
        label: 'Ownership',
        availability: 'planned',
        requiredSystem: 'Requires ownership objectives and evaluation.',
      },
      {
        id: 'organization-staff-facilities',
        label: 'Staff & Facilities',
        availability: 'planned',
        requiredSystem: 'Requires staff and facilities systems.',
      },
    ],
  },
  {
    id: 'team',
    label: 'Team',
    pages: [
      {
        id: 'team-roster',
        label: 'Roster',
        availability: 'available',
      },
      {
        id: 'team-rotation-gameplan',
        label: 'Rotation & Gameplan',
        availability: 'planned',
        requiredSystem: 'Requires rotation and gameplan systems.',
      },
      {
        id: 'team-health',
        label: 'Health',
        availability: 'planned',
        requiredSystem: 'Requires player health and injury systems.',
      },
      {
        id: 'team-development',
        label: 'Development',
        availability: 'planned',
        requiredSystem: 'Requires player development systems.',
      },
    ],
  },
  {
    id: 'front-office',
    label: 'Front Office',
    pages: [
      {
        id: 'front-office-overview',
        label: 'Overview',
        availability: 'planned',
        requiredSystem: 'Requires front-office management systems.',
      },
      {
        id: 'front-office-scouting',
        label: 'Scouting',
        availability: 'planned',
        requiredSystem: 'Requires player scouting systems.',
      },
      {
        id: 'front-office-draft',
        label: 'Draft',
        availability: 'planned',
        requiredSystem: 'Requires a player draft system.',
      },
      {
        id: 'front-office-free-agency',
        label: 'Free Agency',
        availability: 'planned',
        requiredSystem: 'Requires free-agency and contract systems.',
      },
      {
        id: 'front-office-transactions',
        label: 'Transactions',
        availability: 'planned',
        requiredSystem: 'Requires roster transaction systems.',
      },
      {
        id: 'front-office-market',
        label: 'Market',
        availability: 'planned',
        requiredSystem: 'Requires a player market system.',
      },
    ],
  },
  {
    id: 'schedule',
    label: 'Schedule',
    pages: [
      {
        id: 'schedule-team-schedule',
        label: 'Team Schedule',
        availability: 'planned',
        requiredSystem: 'Requires schedule generation and season state.',
      },
      {
        id: 'schedule-calendar',
        label: 'Calendar',
        availability: 'planned',
        requiredSystem: 'Requires a league calendar system.',
      },
      {
        id: 'schedule-results',
        label: 'Results',
        availability: 'planned',
        requiredSystem: 'Requires game simulation and saved results.',
      },
      {
        id: 'schedule-postseason',
        label: 'Postseason',
        availability: 'planned',
        requiredSystem: 'Requires a postseason system.',
      },
    ],
  },
  {
    id: 'finances',
    label: 'Finances',
    pages: [
      {
        id: 'finances-overview',
        label: 'Overview',
        availability: 'planned',
        requiredSystem: 'Requires a league financial model.',
      },
      {
        id: 'finances-cap-sheet',
        label: 'Cap Sheet',
        availability: 'planned',
        requiredSystem: 'Requires salary-cap and contract systems.',
      },
      {
        id: 'finances-contract-planning',
        label: 'Contract Planning',
        availability: 'planned',
        requiredSystem: 'Requires contract-planning systems.',
      },
    ],
  },
  {
    id: 'league',
    label: 'League',
    pages: [
      {
        id: 'league-overview',
        label: 'Overview',
        availability: 'planned',
        requiredSystem: 'Requires league summary data.',
      },
      {
        id: 'league-standings',
        label: 'Standings',
        availability: 'planned',
        requiredSystem: 'Requires schedules, results, and standings.',
      },
      {
        id: 'league-teams',
        label: 'Teams',
        availability: 'available',
      },
      {
        id: 'league-players',
        label: 'Players',
        availability: 'available',
      },
      {
        id: 'league-leaders',
        label: 'Leaders',
        availability: 'planned',
        requiredSystem: 'Requires season statistics and leader derivation.',
      },
      {
        id: 'league-transactions',
        label: 'Transactions',
        availability: 'planned',
        requiredSystem: 'Requires league transaction history.',
      },
    ],
  },
  {
    id: 'inbox',
    label: 'Inbox',
    pages: [
      {
        id: 'inbox-decision-queue',
        label: 'Decision Queue',
        availability: 'planned',
        requiredSystem: 'Requires a decision-event system.',
      },
      {
        id: 'inbox-messages',
        label: 'Messages',
        availability: 'planned',
        requiredSystem: 'Requires an in-game messaging system.',
      },
    ],
  },
  {
    id: 'history',
    label: 'History',
    pages: [
      {
        id: 'history-career-overview',
        label: 'Career Overview',
        availability: 'planned',
        requiredSystem: 'Requires multi-season career state.',
      },
      {
        id: 'history-season-history',
        label: 'Season History',
        availability: 'planned',
        requiredSystem: 'Requires completed-season archives.',
      },
      {
        id: 'history-records',
        label: 'Records',
        availability: 'planned',
        requiredSystem: 'Requires historical record tracking.',
      },
      {
        id: 'history-championships',
        label: 'Championships',
        availability: 'planned',
        requiredSystem: 'Requires postseason and championship history.',
      },
      {
        id: 'history-awards',
        label: 'Awards',
        availability: 'planned',
        requiredSystem: 'Requires a league awards system.',
      },
    ],
  },
] as const satisfies readonly NavigationSectionDefinition[]

export type NavigationSection = (typeof NAVIGATION_SECTIONS)[number]
export type NavigationSectionId = NavigationSection['id']
export type NavigationPage = NavigationSection['pages'][number]
export type NavigationPageId = NavigationPage['id']
export type AvailableNavigationPageId = Extract<
  NavigationPage,
  { readonly availability: 'available' }
>['id']

export const DEFAULT_PAGE_ID: NavigationPageId = 'dashboard-overview'

const NAVIGATION_PAGES: readonly NavigationPage[] =
  NAVIGATION_SECTIONS.flatMap(
    (section): readonly NavigationPage[] => section.pages,
  )

export function getSectionById(
  sectionId: NavigationSectionId,
): NavigationSection | undefined {
  return NAVIGATION_SECTIONS.find((section) => section.id === sectionId)
}

export function getPageById(
  pageId: NavigationPageId,
): NavigationPage | undefined {
  return NAVIGATION_PAGES.find((page) => page.id === pageId)
}

export function getSectionForPage(
  pageId: NavigationPageId,
): NavigationSection | undefined {
  return NAVIGATION_SECTIONS.find((section) =>
    section.pages.some((page) => page.id === pageId),
  )
}
