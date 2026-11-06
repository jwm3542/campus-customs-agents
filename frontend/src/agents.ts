import type { AgentName } from './types'

// Each agent is a member of the house band. Same order every time so eyes learn the lineup.
export const LINEUP: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const AGENTS: Record<AgentName, { name: string; role: string; glyph: string }> = {
  boss: { name: 'The Boss', role: 'Frontman · calls the play', glyph: '★' },
  inventory: { name: 'Inventory', role: 'Stockroom · rhythm guitar', glyph: '▤' },
  accounting: { name: 'Accounting', role: 'The ledger · bass', glyph: '$' },
  facilities: { name: 'Facilities', role: 'The building · drums', glyph: '⌂' },
  customer_service: { name: 'Customer Service', role: 'The counter · vocals', glyph: '♪' },
}

export const TICKET_KIND: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
