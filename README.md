# FleetGuard AI

Predictive failure engine + agentic AI assistant for commercial fleets.
Turns raw weekly telematics into a live Green/Amber/Red risk score per
vehicle per part, a remaining-useful-life estimate, a fleet-wide
maintenance schedule, and a cost-impact view — all traceable back to
real signals, with an AI agent that reads the same data instead of a
separate, potentially-disagreeing source of truth.

---

## Why this exists

Commercial fleets mostly run reactive maintenance: a part fails, the
truck breaks down, and only then does anyone find out. The telematics
data that could have flagged it — coolant temp, oil pressure, battery
voltage sag, DTC recurrence, and five other weekly signals — is already
being collected. It's just not being turned into a warning. FleetGuard
AI closes that gap: correlate signals against real failure history,
build a per-part scoring rule from that correlation, score every
vehicle live, estimate how much life is left, and surface all of it
through a dashboard and a tool-calling AI agent that can answer
questions in plain language.

## Architecture

```
React (Vite + Tailwind)  ──REST/JSON──▶  FastAPI  ──SQLAlchemy ORM──▶  PostgreSQL
                                             │
                                             └──▶  Groq API (Llama 3.3 70B)
                                                    tool-calling agent, reads the
                                                    SAME service functions as the
                                                    REST API — never a separate
                                                    data path
```

Everything the dashboard shows and everything the agent says is
computed by the same three service-layer engines:

1. **Correlation Engine** (`services/correlation.py`) — point-biserial
   correlation + XGBoost feature importance, ranking which of the 9
   weekly telematics signals actually predict failure for a given part.
2. **Scoring Engine** (`services/scoring.py`) — z-score each signal
   against the fleet population, weight by the saved rule, sum, pass
   through a sigmoid calibrated with a base-rate intercept → failure
   probability → Green/Amber/Red tier.
3. **RUL Engine** (`services/rul.py`) — the same score, compressed onto
   the part's design-life mileage via quadratic compression, so RUL and
   risk tier can never contradict each other.

### Planned deployment (Azure)

| Local (current) | Azure (planned) |
|---|---|
| Vite dev server | Static Web Apps (CDN) |
| Uvicorn / FastAPI | App Service |
| Local PostgreSQL | Azure Database for PostgreSQL (Flexible Server) |
| `.env` secret | Azure Key Vault (`GROQ_API_KEY`) |

