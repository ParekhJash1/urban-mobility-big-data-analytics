"""Install the small Windows Hadoop helper required by Spark checkpoints."""

import argparse
from pathlib import Path

import requests


WINDOWS_HADOOP_FILES = {
    "winutils.exe": "https://github.com/cdarlint/winutils/raw/refs/heads/master/hadoop-3.3.6/bin/winutils.exe",
    "hadoop.dll": "https://github.com/cdarlint/winutils/raw/refs/heads/master/hadoop-3.3.6/bin/hadoop.dll",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up winutils.exe for local Spark streaming on Windows")
    parser.add_argument("--output-dir", default="hadoop-local")
    args = parser.parse_args()
    bin_dir = Path(args.output_dir) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for filename, url in WINDOWS_HADOOP_FILES.items():
        destination = bin_dir / filename
        with requests.get(url, timeout=60) as response:
            response.raise_for_status()
            destination.write_bytes(response.content)
        print(f"Saved {destination}")
    print("The streaming script automatically uses this project-local helper.")


if __name__ == "__main__":
    main()
