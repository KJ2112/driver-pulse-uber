import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_ingestion import load_all
from signal_processing import run_signal_processing
from earnings_forecast import run_earnings_forecast
from trip_summarizer import summarize_trips

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')


def main():
    print("Driver Pulse Pipeline")
    print("=" * 40)

    print("\n[1/4] Loading data...")
    data = load_all()
    for name, df in data.items():
        print(f"  {name}: {len(df)} rows")

    print("\n[2/4] Running signal fusion...")
    flagged_moments = run_signal_processing(data)
    print(f"  Flagged moments: {len(flagged_moments)}")
    if len(flagged_moments) > 0:
        print(f"  Severity breakdown: {flagged_moments['severity'].value_counts().to_dict()}")

    print("\n[3/4] Running earnings forecast...")
    earnings_status = run_earnings_forecast(data)
    print(f"  Forecasts computed: {len(earnings_status)}")
    print(f"  Status breakdown: {earnings_status['forecast_status'].value_counts().to_dict()}")

    print("\n[4/4] Building trip summaries...")
    trip_summaries = summarize_trips(data['trips'], flagged_moments)
    print(f"  Trips summarized: {len(trip_summaries)}")
    print(f"  Quality breakdown: {trip_summaries['trip_quality_rating'].value_counts().to_dict()}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    flagged_path = os.path.join(OUTPUT_DIR, 'flagged_moments.csv')
    summaries_path = os.path.join(OUTPUT_DIR, 'trip_summaries.csv')
    earnings_path = os.path.join(OUTPUT_DIR, 'earnings_status.csv')

    flagged_moments.to_csv(flagged_path, index=False)
    trip_summaries.to_csv(summaries_path, index=False)
    earnings_status.to_csv(earnings_path, index=False)

    print(f"\nOutputs written to {OUTPUT_DIR}/")
    print(f"  flagged_moments.csv  ({len(flagged_moments)} rows)")
    print(f"  trip_summaries.csv   ({len(trip_summaries)} rows)")
    print(f"  earnings_status.csv  ({len(earnings_status)} rows)")
    print("\nPipeline complete.")


if __name__ == '__main__':
    main()
