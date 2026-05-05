import { readFileSync, readdirSync } from 'fs'
import { join } from 'path'
import type { AnaliseSource } from '~/types/analise'

/**
 * Returns metadata for all available analyses.
 * In production: fetches the pre-compiled _index.json (static asset).
 * In dev: scans public/analises/*.json files dynamically.
 */
export default defineEventHandler(async (event) => {
  // Dev: scan source files
  try {
    const publicDir = join(process.cwd(), 'public', 'analises')
    const files = readdirSync(publicDir).filter(f => f.endsWith('.json'))
    const analises: Array<{ id: string; title: string; description?: string; backgroundColor?: string; backgroundImage?: string }> = []

    for (const file of files) {
      const content = readFileSync(join(publicDir, file), 'utf-8')
      const config: AnaliseSource = JSON.parse(content)
      analises.push({
        id: config.id,
        title: config.title,
        description: config.description,
        backgroundColor: config.backgroundColor,
        backgroundImage: config.backgroundImage,
      })
    }
    return analises
  } catch {
    // Edge runtime: no fs, fetch from static asset
  }

  // Production (Cloudflare Pages): fetch the static compiled index
  const url = getRequestURL(event)
  const baseUrl = `${url.protocol}//${url.host}`
  const data = await $fetch(`${baseUrl}/analises/_compiled/_index.json`)
  return data
})
