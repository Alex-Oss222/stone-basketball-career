import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import {
  LEAGUE_SETUP_PROGRESS_LABEL,
  NO_SEASON_STARTED_LABEL,
  SAVE_INDICATOR_LABELS,
} from '../app/dashboardViewModel'
import type {
  DashboardAction,
  SaveIndicatorState,
} from '../app/dashboardViewModel'
export type { SaveIndicatorState } from '../app/dashboardViewModel'
import {
  formatLocalDateForDisplay,
  formatSeasonPhaseForDisplay,
} from '../app/scheduleViewModel'
import {
  NAVIGATION_SECTIONS,
  getSectionForPage,
} from '../app/navigation'
import type {
  NavigationPage,
  NavigationPageId,
  NavigationSection,
} from '../app/navigation'
import type { Team } from '../domain/league'
import type { LocalDate } from '../domain/localDate'
import type { SeasonPhase } from '../domain/season'

type AvailableNavigationPage = Extract<
  NavigationPage,
  { readonly availability: 'available' }
>

type PlannedNavigationPage = Extract<
  NavigationPage,
  { readonly availability: 'planned' }
>

export interface ApplicationShellProps {
  readonly activePageId: NavigationPageId
  readonly pageNavigationActive: boolean
  readonly controlledTeam: Team | null
  readonly saveState: SaveIndicatorState | null
  readonly dashboardAction: DashboardAction
  readonly progress?: LeagueProgressPresentation
  readonly busy: boolean
  readonly onNavigate: (pageId: NavigationPageId) => void
  readonly onMainMenu: () => void
  readonly onAuthoritativeAction: (action: DashboardAction) => void
  readonly onNewLeague?: () => void
  readonly children: ReactNode
}

export function ApplicationShell({
  activePageId,
  pageNavigationActive,
  controlledTeam,
  saveState,
  dashboardAction,
  progress,
  busy,
  onNavigate,
  onMainMenu,
  onAuthoritativeAction,
  onNewLeague,
  children,
}: ApplicationShellProps) {
  const activeSection = requireSectionForPage(activePageId)

  return (
    <div className="application-shell">
      <a className="skip-link" href="#workspace-content">
        Skip to content
      </a>
      <AppHeader
        controlledTeam={controlledTeam}
        saveState={saveState}
        dashboardAction={dashboardAction}
        progress={progress}
        busy={busy}
        onMainMenu={onMainMenu}
        onAuthoritativeAction={onAuthoritativeAction}
        onNewLeague={onNewLeague}
      />
      <PrimaryNavigation
        activePageId={activePageId}
        pageNavigationActive={pageNavigationActive}
        busy={busy}
        onNavigate={onNavigate}
      />
      <SecondaryTabNavigation
        activePageId={activePageId}
        pageNavigationActive={pageNavigationActive}
        section={activeSection}
        busy={busy}
        onNavigate={onNavigate}
      />
      <main
        id="workspace-content"
        className="application-shell-content"
        aria-busy={busy}
        tabIndex={-1}
      >
        {children}
      </main>
    </div>
  )
}

export interface AppHeaderProps {
  readonly controlledTeam: Team | null
  readonly saveState: SaveIndicatorState | null
  readonly dashboardAction: DashboardAction
  readonly progress?: LeagueProgressPresentation
  readonly busy: boolean
  readonly onMainMenu: () => void
  readonly onAuthoritativeAction: (action: DashboardAction) => void
  readonly onNewLeague?: () => void
}

export interface LeagueProgressPresentation {
  readonly seasonLabel: string
  readonly currentDate: LocalDate
  readonly currentPhase: SeasonPhase
}

export function AppHeader({
  controlledTeam,
  saveState,
  dashboardAction,
  progress,
  busy,
  onMainMenu,
  onAuthoritativeAction,
  onNewLeague,
}: AppHeaderProps) {
  const teamName =
    controlledTeam === null
      ? 'No team selected'
      : `${controlledTeam.city} ${controlledTeam.nickname}`
  const teamContext =
    controlledTeam === null
      ? 'Choose a team to establish your front office.'
      : controlledTeam.abbreviation

  return (
    <header className="application-header">
      <div className="application-header-brand">
        <button
          type="button"
          className="main-menu-button"
          onClick={onMainMenu}
          disabled={busy}
        >
          Stone Basketball GM
        </button>
        <div className="controlled-team-identity" aria-label="Controlled team">
          <strong>{teamName}</strong>
          <span>{teamContext}</span>
        </div>
      </div>

      <div className="application-progress" aria-label="League progression">
        {progress === undefined ? (
          <>
            <span className="application-progress-primary">
              {LEAGUE_SETUP_PROGRESS_LABEL}
            </span>
            <span className="application-progress-detail">
              {NO_SEASON_STARTED_LABEL}
            </span>
          </>
        ) : (
          <>
            <span className="application-progress-primary">
              {progress.seasonLabel}
            </span>
            <span className="application-progress-detail">
              <span className="visually-hidden">Current date: </span>
              {formatLocalDateForDisplay(progress.currentDate)}
            </span>
            <span className="application-progress-detail">
              <span className="visually-hidden">Current phase: </span>
              {formatSeasonPhaseForDisplay(progress.currentPhase)}
            </span>
          </>
        )}
      </div>

      <div className="application-header-actions">
        {saveState !== null && <SaveStateIndicator state={saveState} />}
        <button
          type="button"
          className="header-utility-button"
          aria-disabled="true"
          title="Tools and settings are coming later"
        >
          Tools / Settings{' '}
          <span className="coming-later-marker">Coming later</span>
        </button>
        {onNewLeague !== undefined && (
          <button
            type="button"
            className="new-league-button"
            onClick={onNewLeague}
            disabled={busy}
          >
            New League
          </button>
        )}
        <AuthoritativeAction
          action={dashboardAction}
          busy={busy}
          onAction={onAuthoritativeAction}
        />
      </div>
    </header>
  )
}

