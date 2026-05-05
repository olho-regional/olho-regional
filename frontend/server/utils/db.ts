import { drizzle } from 'drizzle-orm/libsql'
import { createClient, type Client } from '@libsql/client'
import { resolve } from 'node:path'

let db: ReturnType<typeof drizzle> | null = null
let fallbackDb: ReturnType<typeof drizzle> | null = null
let dbSource: 'local' | 'vps' | 'turso' = 'local'
let initialized = false

export function getDbSource() {
  return dbSource
}

function createTursoFallback(env: any): ReturnType<typeof drizzle> | null {
  const tursoUrl = env.TURSO_DATABASE_URL
  const tursoToken = env.TURSO_AUTH_TOKEN
  if (!tursoUrl) return null
  const client = createClient({ url: tursoUrl, authToken: tursoToken })
  return drizzle(client)
}

export async function initDB(event?: any) {
  if (initialized) return

  if (import.meta.dev) {
    // Allow testing VPS/Turso in dev by setting env vars
    const vpsUrl = process.env.VPS_DATABASE_URL
    const vpsToken = process.env.VPS_AUTH_TOKEN
    if (vpsUrl && vpsToken) {
      try {
        const client = createClient({ url: vpsUrl, authToken: vpsToken })
        await client.execute('SELECT 1')
        db = drizzle(client)
        dbSource = 'vps'
        initialized = true
        console.log('[db] Dev mode: connected to VPS')
        return
      } catch (e: any) {
        console.warn('[db] Dev mode: VPS failed, using local file:', e.message)
      }
    }

    const dbPath = resolve(process.cwd(), '../processamento/database/olho-regional.db')
    const client = createClient({ url: `file:${dbPath}` })
    db = drizzle(client)
    dbSource = 'local'
    initialized = true
    return
  }

  const env = event?.context?.cloudflare?.env ?? process.env
  const vpsUrl = env.VPS_DATABASE_URL
  const vpsToken = env.VPS_AUTH_TOKEN

  // Always prepare the Turso fallback
  fallbackDb = createTursoFallback(env)

  // Try VPS first
  if (vpsUrl && vpsToken) {
    try {
      const client = createClient({ url: vpsUrl, authToken: vpsToken })
      await client.execute('SELECT 1')
      db = drizzle(client)
      dbSource = 'vps'
      initialized = true
      return
    } catch {
      console.warn('[db] VPS unavailable, falling back to Turso')
    }
  }

  // Fallback to Turso
  if (fallbackDb) {
    db = fallbackDb
    dbSource = 'turso'
    initialized = true
    return
  }

  throw new Error('No database URL configured (VPS_DATABASE_URL or TURSO_DATABASE_URL)')
}

/** Switch to Turso fallback if VPS fails mid-session */
export function failoverToTurso() {
  if (fallbackDb && dbSource === 'vps') {
    console.warn('[db] VPS query failed, switching to Turso for this isolate')
    db = fallbackDb
    dbSource = 'turso'
  }
}

export function useDB() {
  return db as any
}
