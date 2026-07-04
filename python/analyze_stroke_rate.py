import os
import pandas as pd
from swim_parser import SwimParser

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "csv"))
POOL_LENGTH_YD = 25 # Assuming default from SwimParser

def analyze_stroke_rate():
    parser = SwimParser(pool_length_yd=POOL_LENGTH_YD)
    all_lengths_data = []

    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            file_path = os.path.join(DATA_DIR, f)
            print(f"Parsing: {f}")
            parsed_data = parser.parse_file(file_path)
            if parsed_data:
                all_lengths_data.extend(parsed_data)

    if not all_lengths_data:
        print("No swim data found or all data filtered out.")
        return

    df = pd.DataFrame(all_lengths_data)

    # Filter for active swimming (already handled by parser, but good to be explicit if more filters are added)
    # Ensure pace is valid (non-zero time) and strokes are valid (non-zero)
    df = df[df['pace_100yd_sec'] > 0]
    df = df[df['avg_swimming_cadence'] > 0] # Cadence is strokes/min

    if df.empty:
        print("No valid active swim lengths found after filtering.")
        return

    # Sort by pace (lower is better for pace_100yd_sec)
    df_sorted_by_pace = df.sort_values(by='pace_100yd_sec').reset_index(drop=True)

    # Consider the fastest 25% of lengths for "consistently highest pace"
    fastest_percentile = 0.25
    num_fastest_lengths = max(1, int(len(df_sorted_by_pace) * fastest_percentile))
    fastest_lengths = df_sorted_by_pace.head(num_fastest_lengths)

    print(f"\nAnalyzing the fastest {len(fastest_lengths)} lengths ({fastest_percentile*100}% of total valid lengths):")
    
    min_pace_overall = df['pace_100yd_sec'].min()
    max_pace_overall = df['pace_100yd_sec'].max()
    avg_pace_overall = df['pace_100yd_sec'].mean()

    min_cadence_overall = df['avg_swimming_cadence'].min()
    max_cadence_overall = df['avg_swimming_cadence'].max()
    avg_cadence_overall = df['avg_swimming_cadence'].mean()

    print(f"Overall Pace Range (sec/100yd): {min_pace_overall:.2f} - {max_pace_overall:.2f} (Avg: {avg_pace_overall:.2f})")
    print(f"Overall Cadence Range (strokes/min): {min_cadence_overall:.2f} - {max_cadence_overall:.2f} (Avg: {avg_cadence_overall:.2f})")


    if not fastest_lengths.empty:
        avg_cadence_fastest = fastest_lengths['avg_swimming_cadence'].mean()
        min_cadence_fastest = fastest_lengths['avg_swimming_cadence'].min()
        max_cadence_fastest = fastest_lengths['avg_swimming_cadence'].max()
        
        avg_pace_fastest = fastest_lengths['pace_100yd_sec'].mean()
        min_pace_fastest = fastest_lengths['pace_100yd_sec'].min()
        max_pace_fastest = fastest_lengths['pace_100yd_sec'].max()

        print(f"\nFor fastest {fastest_percentile*100}% of lengths:")
        print(f"  Average Pace: {avg_pace_fastest:.2f} sec/100yd (Range: {min_pace_fastest:.2f} - {max_pace_fastest:.2f})")
        print(f"  Optimal Stroke Cadence: {avg_cadence_fastest:.2f} strokes/min (Range: {min_cadence_fastest:.2f} - {max_cadence_fastest:.2f})")
        print("Interpretation: This suggests that when your stroke cadence falls within this 'Optimal Stroke Cadence' range, you tend to achieve your highest paces.")
    else:
        print("Could not find enough fast lengths to analyze.")

if __name__ == "__main__":
    analyze_stroke_rate()