See `docs/azure-deploy-guide.md` (or wherever you've saved it) for the
full step-by-step.

## Data model

Two dimension tables (`vehicles`, `parts`) anchor everything else, which
records either an event or a rule against them:

| Table | Role |
|---|---|
| `vehicles` | vin (PK), model, region, registration_date, total_km_driven |
| `parts` | part_code (PK), part_name, category, design_life_km |
| `telematics_weekly` | 9 weekly signal columns per vin, per week |
| `failures` | job_card_id (PK), vin, part_code, failure_date, odometer_at_failure_km |
| `predictions` | vin, part_code, failure_probability, risk_tier, rul_km, rul_days, computed_date |
| `rule_config` | part_code, signal, correlation_weight, method — the saved scoring rule |
| `users` | login accounts (email/password + Microsoft SSO via MSAL) |

The AI agent has **no table of its own** — it's fully stateless and reads
`predictions` / `rule_config` directly through the same service
functions the REST API uses.

## Features

### Authentication
- Email + password sign-in for demo accounts
- Microsoft SSO (MSAL) for enterprise fleet operators
- Role-based access: admins see the full fleet, fleet owners see only
  their own vehicles

### Rule Builder
Correlate telematics signals against real failure history (point-biserial
r and XGBoost importance side by side), then build an editable per-part
scoring rule — uncheck a signal to exclude it and weights renormalize
automatically. One saved, versioned rule per part, applied instantly
everywhere else that part is scored.

### Failure Probability
Fleet-wide ranked list (400 vehicles, filterable by tier), one-click
"Run Scoring" to recompute live, and a per-vehicle drill-down showing
which signals are driving the prediction plus a 6-week probability trend.

### RUL Explorer
Remaining useful life (days/km) per vehicle/part, baseline mileage life
vs. risk-adjusted RUL side by side, and an Action Agent that drafts an
outreach message for at-risk vehicles — always a draft, never auto-sent.

### Maintenance Calendar
Fleet-wide timeline across **every** vehicle and **every** part (not just
the currently-selected part), bucketed by urgency — due now, this month,
this quarter, later. Built entirely from RUL data that's already been
computed; no new calculation. Click any row to jump to that vehicle's
detail.

### Cost Impact
Turns real Red/Amber-tier counts into an estimated dollar figure for
cost avoided by catching failures early, broken down by part category.
The vehicle counts are real; the cost-per-catch number is a **user-set,
editable input** (defaults to $0, not a hardcoded guess) so the page is
honest about which numbers are measured and which are assumptions.

### VIN Search
Debounced search bar in the top bar; type a full or partial VIN, get a
dropdown of matches, click through straight to that vehicle's detail.

### Notifications + live badges
- Bell icon showing current Red-tier count for the selected part, with a
  dropdown to jump to a vehicle
- Matching badge on the Failure Probability tab (same underlying fetch,
  so they can never disagree)
- "Last scored" pill showing real wall-clock time since you last clicked
  "Run Scoring" this session (not the fixed simulation date, which never
  changes regardless of when you actually run scoring)

### Export
One-click CSV export of the current (filtered) ranked list on Failure
Probability.

### Insight Agent
Tool-calling chat assistant (Groq / Llama 3.3 70B, 7 tools: `list_parts`,
`get_correlation`, `get_predictions`, `get_prediction_detail`, `get_rul`,
`compare_parts`, `find_vehicle`). Answers plain-language fleet questions
by making real function calls against the same data the dashboard shows
— every number in a reply traces back to an actual tool call, never
invented.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Data / ML | pandas, NumPy, SciPy, scikit-learn, XGBoost |
| Database | PostgreSQL |
| AI | Groq (Llama 3.3 70B), custom tool-calling agent |
| Dev tooling | Python 3.12+, GitHub, VS Code |

## Project structure

```
backend/
  app/
    api/            # FastAPI routers — parts, predictions, rul, agent, auth, vehicles, maintenance
    services/        # correlation, scoring, rul, rule_builder, features (the 3 engines)
    agent/           # tools.py (7 tool definitions + executors), action.py (draft_outreach)
    models/          # SQLAlchemy models — core, rules, telematics, failure, user
    schemas/         # Pydantic request/response models
    core/            # database session, auth/JWT, config
  alembic/           # migrations
  scripts/           # generate_data.py, seed_demo_users.py, seed_predictions.py, validate_data.py

frontend/
  src/
    pages/           # OverviewPage, RuleBuilderPage, FailureProbabilityPage, RULExplorerPage,
                      # MaintenanceCalendarPage, CostImpactPage, Login
    components/       # TopBar, TopTabs, Sidebar, ChatPanel, VinSearch, NotificationBell,
                      # LastScoredBadge, RiskBadge, chart components
    hooks/            # usePartContext — shared part selection + Red-tier alert state
    api/client.js     # all backend calls
    context/          # AuthContext
```

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
# requirements.txt is currently missing python-jose, which core/auth.py needs:
pip install python-jose

# .env — DATABASE_URL, JWT_SECRET_KEY, GROQ_API_KEY, AZURE_TENANT_ID, AZURE_CLIENT_ID
alembic upgrade head
python scripts/generate_data.py      # seeds 400 vehicles, 5 parts, 52 weeks of telematics, ~227 failures
uvicorn app.main:app --reload         # http://127.0.0.1:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                           # http://localhost:5173, VITE_API_BASE_URL in .env
```

**First run, in order:** Rule Builder (save a rule for a part) → Failure
Probability (Run Scoring) → RUL Explorer (Run RUL for this part). Do this
per part — Maintenance Calendar and Cost Impact are fleet-wide across
all parts, so the more parts you've scored, the fuller they are.

## Known performance note

`run_rul_for_part` used to recompute fleet-wide population stats from
scratch on every single vehicle it scored — O(n²) database queries.
Fixed by computing those stats once per run and passing them through
(`services/scoring.py` / `services/rul.py`). Verified: ~63s → ~0.76s for
a 400-vehicle fleet.

## License

Internal training project — Aays.
