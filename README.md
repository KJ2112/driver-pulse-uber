# Driver Pulse: Team[]
### Uber Hackathon Submission

Driver Pulse gives drivers two things they currently don't have: a clear record of stressful or conflict moments during their trips, and a live earnings tracker that tells them whether they are on pace to hit their daily goal.

Built for the Uber Hackathon by team -

---

## What It Does

**Stress Detection**
The system fuses accelerometer and audio signals to detect four types of events during a trip:

| Event | What It Means |
|---|---|
| `conflict_moment` | High lateral force AND sustained loud audio — possible argument |
| `harsh_braking` | Sudden deceleration spike, audio was calm |
| `audio_spike` | Sustained loud cabin audio for 30+ seconds, no harsh motion |
| `moderate_brake` | Moderate lateral force, within cautionary range |
| `sustained_stress` | Prolonged elevated readings across both signals |

Each event gets a severity (HIGH / MEDIUM / LOW), a combined stress score, and a plain English explanation.

**Earnings Velocity**
Tracks whether a driver is on pace to hit their daily earnings goal using a live run-rate calculation:

```
current_velocity  = earnings_so_far / active_hours
required_velocity = target / total_shift_hours
projected         = earnings_so_far + current_velocity × remaining_hours
```

Handles two edge cases explicitly:
- **Cold start** — in the first 30 minutes, falls back to the driver's historical average so the forecast isn't based on too little data
- **Idle time** — velocity is computed on active trip time only, so waiting between rides doesn't unfairly tank the number

---

## Project Structure

```
driver_pulse/
├── data/
│   ├── accelerometer_data.csv
│   ├── audio_intensity_data.csv
│   ├── trips.csv
│   ├── drivers.csv
│   ├── driver_goals.csv
│   └── earnings_velocity_log.csv
├── src/
│   ├── data_ingestion.py      # DataLoader class — loads and cleans all 6 CSVs
│   ├── signal_processing.py   # SignalProcessor, RealSensorFusion, SyntheticFlagGenerator
│   ├── earnings_forecast.py   # EarningsForecaster, DriverGoal, ShiftSummary
│   └── trip_summarizer.py     # TripSummarizer, TripStressAnalyzer
├── outputs/
│   ├── flagged_moments.csv
│   ├── trip_summaries.csv
│   └── earnings_status.csv
├── app.py                     # Streamlit dashboard
├── main.py                    # Pipeline runner
└── requirements.txt
```

---

## How To Run

**1. Create and activate a virtual environment (Recommended)**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```
*(Alternatively, you can install directly: `pip install pandas numpy streamlit`)*

**3. Run the pipeline** (generates output CSVs)
```bash
python main.py
```

**4. Launch the dashboard**
```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Dashboard

**Dashboard Login**
When you open the dashboard, you will be prompted to enter a **Driver ID**. You can enter an existing ID from the dataset (e.g., `DRV001`) to log in and view the driver metrics.

**Tab 1 — Earnings Tracker**
Shows ON TRACK or AT RISK status, current vs required velocity, progress bar toward daily goal, and a breakdown of active vs idle time.

**Tab 2 — Trip Review**
Each trip is an expandable card showing fare, duration, stress score, and quality rating (excellent / good / fair / poor). Expanding a card shows a timestamped list of flagged moments with color-coded severity and plain English explanations.

---

## Design Decisions

**Audio stays on the phone**
Raw audio is never stored or transmitted. Only the decibel level is extracted and sent. This is both a privacy decision and a bandwidth decision — one number per reading versus a continuous audio stream.

**Fusion runs on the server**
Motion and audio scores are combined server-side so that detection thresholds can be updated for all drivers at once without requiring an app update.

**Signal fusion window**
A plus-or-minus 30 second window is used to match motion and audio events. This matches the 30-second sampling rate in the dataset and was validated against TRIP002, the reference conflict case.

**Normalization caps**
- Motion: divided by 8.0, the maximum lateral magnitude observed in TRIP002
- Audio: mapped from the 60-100 dB range (quiet to argument-level)

**Cold start threshold**
Switches from historical average to live velocity after 30 minutes of active driving. Below this threshold the sample size is too small for a reliable rate.

---

## Output Schema

**`flagged_moments.csv`**
```
flag_id, trip_id, driver_id, timestamp, elapsed_seconds,
flag_type, severity, motion_score, audio_score, combined_score,
explanation, context
```

**`trip_summaries.csv`**
```
trip_id, driver_id, date, duration_min, distance_km, fare,
earnings_velocity, motion_events_count, audio_events_count,
flagged_moments_count, max_severity, stress_score, trip_quality_rating
```

**`earnings_status.csv`**
```
driver_id, date, total_earnings, active_hours, idle_hours,
current_velocity, target_velocity, projected_earnings,
forecast_status, is_cold_start
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data processing | pandas, numpy |
| Dashboard | Streamlit |
| Language | Python 3.12 |

---

## Scalability Notes

The system was designed with production scale in mind even though this submission runs locally:

- Signal fusion is stateless per event — parallelizes trivially across drivers
- Worker partitioning by `driver_id` means each driver's context stays in one place, no cross-worker coordination
- Audio processing belongs at the edge (phone) to protect privacy and reduce bandwidth
- Threshold updates (motion cap, audio floor, sustained duration) are all centralized in `FlagRule` and `ScoreNormalizer` — one change propagates to all drivers instantly
