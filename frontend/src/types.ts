export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface RunRecord {
  ticket_id: number
  status: 'queued' | 'running' | 'done' | 'error'
  queued_at?: string
  started_at?: string
  finished_at?: string
  decision?: TicketDecision
  error?: string
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  is_resolved: boolean
  run: RunRecord | null
}

export interface TicketDecision {
  ticket_id: number
  decision: string
  agents_used: AgentName[]
  approvals_queued: { approval_id: number; kind: string; ref_id: number; amount: number; reason: string }[]
  customer_draft: string | null
  blockers: string[]
  final_status: string
}

export interface SpecialistReport {
  agent: AgentName
  summary: string
  facts: string[]
  actions_taken: string[]
  blockers: string[]
  draft_message: string | null
}

export interface AgentEvent {
  ts: string
  run_id: string
  ticket_id: number | null
  agent: AgentName
  depth: number
  event: 'run_start' | 'model_response' | 'tool_result' | 'delegate' | 'delegate_refused' | 'run_end' | 'error'
  said: string | null
  tools: string[]
  to: AgentName | null
  detail: Record<string, any>
}

export interface Approval {
  id: number
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
  account: string
  reason: string
  requested_by: string
  ticket_id: number | null
  status: 'pending' | 'approved' | 'rejected'
  decided_by: string | null
  decided_at: string | null
  created_at: string
}

export interface Cash {
  name: string
  balance: number
  pending_approval_total: number
  balance_if_all_approved: number
}
