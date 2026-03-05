/**
 * Returns 'poor' | 'strong' | 'unknown' based on configurable thresholds.
 * A launch is 'poor' if either metric is below its threshold (and known).
 */
export function getPerformanceLabel(launch, settings) {
  if (!settings) return 'unknown'

  const twitterPoor =
    launch.twitter_likes != null && launch.twitter_likes < settings.twitter_likes_threshold
  const linkedinPoor =
    launch.linkedin_likes != null && launch.linkedin_likes < settings.linkedin_likes_threshold

  if (twitterPoor || linkedinPoor) return 'poor'
  return 'strong'
}

export function isPoorPerformer(launch, settings) {
  return getPerformanceLabel(launch, settings) === 'poor'
}
