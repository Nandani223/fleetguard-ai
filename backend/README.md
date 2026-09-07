# FleetGuard AI — Backend

## Day 1 status: Postgres + schema-as-code — DONE

### What's set up
- PostgreSQL 16 running locally (service, not Docker in this sandbox — swap to
  the Docker command below on your own machine if you prefer containerized).
- Database `fleetguard_db`, user `fleetguard` (see `.env` for the connection string).
- 6 tables created via SQLAlchemy models + Alembic migration, matching Section 5
  of the brief:
  - `vehicles` (Vehicle Master)
  - `parts` (Part Master)
  - `failures` (Job Card / Failure History)
  - `telematics_weekly` (Telematics Signals, weekly aggregate)
  - `rule_config` (persisted per-part scoring rule)
  - `predictions` (fleet-wide scoring + RUL output)
- Real foreign keys enforced: `failures.vin/part_code`, `telematics_weekly.vin`,
  `rule_config.part_code`, `predictions.vin/part_code` all reference their
  parent tables — verified by attempting an insert with a bad `part_code` and
  confirming Postgres rejects it (`IntegrityError`).
- A `CHECK` constraint on `predictions.risk_tier` restricts it to
  `Green` / `Amber` / `Red`.
- Unique constraints: `(vin, week_start_date)` on telematics,
  `(part_code, signal, method)` on rule_config, `(vin, part_code, computed_date)`
  on predictions — so re-running the scoring engine on the same day
  overwrites/upserts rather than silently duplicating rows.

### Schema deviations from the brief (and why)
- `rule_config` has an extra `method` column (`logistic_regression` |
  `xgboost_importance`) since Day 3 plans to compute both correlation methods
  side-by-side, not just one — the brief allows "you choose and justify."
- `predictions` includes both `rul_km` and `rul_days` (brief just says
  "RUL (km/days)") since the RUL estimator (Day 5) will produce both units,
  and splitting them avoids ambiguous parsing of a combined string field.
- `top_signals` is stored as a comma-separated string for now (simplest
  representation for a capstone scope); a normalized child table would be
  the "more correct" version if this were a production system.

### Local setup (reproducing this from scratch)
```bash
# Postgres via Docker (recommended outside this sandbox)
docker run -d --name fleetguard-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16

# create db + user (adjust for docker exec if using the container above)
psql -h localhost -U postgres -c "CREATE USER fleetguard WITH PASSWORD 'fleetguard_dev_pw';"
psql -h localhost -U postgres -c "CREATE DATABASE fleetguard_db OWNER fleetguard;"

# python deps
cd backend
pip install -r requirements.txt

# apply schema
alembic upgrade head
```

### Verify it worked
```bash
psql -h localhost -U fleetguard -d fleetguard_db -c "\dt"
```
You should see: `vehicles`, `parts`, `failures`, `telematics_weekly`,
`rule_config`, `predictions`, `alembic_version`.

## Day 2 status: Synthetic data generator — DONE

### What's generated
Running `python scripts/generate_data.py` populates:
- **5 parts**: Alternator, Radiator, Brake Pads, Suspension Bushings, Turbocharger
- **400 vehicles**: realistic VINs, 4 models, 4 regions, registration dates
  spread over ~6 years, usage intensity varying per vehicle (some drive ~3x
  the monthly km of others)
- **20,800 weekly telematics rows** (400 vehicles × 52 weeks): 9 signals per
  row (coolant temp variance, oil pressure dips, battery voltage sag, DTC
  recurrence, harsh braking frequency, overload duty share, high-RPM dwell,
  short-trip ratio, idle time)
- **227 failure records** across all 5 parts (target was 150-250 — comfortably in range)

### Layered realism (not just one flat correlation)
1. **Primary signal**: each vehicle has a latent "alternator degradation
   rate" that drives BOTH its coolant/oil/battery telematics AND its
   alternator failure probability — a genuine common-cause relationship,
   not a copied label.
2. **Regional confounder**: North region has 1.35x "road roughness" vs.
   0.85-1.05x elsewhere. This elevates harsh-braking/overload telematics
   AND wear-based failure probability for Chassis/Engine parts (brake pads,
   suspension, turbo) — but NOT the radiator, which has no regional
   modifier and acts as a control to prove the effect is real.
3. **Seasonality**: coolant temp variance carries a summer bump independent
   of vehicle-level degradation.
4. **Heterogeneity**: registration age and usage intensity vary per vehicle
   for realistic odometer spread (23K–678K km across the fleet).

