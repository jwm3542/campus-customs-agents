import type { AgentEvent, Approval, Cash, RunRecord, Ticket } from './types'

export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body?.detail ?? `${res.status} ${res.statusText}`)
  return body as T
}

export const api = {
  health: () => req<{ ok: boolean; model: string; database: string }>('/api/health'),
  tickets: () => req<{ tickets: Ticket[] }>('/api/tickets').then(r => r.tickets),
  run: (id: number) => req<RunRecord>(`/api/tickets/${id}/run`, { method: 'POST' }),
  events: (ticketId: number) =>
    req<{ events: AgentEvent[] }>(`/api/events?limit=300&ticket_id=${ticketId}`).then(r => r.events),
  approvals: () => req<{ approvals: Approval[]; payments: any[] }>('/api/approvals'),
  approve: (id: number, approved_by: string) =>
    req(`/api/approvals/${id}/approve`, { method: 'POST', body: JSON.stringify({ approved_by }) }),
  reject: (id: number, rejected_by: string, reason: string) =>
    req(`/api/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify({ rejected_by, reason }) }),
  cash: () => req<Cash>('/api/cash'),
  reset: () => req<{ ok: boolean; message: string }>('/api/reset', { method: 'POST' }),
}
