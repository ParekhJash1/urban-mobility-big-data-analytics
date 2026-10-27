import argparse
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a NYC TLC Yellow Taxi Parquet file")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--month", type=int, default=1, choices=range(1, 13))
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()

    filename = f"yellow_tripdata_{args.year}-{args.month:02d}.parquet"
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{filename}"
    destination = Path(args.output_dir) / filename
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
    print(f"Saved {destination} ({destination.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
