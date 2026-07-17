import {
  EXHIBITION_AWAY_TEAM,
  EXHIBITION_GAME_RESULT,
  EXHIBITION_HOME_TEAM,
  EXHIBITION_PLAYER_INFO,
} from '../dev/exhibitionGameResult'
import { GameResultPage } from './gameResultPage'

/**
 * DEV ONLY — renders the post-game workspace against the hand-written design
 * fixture. Loaded lazily behind an import.meta.env.DEV guard so neither this
 * module nor the fixture reaches the production bundle. Real games keep
 * showing an honest absence of results until the simulation exists.
 */
export default function DevGameResultPreview({
  onBack,
}: {
  readonly onBack: () => void
}) {
  return (
    <div className="dev-preview-page">
      <p className="dev-preview-banner" role="note">
        Design preview — every name and number below is a hand-written fixture,
        not a simulated result. This screen exists to decide the result
        contract (roadmap §6) and is excluded from production builds.
      </p>
      <GameResultPage
        result={EXHIBITION_GAME_RESULT}
        homeTeam={EXHIBITION_HOME_TEAM}
        awayTeam={EXHIBITION_AWAY_TEAM}
        playerInfo={EXHIBITION_PLAYER_INFO}
        contextLabel="Exhibition preview · design fixture"
        onBack={onBack}
      />
    </div>
  )
}
