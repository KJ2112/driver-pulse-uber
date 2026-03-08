import pandas as pd
import numpy as np

COLD_START_HOURS = 0.5


class DriverGoal:
    """Represents a single driver's shift goal for one date."""

    def __init__(self, row: pd.Series):
        self.driver_id      = row['driver_id']
        self.date           = row['date']
        self.target_earnings = float(row['target_earnings'])
        self.target_hours    = float(row['target_hours'])
        self.shift_start     = row['shift_start']
        self.shift_end       = row['shift_end']

    @property
    def required_velocity(self) -> float:
        return self.target_earnings / self.target_hours if self.target_hours > 0 else 0.0


class ShiftSummary:
    """Computes earnings metrics for a driver's shift from their completed trips."""

    def __init__(self, driver_trips: pd.DataFrame, goal: DriverGoal):
        self._trips = driver_trips
        self._goal  = goal
        self._compute()

    def _compute(self):
        self._trips = self._trips.copy()
        self._trips['trip_duration_hours'] = self._trips['duration_min'] / 60.0
        self.total_earnings = float(self._trips['fare'].sum())
        self.active_hours   = float(self._trips['trip_duration_hours'].sum())

        last_end = self._trips['end_time'].max()
        elapsed  = (last_end - self._goal.shift_start).total_seconds() / 3600.0
        self.idle_hours       = max(0.0, elapsed - self.active_hours)
        self.remaining_hours  = max(0.0, (self._goal.shift_end - last_end).total_seconds() / 3600.0)
        self.is_cold_start    = self.active_hours < COLD_START_HOURS

    @property
    def has_trips(self) -> bool:
        return not self._trips.empty


class EarningsForecaster:
    """
    Computes earnings velocity status for all drivers across all goals.
    Uses DriverGoal and ShiftSummary internally.
    """

    def __init__(self, trips_df: pd.DataFrame, goals_df: pd.DataFrame, drivers_df: pd.DataFrame):
        self._trips   = trips_df.copy()
        self._goals   = goals_df.copy()
        self._drivers = drivers_df

        # normalize date columns for consistent matching
        self._trips['date'] = self._trips['date'].astype(str)
        self._goals['date'] = self._goals['date'].astype(str)

    def _historical_avg(self, driver_id: str) -> float:
        if driver_id in self._drivers.index:
            return float(self._drivers.loc[driver_id, 'avg_earnings_per_hour'])
        return float(self._drivers['avg_earnings_per_hour'].mean())

    def _forecast_one(self, goal: DriverGoal) -> dict:
        driver_trips = self._trips[
            (self._trips['driver_id'] == goal.driver_id) &
            (self._trips['date'] == goal.date)
        ]

        if driver_trips.empty:
            return {
                'driver_id':        goal.driver_id,
                'date':             goal.date,
                'total_earnings':   0.0,
                'active_hours':     0.0,
                'idle_hours':       0.0,
                'current_velocity': self._historical_avg(goal.driver_id),
                'target_velocity':  round(goal.required_velocity, 2),
                'projected_earnings': 0.0,
                'forecast_status':  'cold_start',
                'is_cold_start':    True,
            }

        shift = ShiftSummary(driver_trips, goal)

        current_velocity = (
            self._historical_avg(goal.driver_id)
            if shift.is_cold_start
            else shift.total_earnings / shift.active_hours
        )
        projected = shift.total_earnings + current_velocity * shift.remaining_hours
        status    = 'on_track' if projected >= goal.target_earnings else 'at_risk'

        return {
            'driver_id':          goal.driver_id,
            'date':               goal.date,
            'total_earnings':     round(shift.total_earnings, 2),
            'active_hours':       round(shift.active_hours, 3),
            'idle_hours':         round(shift.idle_hours, 3),
            'current_velocity':   round(current_velocity, 2),
            'target_velocity':    round(goal.required_velocity, 2),
            'projected_earnings': round(projected, 2),
            'forecast_status':    status,
            'is_cold_start':      shift.is_cold_start,
        }

    def run(self) -> pd.DataFrame:
        """Compute forecasts for all driver-goal pairs. Returns earnings_status DataFrame."""
        results = []
        for _, row in self._goals.iterrows():
            goal   = DriverGoal(row)
            result = self._forecast_one(goal)
            results.append(result)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        return df[[
            'driver_id', 'date', 'total_earnings', 'active_hours', 'idle_hours',
            'current_velocity', 'target_velocity', 'projected_earnings',
            'forecast_status', 'is_cold_start'
        ]].reset_index(drop=True)


# module-level wrapper so app.py / main.py need no changes
def run_earnings_forecast(data: dict) -> pd.DataFrame:
    return EarningsForecaster(
        trips_df   = data['trips'],
        goals_df   = data['goals'],
        drivers_df = data['drivers'],
    ).run()


if __name__ == '__main__':
    from data_ingestion import load_all
    data = load_all()
    earnings = run_earnings_forecast(data)
    print(f"Forecasts: {len(earnings)}")
    print(earnings[['driver_id', 'total_earnings', 'current_velocity', 'target_velocity', 'forecast_status', 'is_cold_start']].head(10).to_string())
    print("\nStatus breakdown:")
    print(earnings['forecast_status'].value_counts())
