# FleetGuard AI — Frontend

React + Vite + Tailwind, wired to the FastAPI backend from Days 1-6.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173. The backend must already be running at
http://127.0.0.1:8000 (via `uvicorn app.main:app --reload` in the `backend`
folder) — `.env` points `VITE_API_BASE_URL` there by default; change it if
your backend runs somewhere else.

## Before you look at Failure Probability or RUL Explorer

Those two screens read from the `predictions` table, which only gets
populated when you run scoring. If a screen looks empty:
1. Go to **Rule Builder**, pick a part, save a rule (or just use the
   default pre-checked signals).
2. Go to **Failure Probability**, click **Run Scoring**.
3. Go to **RUL Explorer**, click **Run RUL for this part**.

After that, both screens have real data to show. Re-run these anytime you
regenerate synthetic data or rebuild a rule.

## Design

- **Palette**: dark instrument-panel theme (`#10141A` background), with
  three risk colors (green/amber/red) used consistently everywhere a risk
  tier appears, plus one cyan "signal" accent for interactive/agent
  elements.
- **Type**: Space Grotesk (headings), Inter (body), JetBrains Mono (VINs,
  part codes, probabilities, RUL figures — numbers are the actual content
  here, so they get an instrument-readout treatment).
- **Signature element**: the **Signal Arc** (`src/components/SignalArc.jsx`)
  — a 270° radial gauge used everywhere a probability is shown, instead of
  a generic progress bar. It's the same visual language as the vehicle
  sensor gauges (coolant temp, oil pressure) this whole product reads —
  someone reading fleet risk is themselves reading a gauge.

## Structure

```
src/
  api/client.js          — every backend call, one place
  constants.js           — risk colors, telematics signal list/labels
  components/
    SignalArc.jsx         — signature gauge component
    RiskBadge.jsx, Sparkline.jsx, EmptyState.jsx, Loading.jsx
    Sidebar.jsx, TopBar.jsx — layout chrome
    ChatPanel.jsx          — persistent Insight Agent panel
    ErrorBoundary.jsx      — catches render errors per-page instead of
                              going to a blank screen (see note below)
  hooks/usePartContext.jsx — shared "which part is selected" state
  pages/
    RuleBuilderPage.jsx
    FailureProbabilityPage.jsx  — ranked list + drill-down detail
    RULExplorerPage.jsx          — probability + RUL side by side,
                                    plus the Action Agent draft button
```

## A bug worth knowing about (already fixed, but useful context)

The `/predictions/{vin}/{part_code}` endpoint returns `top_signals` as a
comma-joined **string** (matching its Pydantic schema), but the first
version of the Failure Probability drill-down panel called `.map()` on it
as if it were an array. That crashed the render with no error boundary in
place, producing a **silent blank page** — confirmed via an actual
screenshot, not just by reading the code. Fixed by splitting the string
correctly, and an `ErrorBoundary` was added around the routed page content
so any *future* rendering bug shows a message and a retry button instead
of a blank screen — worth having before a live demo.

## Chat panel behavior

`ChatPanel.jsx` carries `conversation_history` forward between messages
(returned opaquely by `/agent/chat` and passed back on the next call) so
it's a real multi-turn conversation, not single-shot Q&A. Each reply shows
which backend tools were called and their raw results in a collapsible
chip — this is the visible proof that answers are grounded in live data,
not invented, matching the brief's requirement.
