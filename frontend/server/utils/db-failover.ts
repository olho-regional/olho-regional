import { failoverToTurso, useDB, getDbSource } from './db'

/**
 * Execute a database operation with automatic failover to Turso if VPS fails.
 * Use this in API routes instead of calling useDB() + query directly.
 */
export async function withDbFailover<T>(fn: (db: ReturnType<typeof useDB>) => Promise<T>): Promise<T> {
  const db = useDB()
  try {
    return await fn(db)
  } catch (err: any) {
    // If already on Turso or local, don't retry
    if (getDbSource() !== 'vps') throw err

    // Connection/network errors → failover
    const msg = err?.message || ''
    if (msg.includes('fetch') || msg.includes('ECONNREFUSED') || msg.includes('timeout') || msg.includes('network')) {
      failoverToTurso()
      const fallback = useDB()
      return await fn(fallback)
    }

    // Non-network error (e.g. SQL syntax) — don't retry
    throw err
  }
}
