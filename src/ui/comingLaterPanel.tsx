export interface ComingLaterPanelProps {
  readonly title: string
  readonly requirement: string
}

/**
 * Honest placeholder for a scaffolded tab whose data system does not exist
 * yet. It shows no fabricated schedule, result, or standing values.
 */
export function ComingLaterPanel({ title, requirement }: ComingLaterPanelProps) {
  return (
    <section className="coming-later-panel" aria-label={`${title} — coming later`}>
      <p className="coming-later-marker">Coming later</p>
      <h3>{title}</h3>
      <p className="coming-later-requirement">{requirement}</p>
      <p className="coming-later-note">
        No placeholder data is shown until that system is implemented.
      </p>
    </section>
  )
}
