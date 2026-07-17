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

  it.each([
    ['front-office-draft', 'front-office', 'a player draft system'],
    ['history-championships', 'history', 'postseason and championship history'],
  ] as const)(
    '%s contains only its honest dependency explanation',
    (pageId, sectionId, requiredCopy) => {
      const section = getSectionById(sectionId)
      const page = getPageById(pageId)
      if (section === undefined || page?.availability !== 'planned') {
        throw new Error(`Expected the planned ${pageId} page`)
      }

      const markup = renderToStaticMarkup(
        <ComingLaterPage section={section} page={page} />,
      )
      const visibleText = markup.replace(/<[^>]*>/g, ' ')

      expect(markup).not.toMatch(/<(?:table|dl)(?:\s|>)/i)
      expect(visibleText).not.toMatch(/\d/)
      expect(markup).toContain(requiredCopy)
      expect(markup).not.toContain('Score')
      expect(markup).not.toContain('Record')
      expect(markup).not.toContain('Standings')
    },
  )
})
