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

  // Production (Cloudflare Pages): read from static assets via ASSETS binding
  const env = (event.context.cloudflare?.env) || (globalThis as any).__env__
  if (env?.ASSETS) {
    const url = new URL('/analises/_compiled/_index.json', getRequestURL(event))
    const res = await env.ASSETS.fetch(new Request(url.toString()))
    if (res.ok) return res.json()
  }
  throw createError({ statusCode: 404, statusMessage: 'Analyses not found' })
})