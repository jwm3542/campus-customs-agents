import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from './api'
import { AGENTS, LINEUP, TICKET_KIND, money } from './agents'
import type { AgentEvent, AgentName, Approval, Cash, SpecialistReport, Ticket, TicketDecision } from './types'

type Volume = 3 | 5 | 7 | 11
const VOLUMES: Record<Volume, { cls: string; label: string; next: Volume }> = {
  3: { cls: 'low', label: '1938 · big band', next: 5 },
  5: { cls: 'fifties', label: '1956 · rockabilly', next: 7 },
  7: { cls: 'shop', label: '1975 · the shop', next: 11 },
  11: { cls: 'eleven', label: '1984 · one louder', next: 3 },
}

function useVolume() {
  const [vol, setVol] = useState<Volume>(() => {
    const v = Number(localStorage.getItem('cc-volume'))
    return v === 3 || v === 5 || v === 11 ? v : 7
  })
  useEffect(() => {
    document.body.className = VOLUMES[vol].cls
    localStorage.setItem('cc-volume', String(vol))
  }, [vol])
  return [vol, () => setVol(VOLUMES[vol].next)] as const
}

/** Rolls the register digits from the old balance to the new one. */
function useRolling(target: number | undefined) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target === undefined) return
    const start = from.current ?? target
    if (start === target) { setShown(target); from.current = target; return }
    const t0 = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / 1400)
      setShown(start + (target - start) * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); from.current = target }
  }, [target])
  return shown
}

type Mode = 'idle' | 'thinking' | 'tool' | 'handoff' | 'done' | 'error'
type AgentState = { mode: Mode; line: string }

function stageFrom(events: AgentEvent[]): Record<AgentName, AgentState> {
  const s = Object.fromEntries(
    LINEUP.map(a => [a, { mode: 'idle', line: 'Waiting in the wings.' }]),
  ) as Record<AgentName, AgentState>
  const set = (a: AgentState, mode: Mode, line: string) => { a.mode = mode; a.line = line }
  for (const e of events) {
    const a = s[e.agent]
    if (!a) continue
    switch (e.event) {
      case 'run_start': set(a, 'thinking', 'Reading the task…'); break
      case 'model_response': {
        const tools = e.tools.filter(t => t !== 'delegate')
        if (e.tools.includes('delegate')) set(a, 'handoff', 'Handing off a part…')
        else if (tools.length) set(a, 'tool', `Using ${tools.join(', ')}`)
        else if (e.said) set(a, 'thinking', e.said)
        break
      }
      case 'tool_result': set(a, 'thinking', `Got ${e.tools.join(', ') || 'results'} back`); break
      case 'delegate': set(a, 'handoff', `Waiting on ${AGENTS[e.to as AgentName]?.name ?? e.to}`); break
      case 'delegate_refused': set(a, 'thinking', `Hand-off refused: ${e.said}`); break
      case 'run_end': set(a, 'done', e.detail?.output?.summary ?? e.detail?.output?.decision ?? 'Done.'); break
      case 'error': set(a, 'error', e.detail?.message ?? 'Error'); break
    }
  }
  return s
}

const isLive = (t?: Ticket | null) => t?.run?.status === 'running' || t?.run?.status === 'queued'

function Stamp({ t }: { t: Ticket }) {
  if (t.is_resolved) return <span className="stamp resolved">Resolved</span>
  if (isLive(t)) return <span className="stamp live">On stage</span>
  if (t.status === 'waiting_approval') return <span className="stamp wait">Needs your OK</span>
  return <span className="stamp open">{t.status.replace(/_/g, ' ')}</span>
}

