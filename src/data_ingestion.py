import os
import pandas as pd


class DataLoader:
    """
    Loads and cleans all six source CSVs.
    Holds results as attributes after calling .load_all().
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.data_dir = data_dir
        self.accelerometer = None
        self.audio = None
        self.trips = None
        self.drivers = None
        self.goals = None
        self.velocity_log = None

    def _path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    def load_accelerometer(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('accelerometer_data.csv'))
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df = df.dropna(subset=['accel_x', 'accel_y', 'accel_z', 'trip_id', 'timestamp'])
        df = df[df['accel_z'].abs() > 0.5]
        return df.sort_values(['trip_id', 'timestamp']).reset_index(drop=True)

    def load_audio(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('audio_intensity_data.csv'))
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df = df.dropna(subset=['audio_level_db', 'trip_id', 'timestamp'])
        return df.sort_values(['trip_id', 'timestamp']).reset_index(drop=True)

    def load_trips(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('trips.csv'))
        df['start_time'] = pd.to_datetime(df['date'] + ' ' + df['start_time'])
        df['end_time'] = pd.to_datetime(df['date'] + ' ' + df['end_time'])
        df = df[df['trip_status'] == 'completed']
        df = df.dropna(subset=['trip_id', 'driver_id', 'fare'])
        return df.reset_index(drop=True)

    def load_drivers(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('drivers.csv'))
        df = df.dropna(subset=['driver_id', 'avg_earnings_per_hour'])
        return df.set_index('driver_id')

    def load_goals(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('driver_goals.csv'))
        df['shift_start'] = pd.to_datetime(df['date'] + ' ' + df['shift_start_time'])
        df['shift_end'] = pd.to_datetime(df['date'] + ' ' + df['shift_end_time'])
        df = df.dropna(subset=['driver_id', 'target_earnings', 'target_hours'])
        return df.reset_index(drop=True)

    def load_velocity_log(self) -> pd.DataFrame:
        df = pd.read_csv(self._path('earnings_velocity_log.csv'))
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df = df.dropna(subset=['driver_id', 'cumulative_earnings', 'elapsed_hours'])
        return df.sort_values(['driver_id', 'timestamp']).reset_index(drop=True)

    def load_all(self) -> dict:
        """Load all six datasets. Returns dict for backward compatibility with app.py."""
        self.accelerometer = self.load_accelerometer()
        self.audio         = self.load_audio()
        self.trips         = self.load_trips()
        self.drivers       = self.load_drivers()
        self.goals         = self.load_goals()
        self.velocity_log  = self.load_velocity_log()
        return {
            'accelerometer': self.accelerometer,
            'audio':         self.audio,
            'trips':         self.trips,
            'drivers':       self.drivers,
            'goals':         self.goals,
            'velocity_log':  self.velocity_log,
        }

    def summary(self):
        for name in ['accelerometer', 'audio', 'trips', 'drivers', 'goals', 'velocity_log']:
            df = getattr(self, name)
            status = f"{len(df)} rows" if df is not None else "not loaded"
            print(f"  {name}: {status}")


# module-level wrapper so app.py / main.py need no changes
def load_all(data_dir: str = None) -> dict:
    return DataLoader(data_dir).load_all()


if __name__ == '__main__':
    loader = DataLoader()
    loader.load_all()
    loader.summary()
