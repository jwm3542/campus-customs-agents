# Campus Customs Ops Desk: Dashboard Design

The board lives in `frontend/` (React + Vite + TypeScript). It runs at `http://localhost:5173` and calls the FastAPI routes at `http://localhost:8000`. The backend's CORS setting allows the `localhost:5173` and `127.0.0.1:5173` origins.

## The idea: a record-shop back counter

Campus Customs is a little print shop on Chapel Street, so the desk should look like the counter behind the register, not a SaaS admin panel. Every piece of the screen is an object that would actually sit on that counter:

- order slips on a wire
- a cash register
- a checkbook
- the band playing on the shop stereo

The metaphor does real work. When a part looks like the object it stands for, you already know how to use it, so nobody has to learn the dashboard. That's what makes it a desk people would want to sit at.

## Layout: three columns, read left to right like the work flows

| Column | What it is | Why |
|---|---|---|
| **The rail** (left) | The three tickets hang as order slips clipped to a steel wire. Each one is tilted a little, the way slips are on a real kitchen rail. | You pick work the way a cook grabs the next slip. The rail stays put, so you can see the whole queue at a glance. |
| **The stage** (center, widest) | The ticket header with a big **▶ Start the band** button, the five-agent lineup, and the **Live set** feed underneath. | Watching the agents work is the main show, so it gets the most room. |
| **Sign here + Liner notes** (right) | The checkbook of pending payments, then a short summary of what each agent did. | Your decisions and the takeaways sit together, in the spot where your eye lands when the run ends. |

The header is a marquee: the shop sign, the **cash register**, and the **amp knob**. Above it runs a permanent brick-red strip: *"Practice desk · Agents only draft. No customer is emailed and no real vendor is called. Money moves only when a human signs."*

It's responsive. Under 1200px the right column drops below the stage. Under 760px everything stacks.

## How the agents read differently

The agents are the house band. Each one always stands in the same spot, with the same color, glyph, and role, so after one run your eye knows who is who without reading:

| Agent | Glyph | Color (volume 7) | Band role |
|---|---|---|---|
| The Boss | ★ | Yale navy | Frontman: calls the play |
| Inventory | ▤ | Green | Rhythm guitar: the stockroom |
| Accounting | $ | Brass | Bass: the ledger |
| Facilities | ⌂ | Brick | Drums: the building |
| Customer Service | ♪ | Orange | Vocals: the counter |

Each member card has a **VU meter**. It bounces while that agent is thinking, using a tool, or waiting on a hand-off. It sits half-lit when the agent is done. Idle agents are dimmed, so **you can see at a glance which agents the Boss actually called**. That matters, because Problem 6 says calling everyone scores low. A one-line status under the meter says what the agent is doing right now, for example "Using get_invoice" or "Waiting on Accounting".

The **Live set** feed is the play-by-play, pulled from `/api/events`:

- Each line carries the agent's color stripe.
- Tool calls show as little cassette labels (`check_inventory`).
- Hand-offs show as orange arrows ("➜ Accounting").
- Refused hand-offs are flagged in red.
- Each line is indented by delegation depth, so you can see the chain Boss → Inventory → Accounting as nesting.

The board polls every 1.5 s while a run is going and every 6 s otherwise.

## How resolved tickets show up

Each slip on the rail gets a rubber **stamp**:

- **Open** (blue)
- **On stage** (red, pulsing while the team works)
- **Needs your OK** (orange, when a payment is waiting)
- **Resolved** (green)

When a run ends, a banner under the feed reads either "That's a wrap. Ticket resolved." or "Set's over. Ticket is waiting approval." Once a ticket is resolved, its Start button reads **Resolved ✓** and is locked, so nobody spends tokens re-running finished work.

**Liner notes** carry the short summary for each agent. The Boss's final call comes first, then one note per specialist (summary, what it did, what blocked it), and a line saying who "sat this one out". Any customer message has a **Draft · not sent** tag, because we never email customers.

## How cash shows up and drops

The **cash register** in the header shows the checking balance from `/api/cash` in green LCD digits. Under it, it shows how much is waiting on approval and what checking would be after those payments.

When you **Approve & pay**:
- The digits **roll down** from the old balance to the new one, for example $3,400.00 → $2,560.00.
- The register drawer bumps (cha-ching) and the digits flash gold.
- The check turns into a stub under the checkbook, marked "approved by <your name>".

That makes the money moving impossible to miss.

## Human approval: the checkbook

Agents can only **request** a payment. Every pending request shows up as a green, security-patterned **check**: No., ticket, pay-to, amount, memo, which agent asked, and **what checking will be after**. The Approve & pay and Reject buttons stay disabled until you type your name in **Your name**. That name goes to the backend as `approved_by` and is recorded on the payment. The backend refuses any payment that would take checking negative, and the error shows in a red banner.

## The amp knob: four eras, one desk

The knob in the header (remembered in `localStorage` as `cc-volume`) turns the whole desk through four eras of American music, quiet to loud: 3 → 5 → 7 → 11. Nothing moves, only the mood changes:

- **5 · 1956, rockabilly**: the bridge from big band to rock. Mid-century diner: turquoise and cherry red on cream formica with boomerang and starburst flecks, a black-and-white checkerboard strip, a Pacifico script sign, chrome register, rounded pill buttons. Upbeat for a busy afternoon.
- **7 · 1975, the shop** (the default): walnut paneling, brass trim, mustard/orange/brick stripes, the Rye saloon-sign font, and warm paper slips.
- **11 · 1984, one louder**: black and chrome, Metal Mania lettering with a red glow, and neon agent colors on dark panels. For late nights.
- **3 · 1938, big band**: art deco green and gold, Limelight and Josefin Sans fonts, square corners with double gold frames, and a chevron border. Calm and elegant for paying bills.

## Accessibility and polish

- Text contrast stays readable at every volume.
- Every control has a label. Ticket slips use `aria-pressed`.
- The feed and the register are `aria-live`, so screen readers hear progress and balance changes.
- `prefers-reduced-motion` turns off the VU meters, the pulsing, and the roll-down animations.
- Loading ("Tuning up…"), empty, and error states are all spelled out. If the backend is down, the banner says so and asks whether uvicorn is running on :8000.
- **↺ Reset the shop** asks for confirmation, then calls `/api/reset`. It's locked while a run is going.
