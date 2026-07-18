import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

export interface WorkspaceErrorBoundaryProps {
  readonly children: ReactNode
  readonly resetKey: string
}

interface WorkspaceErrorBoundaryState {
  readonly failed: boolean
  readonly resetKey: string
}

/**
 * Contains render-time failures raised by derived read models so that an
 * invariant violation degrades to an in-place message instead of blanking the
 * whole application. The surrounding shell, navigation, and save controls stay
 * interactive. A navigation-key change clears the local failure without
 * remounting healthy snapshot-keyed presentation derivation on every page.
 */
export class WorkspaceErrorBoundary extends Component<
  WorkspaceErrorBoundaryProps,
  WorkspaceErrorBoundaryState
> {
  constructor(props: WorkspaceErrorBoundaryProps) {
    super(props)
    this.state = { failed: false, resetKey: props.resetKey }
  }

  static getDerivedStateFromError(): Pick<
    WorkspaceErrorBoundaryState,
    'failed'
  > {
    return { failed: true }
  }

  static getDerivedStateFromProps(
    props: WorkspaceErrorBoundaryProps,
    state: WorkspaceErrorBoundaryState,
  ): WorkspaceErrorBoundaryState | null {
    return props.resetKey === state.resetKey
      ? null
      : { failed: false, resetKey: props.resetKey }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // No telemetry by product rule; surface locally for developer diagnosis.
    console.error('Workspace content failed to render', error, info)
  }

  override render(): ReactNode {
    if (this.state.failed) {
      return (
        <section
          className="empty-state"
          role="alert"
          aria-labelledby="workspace-error-heading"
        >
          <h2 id="workspace-error-heading">This view could not be displayed</h2>
          <p>
            The current league data could not be shown. Switch to another
            section, or reload the app to try again.
          </p>
        </section>
      )
    }

    return this.props.children
  }
}
