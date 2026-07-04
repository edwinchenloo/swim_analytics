import csv
from datetime import datetime
import os

class SwimParser:
    def __init__(self, pool_length_yd=25):
        self.pool_length_yd = pool_length_yd

    def parse_file(self, file_path):
        raw_rows = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    clean_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
                    if not clean_row or 'start_time' not in clean_row:
                        continue
                    
                    time_str = clean_row['start_time'].replace(' CST', '').replace(' CDT', '')
                    clean_row['start_time_dt'] = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    
                    numeric_fields = [
                        'total_elapsed_time', 'total_timer_time', 'total_strokes', 
                        'avg_speed', 'avg_swimming_cadence', 'avg_heart_rate', 'length_type'
                    ]
                    for field in numeric_fields:
                        if field in clean_row and clean_row[field]:
                            clean_row[field] = float(clean_row[field])
                        else:
                            clean_row[field] = 0.0
                    
                    raw_rows.append(clean_row)

            # Now calculate duration based on start_time of NEXT length
            data = []
            for i in range(len(raw_rows)):
                curr = raw_rows[i]
                
                # Default duration is total_timer_time
                duration = curr.get('total_timer_time', curr.get('total_elapsed_time', 0.0))
                
                # If there's a next length, the "wall-to-wall" time is the difference in start times
                if i < len(raw_rows) - 1:
                    next_len = raw_rows[i+1]
                    wall_time = (next_len['start_time_dt'] - curr['start_time_dt']).total_seconds()
                    # If wall_time is much larger than duration, it suggests a rest was included
                    # but if it's close, it's a better measure of the length.
                    # We'll stick to duration for pace, but use this for filtering.
                
                # --- FILTERS ---
                if curr.get('length_type') == 0.0:
                    continue
                
                strokes = curr.get('total_strokes', 0)
                if strokes < 10.0 or strokes > 18.0:
                    continue

                pace_sec = (duration / self.pool_length_yd) * 100
                if pace_sec > 160.0:
                    continue

                curr['swim_time'] = duration
                curr['message_index'] = len(data)
                curr['distance_yd'] = (len(data) + 1) * self.pool_length_yd
                curr['pace_100yd_sec'] = pace_sec
                curr['pace_str'] = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                data.append(curr)
                
            return data
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")
            return None

    def get_summary(self, data):
        if not data:
            return {}
            
        total_lengths = len(data)
        total_distance = total_lengths * self.pool_length_yd
        total_time_sec = sum(row['swim_time'] for row in data)
        avg_strokes = sum(row['total_strokes'] for row in data) / total_lengths
        avg_cadence = sum(row.get('avg_swimming_cadence', 0) for row in data) / total_lengths
        
        hr_values = [row['avg_heart_rate'] for row in data if row.get('avg_heart_rate', 0) > 0]
        avg_hr = sum(hr_values) / len(hr_values) if hr_values else 0
        
        avg_pace_sec = (total_time_sec / total_distance) * 100
        
        return {
            "date": data[0]['start_time_dt'].strftime('%Y-%m-%d'),
            "start_time": data[0]['start_time_dt'].strftime('%I:%M %p'),
            "total_distance_yd": total_distance,
            "total_lengths": total_lengths,
            "avg_pace_100yd": f"{int(avg_pace_sec // 60)}:{int(avg_pace_sec % 60):02d}",
            "total_time": f"{int(total_time_sec // 60)}:{int(total_time_sec % 60):02d}",
            "avg_strokes": round(avg_strokes, 1),
            "avg_cadence": round(avg_cadence, 1),
            "avg_hr": round(avg_hr, 1)
        }