export default function App() {
  const [vol, turn] = useVolume()
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [signer, setSigner] = useState(() => localStorage.getItem('cc-signer') ?? '')
  const [chaching, setChaching] = useState(false)

  const running = tickets.some(isLive)
  const ticket = tickets.find(t => t.id === selected) ?? null

  const refresh = useCallback(async () => {
    try {
      const [ts, ap, c] = await Promise.all([api.tickets(), api.approvals(), api.cash()])
      setTickets(ts); setApprovals(ap.approvals); setCash(c); setOnline(true)
      const pick = selected ?? ts.find(t => !t.is_resolved)?.id ?? ts[0]?.id ?? null
      if (selected == null) setSelected(pick)
      setEvents(pick == null ? [] : await api.events(pick))
    } catch (e) {
      setOnline(false); setError(`Can't reach the backend: ${(e as Error).message}`)
    }
  }, [selected])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const id = setInterval(refresh, running ? 1500 : 6000)
    return () => clearInterval(id)
  }, [refresh, running])

  // Only the most recent run on this ticket is on stage.
  const runEvents = useMemo(() => {
    const last = events.at(-1)?.run_id
    return last ? events.filter(e => e.run_id === last) : []
  }, [events])
  const stage = useMemo(() => stageFrom(runEvents), [runEvents])
  const reports = useMemo(() => {
    const out: Partial<Record<AgentName, SpecialistReport | TicketDecision>> = {}
    for (const e of runEvents) if (e.event === 'run_end' && e.detail?.output) out[e.agent] = e.detail.output
    return out
  }, [runEvents])

  const feedRef = useRef<HTMLOListElement>(null)
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
  }, [runEvents.length])

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label); setError(null)
    try { await fn(); await refresh() } catch (e) { setError((e as Error).message) } finally { setBusy(null) }
  }

  const pay = (a: Approval) => act(`a${a.id}`, async () => {
    await api.approve(a.id, signer.trim())
    setChaching(true); setTimeout(() => setChaching(false), 1600)
  })

  const pending = approvals.filter(a => a.status === 'pending')
  const decided = approvals.filter(a => a.status !== 'pending').slice(-4).reverse()
  const balance = useRolling(cash?.balance)
  const boss = reports.boss as TicketDecision | undefined
  const satOut = boss ? LINEUP.filter(a => !reports[a]) : []

  return (
    <>
      <div className="announce" role="note">
        Practice desk · Agents only draft. <b>No customer is emailed and no real vendor is called.</b> Money moves only when a human signs.
      </div>

      <header className="marquee">
        <div className="sign">
          <span className="est">Est. 1975 · Chapel St.</span>
          <h1>Campus Customs</h1>
          <span className="sub">Operations Desk</span>
        </div>

        <div className={`register ${chaching ? 'chaching' : ''}`} aria-live="polite" aria-label="Checking balance">
          <span className="reg-label">Checking</span>
          <span className="reg-digits">{balance === undefined ? '----.--' : money(balance)}</span>
          <span className="reg-foot">
            {cash && cash.pending_approval_total > 0
              ? <>Waiting on you {money(cash.pending_approval_total)} · after {money(cash.balance_if_all_approved)}</>
              : 'Nothing waiting on approval'}
          </span>
        </div>

        <button className="amp" onClick={turn} aria-label={`Amp at ${vol}: ${VOLUMES[vol].label}. Click to turn it.`}>
          <span className="knob" data-vol={vol} aria-hidden />
          <span className="amp-read"><b>{vol}</b><small>{VOLUMES[vol].label}</small></span>
        </button>
      </header>
      <div className="stripes" aria-hidden />

      {online === false && <div className="banner error" role="alert">{error} Is uvicorn running on :8000?</div>}
      {online && error && <div className="banner error" role="alert">{error}</div>}

      <main className="desk">
        {/* -------- The rail: order slips clipped on a wire -------- */}
        <section className="rail" aria-label="Tickets">
          <h2>The rail</h2>
          <div className="wire" aria-hidden />
          {tickets.length === 0 && <p className="empty">{online === null ? 'Tuning up…' : 'No tickets.'}</p>}
          {tickets.map((t, i) => (
            <button key={t.id} className={`slip tilt${i % 3}`} aria-pressed={t.id === selected}
              onClick={() => { setSelected(t.id); setEvents([]) }}>
              <span className="clip" aria-hidden />
              <span className="slip-no">#{t.id}</span>
              <span className="slip-kind">{TICKET_KIND[t.type] ?? t.type}</span>
              <strong>{t.subject}</strong>
              <span className="slip-who">{t.requester}</span>
              <span className="slip-what">
                {t.sku && <>{t.qty}× {t.sku} · {t.size}</>}
                {t.lease_id && <>Lease {t.lease_id}</>}
                {t.invoice_id && <> · Inv {t.invoice_id}</>}
              </span>
              <Stamp t={t} />
            </button>
          ))}
          <button className="ghost" disabled={running || !!busy}
            onClick={() => { if (confirm('Reset the working database to the original values?')) act('reset', api.reset) }}>
            {busy === 'reset' ? 'Resetting…' : '↺ Reset the shop'}
          </button>
        </section>

        {/* -------- The stage: the band and the live set -------- */}
        <section className="stage" aria-label="Agents">
          <div className="stage-head">
            <div>
              <h2>{ticket ? `#${ticket.id} · ${ticket.subject}` : 'Pick a ticket'}</h2>
              {ticket?.notes && <p className="muted">“{ticket.notes}”</p>}
            </div>
            <button className="go" disabled={!ticket || running || !!busy || ticket.is_resolved}
              onClick={() => ticket && act('run', () => api.run(ticket.id))}>
              {isLive(ticket) ? 'Band is playing…' : ticket?.is_resolved ? 'Resolved ✓' : '▶ Start the band'}
            </button>
          </div>

          <ul className="lineup">
            {LINEUP.map(a => (
              <li key={a} className={`member ${a} ${stage[a].mode}`}>
                <span className="glyph" aria-hidden>{AGENTS[a].glyph}</span>
                <span className="who"><b>{AGENTS[a].name}</b><small>{AGENTS[a].role}</small></span>
                <span className="vu" aria-hidden><i /><i /><i /><i /><i /></span>
                <span className="line">{stage[a].line}</span>
              </li>
            ))}
          </ul>

          <h3 className="tape">Live set</h3>
          <ol className="feed" ref={feedRef} aria-live="polite">
            {runEvents.length === 0 && <li className="empty">The stage is quiet. Pick a ticket and start the band.</li>}
            {runEvents.map((e, i) => <FeedLine key={i} e={e} />)}
          </ol>
          {ticket?.run?.status === 'error' && <div className="banner error">Run failed: {ticket.run.error}</div>}
          {ticket?.run?.status === 'done' && (
            <div className={`finale ${ticket.is_resolved ? 'resolved' : ''}`}>
              {ticket.is_resolved ? 'That’s a wrap. Ticket resolved.' : `Set’s over. Ticket is ${ticket.status.replace(/_/g, ' ')}.`}
            </div>
          )}
        </section>

        {/* -------- The checkbook + liner notes -------- */}
        <aside className="side">
          <section className="checkbook" aria-label="Approvals">
            <h2>Sign here</h2>
            <p className="muted small">Agents can only ask. You decide. Paying debits checking.</p>
            <label className="signer">
              Your name
              <input value={signer} placeholder="Who’s signing?"
                onChange={e => { setSigner(e.target.value); localStorage.setItem('cc-signer', e.target.value) }} />
            </label>
            {pending.length === 0 && <p className="empty">No payments waiting.</p>}
            {pending.map(a => (
              <article key={a.id} className="check">
                <div className="check-top"><span>No. {a.id}</span><span>Ticket #{a.ticket_id ?? '—'}</span></div>
                <div className="payto">Pay to the order of <b>{a.kind === 'rent' ? `Lease ${a.ref_id} rent` : `Invoice ${a.ref_id}`}</b></div>
                <div className="amount">{money(a.amount)}</div>
                <p className="memo">Memo: {a.reason}<br /><small>asked by {AGENTS[a.requested_by as AgentName]?.name ?? a.requested_by}</small></p>
                {cash && <p className="after">Checking after: <b>{money(cash.balance - a.amount)}</b></p>}
                <div className="check-actions">
                  <button className="approve" disabled={!signer.trim() || !!busy} onClick={() => pay(a)}>
                    {busy === `a${a.id}` ? 'Paying…' : 'Approve & pay'}
                  </button>
                  <button className="reject" disabled={!signer.trim() || !!busy}
                    onClick={() => { const r = prompt('Why reject?'); if (r) act(`r${a.id}`, () => api.reject(a.id, signer.trim(), r)) }}>
                    Reject
                  </button>
                </div>
                {!signer.trim() && <small className="hint">Type your name to sign.</small>}
              </article>
            ))}
            {decided.length > 0 && (
              <ul className="stubs" aria-label="Check stubs">
                {decided.map(a => (
                  <li key={a.id} className={a.status}>
                    <span>#{a.id} · {a.kind} {a.ref_id}</span><span>{money(a.amount)}</span>
                    <em>{a.status} by {a.decided_by}</em>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="liner" aria-label="What each agent did">
            <h2>Liner notes</h2>
            {boss && (
              <div className="verdict">
                <b>★ The call</b>
                <p>{boss.decision}</p>
                <span className="muted small">Final status: {boss.final_status}</span>
                {boss.customer_draft && <blockquote><span className="draft">Draft · not sent</span>{boss.customer_draft}</blockquote>}
              </div>
            )}
            {LINEUP.filter(a => a !== 'boss' && reports[a]).map(a => {
              const r = reports[a] as SpecialistReport
              return (
                <div key={a} className={`note ${a}`}>
                  <b><span aria-hidden>{AGENTS[a].glyph}</span> {AGENTS[a].name}</b>
                  <p>{r.summary}</p>
                  {r.actions_taken.length > 0 && <p className="small">Did: {r.actions_taken.join('; ')}</p>}
                  {r.blockers.length > 0 && <p className="small warn">Blocked: {r.blockers.join('; ')}</p>}
                  {r.draft_message && <blockquote><span className="draft">Draft · not sent</span>{r.draft_message}</blockquote>}
                </div>
              )
            })}
            {Object.keys(reports).length === 0 && <p className="empty">Notes show up as each agent finishes its part.</p>}
            {satOut.length > 0 && <p className="muted small">Sat this one out: {satOut.map(a => AGENTS[a].name).join(', ')}</p>}
          </section>
        </aside>
      </main>
    </>
  )
}

function FeedLine({ e }: { e: AgentEvent }) {
  const who = AGENTS[e.agent]
  const time = new Date(e.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  let body: ReactNode = null
  switch (e.event) {
    case 'run_start': body = <><em>picks up:</em> {e.said}</>; break
    case 'model_response':
      if (!e.said && !e.tools.length) return null
      body = <>{e.said && <span>{e.said} </span>}{e.tools.map((t, i) => <code key={i} className="cassette">{t}</code>)}</>
      break
    case 'tool_result': body = <span className="muted">← {e.tools.join(', ')} answered</span>; break
    case 'delegate': body = <><span className="handoff">➜ {AGENTS[e.to as AgentName]?.name ?? e.to}</span> {e.said}</>; break
    case 'delegate_refused': body = <span className="warn">Hand-off to {e.to} refused: {e.said}</span>; break
    case 'run_end': body = <b>Done: {e.detail?.output?.summary ?? e.detail?.output?.decision}</b>; break
    case 'error': body = <span className="warn">Error: {e.detail?.message}</span>; break
  }
  return (
    <li className={`bubble ${e.agent} ev-${e.event}`} style={{ marginLeft: `${Math.min(e.depth, 3) * 18}px` }}>
      <span className="by"><span aria-hidden>{who?.glyph}</span> {who?.name ?? e.agent} <time>{time}</time></span>
      <span className="said">{body}</span>
    </li>
  )
}