export interface PrimaryNavigationProps {
  readonly activePageId: NavigationPageId
  readonly pageNavigationActive: boolean
  readonly busy: boolean
  readonly onNavigate: (pageId: NavigationPageId) => void
}

export function PrimaryNavigation({
  activePageId,
  pageNavigationActive,
  busy,
  onNavigate,
}: PrimaryNavigationProps) {
  const activeSection = requireSectionForPage(activePageId)

  return (
    <nav className="primary-navigation" aria-label="Primary">
      {NAVIGATION_SECTIONS.map((section) => {
        const firstPage = section.pages[0]
        const isActive =
          pageNavigationActive && section.id === activeSection.id

        return (
          <button
            type="button"
            className="primary-navigation-button"
            key={section.id}
            onClick={() => onNavigate(firstPage.id)}
            aria-current={isActive ? 'page' : undefined}
            disabled={busy}
          >
            {section.label}
          </button>
        )
      })}
    </nav>
  )
}

export interface SecondaryTabNavigationProps {
  readonly activePageId: NavigationPageId
  readonly pageNavigationActive: boolean
  readonly section: NavigationSection
  readonly busy: boolean
  readonly onNavigate: (pageId: NavigationPageId) => void
}

export function SecondaryTabNavigation({
  activePageId,
  pageNavigationActive,
  section,
  busy,
  onNavigate,
}: SecondaryTabNavigationProps) {
  const pages: readonly NavigationPage[] = section.pages

  return (
    <nav
      className="secondary-tab-navigation"
      aria-label={`${section.label} pages`}
    >
      {pages.map((page) => (
        <button
          type="button"
          className="secondary-tab-button"
          key={page.id}
          onClick={() => onNavigate(page.id)}
          aria-current={
            pageNavigationActive && page.id === activePageId
              ? 'page'
              : undefined
          }
          disabled={busy}
        >
          <span>{page.label}</span>
          {page.availability === 'planned' && (
            <span className="coming-later-marker">Coming later</span>
          )}
        </button>
      ))}
    </nav>
  )
}

export interface AvailablePageProps {
  readonly page: AvailableNavigationPage
  readonly section: NavigationSection
  readonly children: ReactNode
}

export function AvailablePage({
  page,
  section,
  children,
}: AvailablePageProps) {
  const headingId = `page-${page.id}-heading`
  const headingRef = usePageHeadingFocus(page.id)

  return (
    <section className="available-page" aria-labelledby={headingId}>
      <header className="page-heading">
        <p className="page-status">{section.label}</p>
        <h1 id={headingId} ref={headingRef} tabIndex={-1}>
          {page.label}
        </h1>
      </header>
      {children}
    </section>
  )
}

export interface ComingLaterPageProps {
  readonly page: PlannedNavigationPage
  readonly section: NavigationSection
}

export function ComingLaterPage({
  page,
  section,
}: ComingLaterPageProps) {
  const headingId = `page-${page.id}-heading`
  const headingRef = usePageHeadingFocus(page.id)

  return (
    <section
      className="coming-later-page"
      aria-label={`${section.label}: ${page.label}`}
      aria-labelledby={headingId}
    >
      <p className="page-status">Coming later</p>
      <h1 id={headingId} ref={headingRef} tabIndex={-1}>
        {page.label}
      </h1>
      <p className="coming-later-requirement">{page.requiredSystem}</p>
      <p className="coming-later-note">
        No placeholder data is shown until that system is implemented.
      </p>
    </section>
  )
}

export interface DashboardCardProps {
  readonly title: string
  readonly children: ReactNode
}

export function DashboardCard({ title, children }: DashboardCardProps) {
  return (
    <section className="dashboard-card">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

export function SaveStateIndicator({
  state,
}: {
  readonly state: SaveIndicatorState
}) {
  const label = SAVE_INDICATOR_LABELS[state]

  return (
    <span
      className={`save-state-indicator save-state-${state}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {label}
    </span>
  )
}

export interface AuthoritativeActionProps {
  readonly action: DashboardAction
  readonly busy: boolean
  readonly onAction: (action: DashboardAction) => void
}

export function AuthoritativeAction({
  action,
  busy,
  onAction,
}: AuthoritativeActionProps) {
  return (
    <button
      type="button"
      className="authoritative-action"
      onClick={() => onAction(action)}
      disabled={busy}
    >
      {action.label}
    </button>
  )
}

function requireSectionForPage(pageId: NavigationPageId): NavigationSection {
  const section = getSectionForPage(pageId)
  if (section === undefined) {
    throw new RangeError(`Navigation page ${pageId} has no section`)
  }
  return section
}

function usePageHeadingFocus(pageId: NavigationPageId) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [pageId])

  return headingRef
}
