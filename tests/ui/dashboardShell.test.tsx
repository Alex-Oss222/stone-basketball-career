import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  SAVE_INDICATOR_LABELS,
  deriveDashboardAction,
} from '../../src/app/dashboardViewModel'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'
import {
  AppHeader,
  ApplicationShell,
  SaveStateIndicator,
} from '../../src/ui/dashboardShell'

const snapshot = createLeagueSnapshotV2Fixture()
const league = snapshot.league
const controlledTeam = league.teams[0]

describe('AppHeader', () => {
  it('shows real team identity, honest progression, and one state-derived action', () => {
    const action = deriveDashboardAction({
      league,
      managedTeamId: controlledTeam.id,
      hasSchedule: true,
    })
    const markup = renderToStaticMarkup(
      <AppHeader
        controlledTeam={controlledTeam}
        saveState="saved"
        dashboardAction={action}
        busy={false}
        onMainMenu={() => undefined}
        onAuthoritativeAction={() => undefined}
      />,
    )

    expect(markup).toContain(
      `${controlledTeam.city} ${controlledTeam.nickname}`,
    )
    expect(markup).toContain(controlledTeam.abbreviation)
    expect(markup).toContain('League setup')
    expect(markup).toContain('No season started')
    expect(markup).toContain('Tools / Settings')
    expect(markup).toContain('Coming later')
    expect(markup).toContain('View Schedule')
    expect(markup.match(/class="authoritative-action"/g)).toHaveLength(1)
    expect(markup).not.toContain('Sim Next Game')
  })

  it('does not claim an empty application has a local save', () => {
    const markup = renderToStaticMarkup(
      <AppHeader
        controlledTeam={null}
        saveState={null}
        dashboardAction={deriveDashboardAction(null)}
        busy={false}
        onMainMenu={() => undefined}
        onAuthoritativeAction={() => undefined}
      />,
    )

    expect(markup).not.toContain('Saved locally')
    expect(markup).not.toContain('save-state-indicator')
    expect(markup).toContain('Create League')
  })

  it('renders explicit schedule-ready progression for a V2-backed view', () => {
    const markup = renderToStaticMarkup(
      <AppHeader
        controlledTeam={controlledTeam}
        saveState="saved"
        dashboardAction={deriveDashboardAction({
          league,
          managedTeamId: controlledTeam.id,
          hasSchedule: true,
        })}
        progress={{
          seasonLabel: snapshot.season.displayLabel,
          currentDate: snapshot.season.currentDate,
          currentPhase: snapshot.season.currentPhase,
        }}
        busy={false}
        onMainMenu={() => undefined}
        onAuthoritativeAction={() => undefined}
      />,
    )

    expect(markup).toContain(snapshot.season.displayLabel)
    expect(markup).toContain('October 5, 2026')
    expect(markup).toContain('Regular season')
    expect(markup).not.toContain('No season started')
  })
})

describe('SaveStateIndicator', () => {
  it.each(Object.entries(SAVE_INDICATOR_LABELS))(
    'renders the exact %s persistence label',
    (state, label) => {
      const markup = renderToStaticMarkup(
        <SaveStateIndicator
          state={state as keyof typeof SAVE_INDICATOR_LABELS}
        />,
      )

      expect(markup).toContain(label)
    },
  )
})

describe('ApplicationShell navigation semantics', () => {
  it('marks the active section and page only for a configured page view', () => {
    const baseProps = {
      activePageId: 'dashboard-overview' as const,
      controlledTeam: null,
      saveState: null,
      dashboardAction: deriveDashboardAction(null),
      busy: false,
      onNavigate: () => undefined,
      onMainMenu: () => undefined,
      onAuthoritativeAction: () => undefined,
    }
    const pageMarkup = renderToStaticMarkup(
      <ApplicationShell {...baseProps} pageNavigationActive>
        <p>Overview content</p>
      </ApplicationShell>,
    )
    const setupMarkup = renderToStaticMarkup(
      <ApplicationShell {...baseProps} pageNavigationActive={false}>
        <p>League setup content</p>
      </ApplicationShell>,
    )

    expect(pageMarkup.match(/aria-current="page"/g)).toHaveLength(2)
    expect(pageMarkup).not.toContain(
      'Permanently delete local league save',
    )
    expect(setupMarkup).not.toContain('aria-current="page"')
    expect(setupMarkup).toContain('href="#workspace-content"')
    expect(setupMarkup).toContain('id="workspace-content"')
    expect(setupMarkup).toContain('tabindex="-1"')
  })
})