### Validation (run `python scripts/validate_data.py`)
Confirms the signal is actually discoverable, not just intended:
- Alternator failure correlates with coolant variance (r=0.50), oil
  pressure dips (r=0.45), battery sag (r=0.50) — all p<0.00001. Moderate-
  strong, not suspiciously perfect.
- North region failure rate is clearly higher for brake pads (0.134 vs.
  0.095 elsewhere), suspension (0.155 vs. 0.091), turbo (0.124 vs. 0.049),
  while the radiator control stays flat (spread 0.03) across regions.

### Files
- `scripts/reference_data.py` — every tunable constant (scale, regions,
  wear model coefficients, alternator model coefficients) in one place
- `scripts/generate_data.py` — the generator itself (reproducible, fixed
  seed = 42; re-running it wipes and regenerates all 4 tables)
- `scripts/validate_data.py` — automated pass/fail checkpoint

### Next: Day 3
Correlation engine + Rule Builder backend — compute signal correlations
two ways (logistic regression + XGBoost importance) and persist a
weighted scoring rule per part.

---

## Day 3 status: Correlation Engine + Rule Builder backend — DONE

### Endpoints (FastAPI, run with `uvicorn app.main:app --reload`)
- `GET /parts` — list all 5 parts
- `GET /parts/{part_code}/correlation` — per-signal correlation, two methods
- `POST /parts/{part_code}/rule` — build + persist a weighted rule from a
  chosen method and include/exclude signal selection
- `GET /parts/{part_code}/rule?method=...` — retrieve the persisted rule

