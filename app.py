import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_ingestion import load_all
from signal_processing import run_signal_processing
from earnings_forecast import run_earnings_forecast
from trip_summarizer import summarize_trips

st.set_page_config(
    page_title="Driver Pulse",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── styles ──
st.markdown("""
<style>
  .metric-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #e2e8f0;
    margin-bottom: 12px;
  }
  .on-track {
    background: #f0fdf4;
    border: 2px solid #22c55e;
    border-radius: 12px;
    padding: 18px 24px;
    text-align: center;
  }
  .at-risk {
    background: #fef2f2;
    border: 2px solid #ef4444;
    border-radius: 12px;
    padding: 18px 24px;
    text-align: center;
  }
  .cold-start {
    background: #fffbeb;
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 18px 24px;
    text-align: center;
  }
  .flag-high   { background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .flag-medium { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .flag-low    { background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .badge-excellent { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-good      { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-fair      { background: #fef9c3; color: #854d0e; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-poor      { background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_pipeline_data():
    data = load_all()
    flagged = run_signal_processing(data)
    earnings = run_earnings_forecast(data)
    summaries = summarize_trips(data['trips'], flagged)
    return data, flagged, earnings, summaries


data, flagged_df, earnings_df, summaries_df = load_pipeline_data()

# ── sidebar ──
st.sidebar.title("Driver Pulse")
st.sidebar.caption("Real-time driver insights")

all_drivers = sorted(earnings_df['driver_id'].unique())
selected_driver = st.sidebar.selectbox("Select Driver", all_drivers)

tab1, tab2 = st.tabs(["Earnings Tracker", "Trip Review"])


# ══════════════════════════════
# TAB 1 — EARNINGS TRACKER
# ══════════════════════════════
with tab1:
    st.header("Earnings Tracker")

    driver_earnings = earnings_df[earnings_df['driver_id'] == selected_driver]

    if driver_earnings.empty:
        st.info("No earnings data found for this driver.")
    else:
        row = driver_earnings.iloc[0]
        status = row['forecast_status']
        is_cold_start = row['is_cold_start']

        # status badge
        if status == 'on_track':
            st.markdown('<div class="on-track"><h2 style="color:#16a34a;margin:0">ON TRACK</h2></div>', unsafe_allow_html=True)
        elif status == 'at_risk':
            st.markdown('<div class="at-risk"><h2 style="color:#dc2626;margin:0">AT RISK</h2></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="cold-start"><h2 style="color:#d97706;margin:0">WARMING UP</h2><p style="margin:4px 0 0;color:#92400e;font-size:14px">Forecast based on historical average (first 30 min)</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # get goal info
        driver_goals = data['goals'][data['goals']['driver_id'] == selected_driver]
        if not driver_goals.empty:
            goal_row = driver_goals.iloc[0]
            target = float(goal_row['target_earnings'])
            target_hours = float(goal_row['target_hours'])
        else:
            target = 1400.0
            target_hours = 8.0

        earned = row['total_earnings']
        projected = row['projected_earnings']
        current_vel = row['current_velocity']
        target_vel = row['target_velocity']
        active_hrs = row['active_hours']
        idle_hrs = row['idle_hours']

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Earned Today", f"₹{earned:,.0f}", f"Goal: ₹{target:,.0f}")
        with col2:
            delta_vel = current_vel - target_vel
            st.metric("Current Velocity", f"₹{current_vel:,.0f}/hr",
                      f"{'ahead' if delta_vel >= 0 else 'behind'} by ₹{abs(delta_vel):,.0f}/hr",
                      delta_color="normal" if delta_vel >= 0 else "inverse")
        with col3:
            st.metric("Projected Earnings", f"₹{projected:,.0f}",
                      f"Target: ₹{target:,.0f}")

        # progress bar
        st.markdown("**Progress to Goal**")
        progress = min(1.0, earned / target) if target > 0 else 0.0
        st.progress(progress)
        st.caption(f"₹{earned:,.0f} of ₹{target:,.0f} ({progress*100:.1f}%)")

        if is_cold_start:
            st.info("Forecast is estimated from your historical average. Live velocity will kick in after 30 minutes of driving.")

        st.divider()

        col4, col5 = st.columns(2)
        with col4:
            st.markdown("**Time Breakdown**")
            st.markdown(f"Active driving: **{active_hrs:.1f} hrs**")
            st.markdown(f"Idle waiting: **{idle_hrs:.1f} hrs**")
        with col5:
            st.markdown("**Velocity Comparison**")
            vel_data = pd.DataFrame({
                'Type': ['Current', 'Required'],
                'Velocity (Rs/hr)': [current_vel, target_vel]
            })
            st.bar_chart(vel_data.set_index('Type'))


# ══════════════════════════════
# TAB 2 — TRIP REVIEW
# ══════════════════════════════
with tab2:
    st.header("Trip Review")

    driver_trips = summaries_df[summaries_df['driver_id'] == selected_driver].copy()

    if driver_trips.empty:
        st.info("No trips found for this driver.")
    else:
        st.caption(f"{len(driver_trips)} trips found")

        for _, trip in driver_trips.iterrows():
            trip_id = trip['trip_id']
            quality = trip['trip_quality_rating']
            flag_count = int(trip['flagged_moments_count'])
            stress = trip['stress_score']
            severity = trip['max_severity']

            badge_html = f'<span class="badge-{quality}">{quality.upper()}</span>'

            with st.expander(
                f"{trip_id}  |  ₹{trip['fare']:.0f}  |  {trip['duration_min']} min  |  {trip['distance_km']} km  |  {flag_count} flags",
                expanded=(quality in ['poor', 'fair'])
            ):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Fare", f"₹{trip['fare']:.0f}")
                col2.metric("Duration", f"{trip['duration_min']} min")
                col3.metric("Stress Score", f"{stress:.2f}")
                col4.metric("Flagged Moments", flag_count)

                st.markdown(f"Trip Quality: {badge_html}", unsafe_allow_html=True)

                if flag_count > 0:
                    st.markdown("**Flagged Moments**")
                    trip_flags = flagged_df[flagged_df['trip_id'] == trip_id].sort_values('elapsed_seconds')

                    for _, flag in trip_flags.iterrows():
                        sev = flag['severity']
                        css_class = f"flag-{sev}"
                        icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(sev, "⚪")
                        time_str = str(flag['timestamp']).split(' ')[-1][:8] if pd.notna(flag['timestamp']) else "unknown"

                        st.markdown(f"""
                        <div class="{css_class}">
                          <strong>{icon} {flag['flag_type'].replace('_', ' ').title()}</strong>
                          &nbsp;&nbsp;<span style="color:#888;font-size:13px">{time_str} &nbsp;|&nbsp; {sev.upper()}</span><br>
                          <span style="font-size:14px">{flag['explanation']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("No flagged moments on this trip.")

        st.divider()
        st.subheader("All Trips Overview")
        display_cols = ['trip_id', 'fare', 'duration_min', 'distance_km',
                        'flagged_moments_count', 'max_severity', 'stress_score', 'trip_quality_rating']
        st.dataframe(driver_trips[display_cols].reset_index(drop=True), use_container_width=True)
