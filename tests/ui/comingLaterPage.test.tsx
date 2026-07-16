import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  getPageById,
  getSectionById,
} from '../../src/app/navigation'
import { ComingLaterPage } from '../../src/ui/dashboardShell'

describe('ComingLaterPage', () => {
  it('renders an honest planned-page explanation without placeholder data', () => {
    const section = getSectionById('organization')
    const page = getPageById('organization-ownership')
    if (section === undefined || page?.availability !== 'planned') {
      throw new Error('Expected the planned organization ownership page')
    }

    const markup = renderToStaticMarkup(
      <ComingLaterPage section={section} page={page} />,
    )

    expect(markup).toContain('Coming later')
    expect(markup).toContain('Ownership')
    expect(markup).toContain(page.requiredSystem)
    expect(markup).toContain(
      'No placeholder data is shown until that system is implemented.',
    )
  })

  it('contains no data table, definition list, or fabricated numeric content', () => {
    const section = getSectionById('schedule')
    const page = getPageById('schedule-results')
    if (section === undefined || page?.availability !== 'planned') {
      throw new Error('Expected the planned schedule results page')
    }

    const markup = renderToStaticMarkup(
      <ComingLaterPage section={section} page={page} />,
    )
    const visibleText = markup.replace(/<[^>]*>/g, ' ')

    expect(markup).not.toMatch(/<(?:table|dl)(?:\s|>)/i)
    expect(visibleText).not.toMatch(/\d/)
  })
})