### Method choice: point-biserial + XGBoost (not logistic regression)
The brief allows point-biserial, logistic regression coefficients, or
XGBoost importance — pick and justify. **Logistic regression was tried
first and dropped** after validation caught a real problem: coolant/
battery/DTC signals are 85-98% correlated with each other (all driven by
the same latent alternator-degradation variable in the synthetic data),
so an unregularized multivariate model couldn't tell them apart and
assigned a huge, misleading coefficient to `coolant_temp_variance` even
for parts with **zero** true relationship to it (verified: raw
point-biserial r≈0.00 for coolant vs. brake-pad failure, while logistic
regression ranked it #1). Point-biserial correlation is computed
per-signal independently, so it doesn't have this problem — and it's a
better fit for the Rule Builder UX anyway, since a multivariate
coefficient changes every time you toggle a different signal on/off,
while a marginal statistic stays meaningful regardless of what else is
included.

### Second bug caught during validation: the feature lookback window
Original design: for a failed vehicle, use the 8 weeks of telematics
*right before* its failure_date. This diluted the measured correlation
significantly (coolant r dropped from ~0.50 to ~0.28) because the
synthetic data samples failure timing independently of how far a
vehicle's degradation had actually progressed — so a high-risk vehicle
could randomly get an early failure date, before its signals had ramped
up. Fixed by using each vehicle's most recent 8 weeks of the observation
window for everyone, which also matches how the model is actually
applied at inference time (score current telematics → predict risk).

### Results (see `scripts/reference_data.py` for the underlying model)
- **Alternator**: DTC recurrence, coolant variance, battery sag, oil
  pressure dips all show r≈0.45–0.51 — the primary signal, as designed.
- **Suspension & Turbocharger**: harsh-braking and overload duty share
  are the *top* signals (r≈0.10–0.23) — the regional confounder
  correctly surfacing through telematics, even though the wear model
  itself uses odometer (not a telematics signal) as its main driver.
- **Radiator (control part)**: everything near-zero (r<0.10) — correctly
  shows no relationship, since it was deliberately built with no
  regional effect, confirming the confounder signal on other parts is
  real rather than a generation artifact.
- **Brake pads**: weak across the board — expected, since its wear cap
  saturates for most vehicles regardless of region (see Day 2 notes).

### Weight persistence convention
`rule_config.correlation_weight` is normalized so all *included* signals'
absolute weights sum to 1. `raw_score` stores the original, unnormalized
correlation/importance value so it's recoverable later without
recomputation. Point-biserial weights keep their sign (a negatively
correlated signal pulls score down); XGBoost importances are unsigned, so
the scoring engine (Day 4) treats "higher value → higher risk" under that
method — a simplification worth a sentence in the design note.

### Next: Day 4
Failure Probability Scoring Engine — apply the persisted rule fleet-wide
to produce probability %, risk tier, top contributing signals, and trend,
plus the backtest (hold out last month's failures, check early detection).

---

## Day 4 status: Failure Probability Scoring Engine — DONE

### Endpoints (added to the same FastAPI app)
- `POST /predictions/run` — score the whole fleet for one part using its
  persisted rule; body: `{part_code, method, as_of_date?}`
- `GET /predictions?part_code=&risk_tier=&computed_date=&limit=&offset=` —
  ranked list (Red first, then Amber, then Green; highest probability
  first within a tier)
- `GET /predictions/{vin}/{part_code}?method=` — drill-down detail: live
  probability, risk tier, top 3 contributing signals, and a 6-week
  probability trend (not persisted — computed on demand, reusable later
  by the Insight Agent's tool calls)

### Scoring method
1. z-score each included signal against the fleet population (mean/std
   from every vehicle's current 8-week-average — same feature
   representation the correlation engine trained on).
2. Weighted sum of z-scores using the rule's persisted weights.
3. Squash through a sigmoid, **shifted by a base-rate intercept** (see bug
   below), to get a 0-1 probability.
4. Risk tier from fixed thresholds: Green <0.30, Amber 0.30-0.60, Red
   ≥0.60 (documented in `scoring.py`, easy to retune).
5. Trend: same scoring logic applied to 6 **rolling 3-week-average**
   points, not 6 raw single weeks (see second bug below).

### Bug #1 caught during validation: uncalibrated probabilities
First version used a symmetric sigmoid centered at zero. Discrimination
was already good (AUC 0.79-0.86 for alternator/turbo — the model ranked
failed vehicles correctly), but calibration was badly off: 48% of the
whole alternator fleet landed in Red tier despite a true failure rate of
20%. Fixed with a base-rate intercept (logit of the part's true
historical failure rate) added to the sigmoid input — the standard fix,
equivalent to what a properly-fit logistic regression's intercept term
supplies automatically. After the fix: Red tier count dropped to a
realistic 117/400 for the alternator, and 58/80 (73%) of vehicles that
actually failed now correctly land in Red. AUC unchanged (0.856), as
expected — this was a calibration problem, not a ranking problem, and a
monotonic sigmoid shift doesn't change rank order.

### Bug #2 caught during validation: noisy single-week trend
First version scored each of the last 6 weeks individually using that
week's raw (un-averaged) signal values. For a real Amber-tier vehicle,
this produced a trend of `[0.69, 0.11, 0.94, 0.24, 0.88, 0.59]` — useless
for a demo or a human reading it, because single-week count-based signals
(e.g. `oil_pressure_dips`) swing too much on their own. Fixed by using a
3-week rolling average for each trend point instead of a single raw
week; the same vehicle's trend is now `[0.60, 0.38, 0.62, 0.46, 0.77,
0.60]` — still shows real week-to-week variance (this is noisy synthetic
telematics, not a smooth curve, and shouldn't look artificially clean)
but is readable and demo-usable.

### Graceful degradation for weak-signal parts
Brake pads (CHS-0330) have no telematics signal above r=0.08 (see Day 3
notes — wear here is genuinely driven by mileage, not captured in
telematics). Rather than hard-failing the scoring run for a part with an
intentionally-empty rule, the engine falls back to the part's historical
base failure rate as a flat probability for every vehicle, tier Green,
and marks `top_signals="insufficient_signal"` so the frontend/agent can
tell this isn't a real per-vehicle signal, not silently present it as one.

### `estimated_window_days`
A lightweight heuristic (weeks until the trend would cross into Red,
based on trend slope), computed here as a placeholder. Day 5's RUL
Estimator will cross-check this against actual remaining-life math so the
two numbers agree, per the brief's requirement that they "tell a
consistent story."

### Next: Day 5
RUL Estimator — remaining km/days from design life vs. observed
degradation, cross-checked against this scoring engine's output for the
same VIN/part so both numbers move together.

---

## Day 5 status: RUL Estimator — DONE

### Endpoints
- `GET /vins/{vin}/parts/{part_code}/rul?method=` — live detail: RUL
  km/days, the failure probability + risk tier it was derived from, and a
  `consistent` flag
- `POST /rul/run` — batch: computes RUL for every vehicle already scored
  by `/predictions/run` for a part, and **updates** those existing
  Prediction rows (doesn't create new ones)

### How consistency is actually guaranteed, not just checked
The brief requires RUL and failure probability to "tell a consistent
story rather than reading like a second, unrelated opinion." Rather than
building a second risk model and hoping the two agree, RUL is
**mathematically derived from Day 4's scoring output**: it calls
`score_single_vehicle` — the exact same function, same rule, same
signals — and uses that probability to compress a mileage-only baseline
(design life vs. current odometer, no telematics involved). There's no
way for the two numbers to disagree, because one is a function of the
other, not a parallel computation.

### Bug caught during validation: adjustment curve too gentle at high risk
First version used a linear compression (`remaining = baseline × (1 -
0.85×probability)`). A vehicle at 99.99% failure probability but
mileage-young for that part (large baseline) came out to **185 days** of
RUL — mathematically consistent by construction, but contradicts what a
Red tier should communicate (imminent, not "somewhat reduced"). Switched
to quadratic compression (`(1-probability)²`): the same vehicle now shows
**25 days**, while a Green-tier vehicle at 30% probability still retains
a reasonable 71 days (49% of its baseline). Verified by rechecking the
same VIN before/after the fix, not just trusting the new formula looked
better on paper.

### Next: Day 6
Insight Agent — Claude API with tool-calling against the same service
functions the REST API uses, so it can never see numbers that differ
from the dashboard. Plus the optional Action Agent (outreach drafting).

---

## Day 6 status: Insight Agent + Action Agent — DONE (LLM loop untested — see below)

### Setup required
Add your Groq API key to `.env`:
```
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```
Without a key, both endpoints fail gracefully with a clear message
instead of crashing (verified) — useful for confirming the rest of the
pipeline works before spending API credits.

Groq's API is OpenAI-compatible, not Anthropic's Messages API, so the
tool-calling loop (`app/agent/agent.py`) and tool schema
(`app/agent/tools.py`'s `TOOL_DEFINITIONS`) use the OpenAI/Groq
`{"type": "function", "function": {...}}` shape and a `role: "tool"`
message pattern for returning results — not Anthropic's `tool_use`/
`tool_result` content blocks. If you switch providers again later, this
is the part that needs rewriting; the tool executors themselves
(`app/agent/tools.py`'s `TOOL_EXECUTORS`) are provider-agnostic and don't
need to change.

### Endpoints
- `POST /agent/chat` — conversational, tool-calling Insight Agent. Body:
  `{"message": str, "conversation_history": [...] }` (pass back the
  `conversation_history` from the previous response to continue a thread;
  omit/empty for a new conversation). Returns `reply`, `tool_calls` (which
  tools fired and what they returned — useful for showing the frontend
  "grounded in live data, not invented"), and `conversation_history` to
  carry forward.
- `POST /agent/draft-outreach` — Action Agent (optional stretch, built).
  Body: `{"vin": str, "part_code": str}`. Deterministically fetches
  prediction + RUL data first, then makes one Claude call to draft a
  message. Never sends anything — returns a draft string only.

### Design: tools call service functions directly, not HTTP
Both agents' tools (`app/agent/tools.py`) call the same
`app.services.*` functions the REST API endpoints call — not HTTP
requests to the backend's own API. One source of truth; the agent
literally cannot see different numbers than the dashboard shows, by
construction, not by convention.

### 7 tools built
`list_parts`, `get_correlation`, `get_predictions`, `get_prediction_detail`,
`get_rul`, `compare_parts`, `find_vehicle` (handles loose references like
a partial VIN — tested: searching "XFD082" correctly found the matching
vehicle). All 7 were tested directly against real data before wiring up
the LLM loop and returned correct, live values matching Days 3-5's
verified output.

### What's verified vs. not yet verified
- **Verified**: all 7 tool executors return correct data; both endpoints
  are registered and reachable; the no-API-key fallback works cleanly for
  both agents (confirmed via live requests); the Action Agent's grounding
  fetch (get_prediction_detail + get_rul) works independently of the LLM
  call.
- **Not yet verified** (no API key available in the dev sandbox this was
  built in): the actual live Claude tool-calling loop — whether it
  correctly chains tool calls, resolves loose VIN references through
  `find_vehicle` on its own, and answers the 5 required sample questions
  end-to-end. **This needs to be tested with a real API key before it can
  be called done** — see the checklist below.

### To verify before demo/submission
1. Add a real `ANTHROPIC_API_KEY` to `.env`, restart the server.
2. Test all 5 required sample questions via `POST /agent/chat`:
   - "Which vehicles are red-tier this week?"
   - "Why is this VIN's alternator at X%?" (use a real VIN from a
     `/predictions` call)
   - "Compare durability of Part A vs Part B" (e.g. ELC-0152 vs CHS-0330)
   - "What's the RUL for VIN ___?"
   - "Which signals are driving risk for Part X?"
3. Ask something with no data available (e.g. a nonexistent VIN) and
   confirm it says so rather than inventing a number.
4. Try a loosely-phrased VIN reference and confirm `find_vehicle` gets
   called automatically.
5. Try `/agent/draft-outreach` on a real Red-tier VIN and read the draft
   for tone/relevance.

### Next: Day 7
Frontend foundation — Rule Builder + Failure Probability screens, wired
to the real endpoints built in Days 3-4.
