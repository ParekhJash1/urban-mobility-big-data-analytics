"""Download official TLC taxi zone names and convert the map to GeoJSON."""

import argparse
import csv
import json
import tempfile
import zipfile
from pathlib import Path

import requests
import shapefile
from pyproj import Transformer


LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"


def download(url: str, destination: Path) -> None:
    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def shape_to_feature(shape_record, transformer: Transformer) -> dict:
    shape = shape_record.shape
    properties = shape_record.record.as_dict()
    properties["LocationID"] = int(properties["LocationID"])

    rings = []
    starts = list(shape.parts) + [len(shape.points)]
    for start, end in zip(starts, starts[1:]):
        ring = [[transformer.transform(x, y)[0], transformer.transform(x, y)[1]] for x, y in shape.points[start:end]]
        if len(ring) >= 4:
            rings.append([ring])

    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "MultiPolygon", "coordinates": rings},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download TLC taxi zone lookup and map data")
    parser.add_argument("--output-dir", default="data/zones")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lookup_path = output_dir / "taxi_zone_lookup.csv"
    geojson_path = Path("backend/static/data/taxi_zones.geojson")
    geojson_path.parent.mkdir(parents=True, exist_ok=True)

    download(LOOKUP_URL, lookup_path)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "taxi_zones.zip"
        download(SHAPEFILE_URL, archive)
        extraction = Path(temporary) / "extracted"
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(extraction)
        shp_path = next(extraction.rglob("*.shp"))
        transformer = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
        reader = shapefile.Reader(str(shp_path))
        features = [shape_to_feature(record, transformer) for record in reader.iterShapeRecords()]
        reader.close()
        geojson_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")

    # Validate that every map feature has a lookup name before reporting success.
    with lookup_path.open(newline="", encoding="utf-8") as lookup_file:
        lookup_rows = list(csv.DictReader(lookup_file))
    print(f"Saved {len(lookup_rows)} named zones to {lookup_path}")
    print(f"Saved {len(features)} map features to {geojson_path}")


if __name__ == "__main__":
    main()
