import pandas as pd
import numpy as np


class TripStressAnalyzer:
    """Computes stress score and quality rating for a single trip's flagged moments."""

    SEVERITY_WEIGHTS = {'high': 1.0, 'medium': 0.5, 'low': 0.2}

    def stress_score(self, trip_flags: pd.DataFrame) -> float:
        if trip_flags.empty:
            return 0.0
        weights = trip_flags['severity'].map(self.SEVERITY_WEIGHTS).fillna(0.2)
        return round(float((trip_flags['combined_score'] * weights).sum() / weights.sum()), 4)

    def max_severity(self, trip_flags: pd.DataFrame) -> str:
        if trip_flags.empty:
            return 'none'
        rank = trip_flags['severity'].map({'high': 3, 'medium': 2, 'low': 1}).max()
        return {3: 'high', 2: 'medium', 1: 'low'}.get(rank, 'low')

    def quality_rating(self, stress: float, flag_count: int, max_sev: str) -> str:
        if flag_count == 0:
            return 'excellent'
        if max_sev == 'high' or stress >= 0.75:
            return 'poor'
        if stress >= 0.5 or flag_count >= 3:
            return 'fair'
        return 'good'


class TripSummarizer:
    """
    Builds one summary row per trip by combining trip data and flagged moments.
    Uses TripStressAnalyzer internally for per-trip stress calculations.
    """

    OUTPUT_COLS = [
        'trip_id', 'driver_id', 'date', 'duration_min', 'distance_km', 'fare',
        'earnings_velocity', 'motion_events_count', 'audio_events_count',
        'flagged_moments_count', 'max_severity', 'stress_score', 'trip_quality_rating'
    ]

    def __init__(self):
        self._analyzer = TripStressAnalyzer()

    def _summarize_one(self, trip: pd.Series, trip_flags: pd.DataFrame) -> dict:
        flag_count    = len(trip_flags)
        stress        = self._analyzer.stress_score(trip_flags)
        max_sev       = self._analyzer.max_severity(trip_flags)
        quality       = self._analyzer.quality_rating(stress, flag_count, max_sev)

        motion_events = int((trip_flags['motion_score'] > 0.4).sum()) if flag_count > 0 else 0
        audio_events  = int((trip_flags['audio_score']  > 0.5).sum()) if flag_count > 0 else 0

        duration_hours = trip['duration_min'] / 60.0
        earnings_vel   = round(trip['fare'] / duration_hours, 2) if duration_hours > 0 else 0.0

        return {
            'trip_id':               trip['trip_id'],
            'driver_id':             trip['driver_id'],
            'date':                  trip['date'],
            'duration_min':          trip['duration_min'],
            'distance_km':           trip['distance_km'],
            'fare':                  trip['fare'],
            'earnings_velocity':     earnings_vel,
            'motion_events_count':   motion_events,
            'audio_events_count':    audio_events,
            'flagged_moments_count': flag_count,
            'max_severity':          max_sev,
            'stress_score':          stress,
            'trip_quality_rating':   quality,
        }

    def summarize(self, trips_df: pd.DataFrame, flagged_df: pd.DataFrame) -> pd.DataFrame:
        """Build summary DataFrame for all trips."""
        rows = [
            self._summarize_one(trip, flagged_df[flagged_df['trip_id'] == trip['trip_id']])
            for _, trip in trips_df.iterrows()
        ]
        return pd.DataFrame(rows)[self.OUTPUT_COLS].reset_index(drop=True)


# module-level wrapper so app.py / main.py need no changes
def summarize_trips(trips_df: pd.DataFrame, flagged_df: pd.DataFrame) -> pd.DataFrame:
    return TripSummarizer().summarize(trips_df, flagged_df)


if __name__ == '__main__':
    from data_ingestion import load_all
    from signal_processing import run_signal_processing

    data    = load_all()
    flagged = run_signal_processing(data)
    summary = summarize_trips(data['trips'], flagged)

    print(f"Trips summarized: {len(summary)}")
    print(summary[['trip_id', 'fare', 'flagged_moments_count', 'max_severity', 'stress_score', 'trip_quality_rating']].head(10).to_string())
    print("\nQuality breakdown:")
    print(summary['trip_quality_rating'].value_counts())
