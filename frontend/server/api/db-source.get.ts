import { getDbSource } from '../utils/db'

export default defineEventHandler(() => {
  return { source: getDbSource() }
})
