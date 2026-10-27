"""Generate local JSON events for the Spark Structured Streaming demo."""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce demo taxi events for the streaming pipeline")
    parser.add_argument("--input-dir", default="data/stream/incoming")
    parser.add_argument("--events", type=int, default=30, help="Number of events; use 0 for continuous mode")
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    output_dir = Path(args.input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    zones = [48, 79, 132, 138, 161, 170, 230, 234, 237]
    created = 0
    while args.events == 0 or created < args.events:
        event = {
            "event_id": str(uuid.uuid4()),
            "pickup_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" "),
            "pickup_zone": random.choice(zones),
            "dropoff_zone": random.choice(zones),
            "total_amount": round(random.uniform(12, 65), 2),
        }
        temporary = output_dir / f".{event['event_id']}.json.tmp"
        destination = output_dir / f"{event['event_id']}.json"
        temporary.write_text(json.dumps(event) + "\n", encoding="utf-8")
        temporary.replace(destination)
        created += 1
        print(f"Produced event {created}: zone {event['pickup_zone']} -> {event['dropoff_zone']}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
