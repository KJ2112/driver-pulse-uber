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
  .flag-high   { background: #fef2f2; color: #0f172a; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .flag-medium { background: #fffbeb; color: #0f172a; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .flag-low    { background: #f0f9ff; color: #0f172a; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin: 6px 0; }
  .badge-excellent { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-good      { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-fair      { background: #fef9c3; color: #854d0e; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  .badge-poor      { background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
  
  .timeline-container { position: relative; margin-top: 20px; padding-left: 80px; font-family: sans-serif; margin-bottom: 40px; }
  .timeline-line { position: absolute; left: 80px; top: 0; bottom: 0; width: 4px; background: #e2e8f0; border-radius: 2px; }
  .time-marker { position: absolute; left: 0; font-weight: 600; color: #64748b; font-size: 14px; transform: translateY(-50%); width: 65px; text-align: right; }
  .timeline-dot { position: absolute; left: -26px; width: 14px; height: 14px; border-radius: 50%; background: #94a3b8; transform: translateY(-50%); top: 50%; border: 3px solid white; box-shadow: 0 0 0 1px #cbd5e1; z-index: 2; }
  .trip-card { position: absolute; left: 110px; right: 20px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); cursor: pointer; transition: all 0.2s; transform: translateY(-50%); display: flex; justify-content: space-between; align-items: center; text-decoration: none !important; color: inherit; z-index: 1; }
  .trip-card:hover { transform: translateY(-50%) scale(1.02); box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-color: #cbd5e1; z-index: 3; }
  .trip-card.stress { border-left: 4px solid #ef4444; background: #fef2f2; }
  .trip-card.normal { border-left: 4px solid #3b82f6; }
  .trip-card .trip-info { display: flex; flex-direction: column; }
  .trip-card .trip-id { font-weight: 600; font-size: 15px; margin-bottom: 4px; color: #1e293b; }
  .trip-card .trip-time { font-size: 13px; color: #64748b; }
  .trip-card .trip-fare { font-weight: 600; font-size: 16px; color: #0f172a; }
  .trip-card.stress .timeline-dot { background: #ef4444; box-shadow: 0 0 0 1px #ef4444; }
  .trip-card.normal .timeline-dot { background: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }
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

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'driver_id' not in st.session_state:
    st.session_state['driver_id'] = None
if 'target_earnings' not in st.session_state:
    st.session_state['target_earnings'] = 1400.0
import datetime
if 'target_hours' not in st.session_state:
    st.session_state['target_hours'] = 8.0
if 'target_start_time' not in st.session_state:
    st.session_state['target_start_time'] = datetime.time(9, 0)
if 'target_end_time' not in st.session_state:
    st.session_state['target_end_time'] = datetime.time(17, 0)


all_drivers = sorted(earnings_df['driver_id'].unique())

# Handle auto-login from query params (when clicking a timeline link)
url_driver = st.query_params.get("driver")
if url_driver and url_driver in all_drivers and not st.session_state['logged_in']:
    st.session_state['logged_in'] = True
    st.session_state['driver_id'] = url_driver

if not st.session_state['logged_in']:
    st.title("Driver Pulse - Login")
    st.markdown("Please enter your Driver ID to access your dashboard.")
    
    with st.form("login_form"):
        driver_id_input = st.text_input("Driver ID", placeholder="e.g. DRV001")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if driver_id_input in all_drivers:
                st.session_state['logged_in'] = True
                st.session_state['driver_id'] = driver_id_input
                st.rerun()
            else:
                st.error("Invalid Driver ID. Please check and try again.")
    st.stop()
    
# ── sidebar ──
selected_driver = st.session_state['driver_id']
st.sidebar.title("Driver Pulse")
st.sidebar.caption(f"Logged in as: **{selected_driver}**")

if st.sidebar.button("Logout", type="primary"):
    st.session_state['logged_in'] = False
    st.session_state['driver_id'] = None
    st.rerun()

# Handle routing based on query params
selected_trip_id = st.query_params.get("trip")

if selected_trip_id:
    # Full page override for Single Trip Details View
    def go_back():
        st.query_params.clear()
        
    st.button("← Back to Dashboard", on_click=go_back)
    st.header(f"Trip Details: {selected_trip_id}")
    
    trip_summ = summaries_df[summaries_df['trip_id'] == selected_trip_id]
    if not trip_summ.empty:
        trip = trip_summ.iloc[0]
        quality = trip['trip_quality_rating']
        badge_html = f'<span class="badge-{quality}">{quality.upper()}</span>'
        flag_count = int(trip['flagged_moments_count'])
        stress = trip['stress_score']
        
        st.markdown(f"**Quality Rating:** {badge_html}", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Fare", f"₹{trip['fare']:.0f}")
        col2.metric("Duration", f"{trip['duration_min']} min")
        col3.metric("Stress Score", f"{stress:.2f}")
        col4.metric("Flagged Moments", flag_count)
        
        if flag_count > 0:
            st.markdown("### Flagged Moments")
            trip_flags = flagged_df[flagged_df['trip_id'] == selected_trip_id].sort_values('elapsed_seconds')
            for _, flag in trip_flags.iterrows():
                sev = flag['severity']
                css_class = f"flag-{sev}"
                icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(sev, "⚪")
                st.markdown(f'''
                <div class="{css_class}">
                    <strong>{icon} {flag['flag_type'].replace('_', ' ').title()}</strong>
                    <br><span style="font-size:14px">{flag['explanation']}</span>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.success("No flagged moments on this trip.")
    else:
        st.error("Trip not found.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Earnings Tracker", "Trip Review", "Settings"])


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

        target = st.session_state['target_earnings']
        target_hours = st.session_state['target_hours']

        earned = row['total_earnings']
        projected = row['projected_earnings']
        current_vel = row['current_velocity']
        target_vel = row['target_velocity']
        active_hrs = row['active_hours']
        idle_hrs = row['idle_hours']

        # ── ROW 1: Earnings Summary (left) + Shift Timeline (right) ──
        col_earnings, col_timeline = st.columns([1, 1.2])

        # ── LEFT: Earnings Summary ──
        with col_earnings:
            st.subheader("Earnings Summary")

            # Status banner
            if status == 'on_track':
                st.markdown('<div class="on-track"><h2 style="color:#16a34a;margin:0">ON TRACK</h2></div>', unsafe_allow_html=True)
            elif status == 'at_risk':
                st.markdown('<div class="at-risk"><h2 style="color:#dc2626;margin:0">AT RISK</h2></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="cold-start"><h2 style="color:#d97706;margin:0">WARMING UP</h2><p style="margin:4px 0 0;color:#92400e;font-size:14px">Forecast based on historical average (first 30 min)</p></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Key metrics
            st.metric("Earned Today", f"₹{earned:,.0f}", f"Goal: ₹{target:,.0f}")

            delta_vel = current_vel - target_vel
            st.metric("Current Velocity", f"₹{current_vel:,.0f}/hr",
                      f"{'ahead' if delta_vel >= 0 else 'behind'} by ₹{abs(delta_vel):,.0f}/hr",
                      delta_color="normal" if delta_vel >= 0 else "inverse")

            st.metric("Projected Earnings", f"₹{projected:,.0f}",
                      f"Target: ₹{target:,.0f}")

            # Progress bar
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Progress to Goal**")
            progress = min(1.0, earned / target) if target > 0 else 0.0
            st.progress(progress)
            st.caption(f"₹{earned:,.0f} of ₹{target:,.0f} ({progress*100:.1f}%)")

            if is_cold_start:
                st.info("Forecast is estimated from your historical average. Live velocity will kick in after 30 minutes of driving.")

        # ── RIGHT: Shift Timeline ──
        with col_timeline:
            st.subheader("Shift Timeline")

            shift_start_time = st.session_state['target_start_time']
            shift_end_time = st.session_state['target_end_time']

            raw_trips = data['trips'][data['trips']['driver_id'] == selected_driver]

            if not raw_trips.empty:
                driver_trips_timeline = raw_trips.merge(summaries_df[['trip_id', 'trip_quality_rating']], on='trip_id', how='left')
                driver_trips_timeline = driver_trips_timeline.sort_values('start_time')

                shift_date = driver_trips_timeline.iloc[0]['start_time'].date()
                shift_start_dt = pd.to_datetime(datetime.datetime.combine(shift_date, shift_start_time))
                shift_end_dt = pd.to_datetime(datetime.datetime.combine(shift_date, shift_end_time))

                if shift_end_dt <= shift_start_dt:
                    shift_end_dt += pd.Timedelta(days=1)

                total_shift_sec = (shift_end_dt - shift_start_dt).total_seconds()
                if total_shift_sec <= 0: total_shift_sec = 3600

                timeline_html = '<div class="timeline-container" style="height: 600px;">'
                timeline_html += '<div class="timeline-line"></div>'

                # Hour markers
                num_hours = int(total_shift_sec // 3600)
                for hour_offset in range(num_hours + 1):
                    marker_time = shift_start_dt + pd.Timedelta(hours=hour_offset)
                    top_pct = (hour_offset * 3600 / total_shift_sec) * 100
                    time_str = marker_time.strftime('%I %p')
                    timeline_html += f'<div class="time-marker" style="top: {top_pct}%">{time_str}</div>'

                # Place trip cards
                for _, trip in driver_trips_timeline.iterrows():
                    t_start = pd.to_datetime(trip['start_time'])
                    t_end = pd.to_datetime(trip['end_time'])

                    offset_sec = (t_start - shift_start_dt).total_seconds()
                    top_pct = max(0, min(100, (offset_sec / total_shift_sec) * 100))

                    quality = trip.get('trip_quality_rating', 'good')
                    status_class = "stress" if quality in ['poor', 'fair'] else "normal"
                    stress_warning = '<span style="color:#ef4444;font-size:12px;margin-left:8px;">⚠️ Conflict detected</span>' if status_class == 'stress' else ''

                    start_str = t_start.strftime('%I:%M %p')
                    end_str = t_end.strftime('%I:%M %p')
                    fare = trip['fare']
                    trip_id = trip['trip_id']

                    timeline_html += f'''
<a href="?trip={trip_id}&driver={selected_driver}" target="_self" class="trip-card {status_class}" style="top: {top_pct}%">
    <div class="timeline-dot"></div>
    <div class="trip-info">
        <div class="trip-id">Trip #{trip_id} {stress_warning}</div>
        <div class="trip-time">Start: {start_str} &bull; End: {end_str}</div>
    </div>
    <div class="trip-fare">₹{fare:.0f}</div>
</a>
'''

                timeline_html += '</div>'
                st.markdown(timeline_html, unsafe_allow_html=True)
            else:
                st.info("No timeline available - no trip records found.")

        # ── ROW 2: Secondary Analytics ──
        st.divider()

        col_time, col_vel = st.columns(2)

        # ── LEFT: Time Breakdown ──
        with col_time:
            st.markdown("**Time Breakdown**")
            st.markdown(f"Active driving: **{active_hrs:.1f} hrs**")
            st.markdown(f"Idle waiting: **{idle_hrs:.1f} hrs**")

        # ── RIGHT: Velocity Comparison ──
        with col_vel:
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

# ══════════════════════════════
# TAB 3 — SETTINGS
# ══════════════════════════════
with tab3:
    st.header("Settings")
    st.markdown("Customize your daily goals and working hours.")
    
    with st.container():
        st.subheader("Goal Settings")
        
        current_target = st.session_state['target_earnings']
        
        import datetime
        default_start = datetime.time(9, 0)
        default_end = datetime.time(17, 0)
        
        with st.form("settings_form"):
            new_target = st.number_input("Target Earnings (₹)", min_value=100.0, max_value=10000.0, value=float(current_target), step=100.0)
            
            st.markdown("**Work Hours**")
            col_start, col_end = st.columns(2)
            with col_start:
                start_time = st.time_input("Start Time", value=default_start)
            with col_end:
                end_time = st.time_input("End Time", value=default_end)
                
            save_button = st.form_submit_button("Save Settings")
            
            if save_button:
                start_dt = datetime.datetime.combine(datetime.date.today(), start_time)
                end_dt = datetime.datetime.combine(datetime.date.today(), end_time)
                if end_dt <= start_dt:
                    end_dt += datetime.timedelta(days=1)
                
                new_hours = (end_dt - start_dt).total_seconds() / 3600.0
                
                st.session_state['target_start_time'] = start_time
                st.session_state['target_end_time'] = end_time
                st.session_state['target_earnings'] = new_target
                st.session_state['target_hours'] = new_hours
                
                st.success(f"Settings successfully updated! Your new target is ₹{new_target:,.0f} for {new_hours:.1f} hours.")