# ═══════════════════════════════════════════════════════════════
# OPERATION IRONSHIELD – Fabric Notebook: Real-Time Data Sender
# ═══════════════════════════════════════════════════════════════
# This notebook reads the pre-generated JSONL datasets and sends
# events to Azure Event Hub (→ Fabric Eventstream) in real-time,
# simulating live sensor feeds.
#
# Usage: Run in Microsoft Fabric notebook attached to a Spark cluster.
# Prerequisites: Upload dataset JSONL files to ABFSS lakehouse path.
# ═══════════════════════════════════════════════════════════════

# %pip install azure-eventhub --quiet

# --- Configuration ---
# Connection string z Custom App source (Krok 4.2) - ZAWIERA EntityPath, nie zmieniaj!
EVENT_HUB_CONNECTION_STRING = "<YOUR_EVENT_HUB_CONNECTION_STRING>"
LAKEHOUSE_PATH = "abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>/Files/ironshield/"

# Time scale factor: 1.0 = real-time, 0.1 = 10x faster (for demo)
TIME_SCALE = 0.5

# Timezone offset (hours from UTC). Polska: +1 (CET) lub +2 (CEST, czas letni)
# Czas letni w Polsce: ostatnia niedziela marca – ostatnia niedziela października
TZ_OFFSET_HOURS = 1  # Zmień na 2 w okresie czasu letniego (CEST)

# --- Install Event Hub SDK (first run only) ---
# %pip install azure-eventhub

import json
import time
from datetime import datetime, timezone, timedelta
from azure.eventhub import EventHubProducerClient, EventData

# --- Load datasets ---
STREAMS = [
    "radar_detections",
    "vehicle_status", 
    "soldier_health",
    "drone_observations",
    "weather_data",
    "sigint_intercepts",
    "ammo_logistics",
]

all_events = []

for stream_name in STREAMS:
    path = f"{LAKEHOUSE_PATH}{stream_name}.jsonl"
    try:
        df = spark.read.text(path)
        rows = df.collect()
        for row in rows:
            event = json.loads(row.value)
            event["_stream"] = stream_name
            all_events.append(event)
        print(f"Loaded {len(rows)} events from {stream_name}")
    except Exception as e:
        print(f"Warning: Could not load {stream_name}: {e}")

# Sort all events by timestamp
all_events.sort(key=lambda e: e.get("Timestamp", ""))
print(f"\nTotal events to send: {len(all_events)}")

# --- Calculate timestamp offset ---
# Przesuwamy wszystkie timestampy tak, aby pierwszy event = TERAZ (w strefie PL)
first_ts = datetime.fromisoformat(all_events[0]["Timestamp"])
local_tz = timezone(timedelta(hours=TZ_OFFSET_HOURS))
now_local = datetime.now(local_tz)
ts_offset = now_local - first_ts.replace(tzinfo=local_tz)
print(f"\n⏰ Timestamp offset: {ts_offset}")
print(f"   Original first event: {first_ts.isoformat()}")
print(f"   Adjusted first event: {(first_ts + ts_offset).strftime('%Y-%m-%dT%H:%M:%S')}+{TZ_OFFSET_HOURS:02d}:00")
print(f"   Local time now:       {now_local.strftime('%Y-%m-%dT%H:%M:%S')}+{TZ_OFFSET_HOURS:02d}:00")

# --- Send events to Event Hub ---
# Nie podawaj eventhub_name - jest juz w EntityPath connection stringa!
producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONNECTION_STRING,
)

print(f"\n🚀 Starting real-time simulation...")
print(f"   Time scale: {TIME_SCALE}x (1.0 = real-time)")
print(f"   Timezone: UTC+{TZ_OFFSET_HOURS}")

prev_ts = None
sent_count = 0
batch_size = 0
event_batch = producer.create_batch()

try:
    for event in all_events:
        ts_str = event.get("Timestamp", "")
        stream = event.pop("_stream", "unknown")
        
        # Shift timestamp to NOW
        if ts_str:
            try:
                orig_ts = datetime.fromisoformat(ts_str)
                new_ts = orig_ts + ts_offset
                new_ts_str = new_ts.strftime("%Y-%m-%dT%H:%M:%S") + f"+{TZ_OFFSET_HOURS:02d}:00"
                event["Timestamp"] = new_ts_str
            except:
                pass

        # Timing: wait proportionally between events
        if prev_ts and ts_str:
            try:
                curr = datetime.fromisoformat(ts_str)
                prev = datetime.fromisoformat(prev_ts)
                delta = (curr - prev).total_seconds() * TIME_SCALE
                if delta > 0:
                    time.sleep(min(delta, 5.0))  # cap at 5s
            except:
                pass
        prev_ts = ts_str
        
        # Include stream name in JSON body (needed for KQL Update Policy routing)
        event["stream"] = stream
        event_data = EventData(json.dumps(event, ensure_ascii=False))
        event_data.properties = {"stream": stream}
        
        try:
            event_batch.add(event_data)
            batch_size += 1
        except ValueError:
            # Batch full, send it
            producer.send_batch(event_batch)
            sent_count += batch_size
            event_batch = producer.create_batch()
            event_batch.add(event_data)
            batch_size = 1
        
        # Send batch every 50 events or so
        if batch_size >= 50:
            producer.send_batch(event_batch)
            sent_count += batch_size
            event_batch = producer.create_batch()
            batch_size = 0
            print(f"   Sent {sent_count}/{len(all_events)} events...")

    # Send remaining
    if batch_size > 0:
        producer.send_batch(event_batch)
        sent_count += batch_size

    print(f"\n✅ Simulation complete! Sent {sent_count} events total.")

finally:
    producer.close()
