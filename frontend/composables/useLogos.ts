/**
 * Resolve a logo URL from a domain.
 * All logos are stored as /logos/{domain}.jpg (no manifest needed).
 */
export function getLogoUrl(domain: string | undefined | null): string | null {
  if (!domain) return null
  const clean = domain.replace(/^www\./, '').replace(/\/$/, '')
  return `/logos/${clean}.jpg`
}
