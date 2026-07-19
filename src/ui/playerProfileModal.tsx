import { useEffect } from 'react'
import type { ReactNode } from 'react'

export interface PlayerProfileModalProps {
  readonly onClose: () => void
  readonly children: ReactNode
}

/**
 * The player profile popup: an overlay over the current screen (roster, etc.)
 * so the player page dismisses instead of navigating away. Closes on Escape, on
 * a backdrop click, and via the close control centered at the top of the page.
 */
export function PlayerProfileModal({
  onClose,
  children,
}: PlayerProfileModalProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      className="player-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Player profile"
      onClick={onClose}
    >
      <button
        type="button"
        className="player-modal-close"
        aria-label="Close player profile"
        onClick={onClose}
      >
        <span aria-hidden="true">×</span>
      </button>
      <div
        className="player-modal-panel"
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
