/** Face Auth API - uses fetch for consistency with existing patterns */
const BASE = '/api/face-auth'

async function request(path: string, options?: RequestInit) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as any).detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const faceAuthApi = {
  getStatus: () => request('/status'),

  enroll: (username: string, frames: string[]) =>
    request('/enroll', { method: 'POST', body: JSON.stringify({ username, frames }) }),

  detect: (frame: string) =>
    request('/detect', { method: 'POST', body: JSON.stringify({ frame }) }),

  livenessCheck: (frames: string[], actions: string[]) =>
    request('/liveness', { method: 'POST', body: JSON.stringify({ frames, actions }) }),

  startGuard: (authorizedUser: string) =>
    request('/guard/start', { method: 'POST', body: JSON.stringify({ authorized_user: authorizedUser }) }),

  stopGuard: () => request('/guard/stop', { method: 'POST' }),

  resetGuard: () => request('/guard/reset', { method: 'POST' }),

  unlockKb: (restore: boolean = true) =>
    request(`/guard/unlock?restore=${restore}`, { method: 'POST' }),

  verify: (frame: string) =>
    request('/verify', { method: 'POST', body: JSON.stringify({ frame }) }),

  removeEnrollment: (username: string) =>
    request(`/enroll/${encodeURIComponent(username)}`, { method: 'DELETE' }),
}
