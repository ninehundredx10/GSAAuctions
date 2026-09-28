#!/usr/bin/env python3
"""
gsa_wny_auctions.py

Pulls current listings from the GSA Auctions API and filters them down to
Western New York (roughly: Erie, Niagara, Genesee, Wyoming, Orleans,
Chautauqua, Cattaraugus counties).

Uses only the Python standard library. No pip install needed.
"""

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request

API_URL = "https://api.gsa.gov/assets/gsaauctions/v2/auctions"

WNY_ZIP3_PREFIXES = ("140", "141", "142", "143", "147")


def fetch_auctions(api_key: str) -> list:
    req = urllib.request.Request(
        f"{API_URL}?format=json",
        headers={"X-API-KEY": api_key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"GSA API returned HTTP {e.code}:\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach the GSA API: {e.reason}")

    data = json.loads(body)
    if isinstance(data, dict):
        for key in ("Results", "results", "auctions", "Auctions", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]
    return data


def matches_filter(record: dict, state: str, zip3_prefixes) -> bool:
    rec_state = (record.get("propertyState") or record.get("PropertyState") or "").upper()
    if rec_state != state.upper():
        return False
    if zip3_prefixes is None:
        return True
    zip_code = str(record.get("propertyZip") or record.get("PropertyZip") or "")
    return zip_code[:3] in zip3_prefixes


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("USAGE")[0])
    parser.add_argument("--api-key", default=None, help="GSA/api.data.gov API key. Falls back to the GSA_API_KEY env var.")
    parser.add_argument("--state", default="NY", help="Two-letter state to filter on (default: NY).")
    parser.add_argument("--all-ny", action="store_true", help="Show every listing in --state, skip the WNY zip filter.")
    parser.add_argument("--csv", metavar="PATH", default=None, help="Write matching rows to a CSV file instead of printing them.")
    args = parser.parse_args()

    api_key = args.api_key or __import__("os").environ.get("GSA_API_KEY")
    if not api_key:
        sys.exit("No API key given. Use --api-key or set the GSA_API_KEY environment variable.")

    all_records = fetch_auctions(api_key)
    zip3 = None if args.all_ny else WNY_ZIP3_PREFIXES
    matches = [r for r in all_records if matches_filter(r, args.state, zip3)]

    print(f"Fetched {len(all_records)} total listings; {len(matches)} matched "
          f"state={args.state}" + ("" if args.all_ny else " + WNY zip filter") + ".\n")

    if args.csv:
        fieldnames = sorted({k for r in matches for k in r.keys()}) or ["note"]
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            if matches:
                writer.writerows(matches)
            else:
                writer.writerow({fieldnames[0]: "no matching listings this run"})
        print(f"Wrote {len(matches)} rows to {args.csv}")
        return

    if not matches:
        return

    for r in matches:
        item = r.get("itemName") or r.get("ItemName") or "(no item name)"
        city = r.get("propertyCity") or r.get("PropertyCity") or "?"
        state = r.get("propertyState") or r.get("PropertyState") or "?"
        zipc = r.get("propertyZip") or r.get("PropertyZip") or "?"
        end = r.get("aucEndDt") or r.get("AucEndDt") or "?"
        bid = r.get("highBidAmount") or r.get("HighBidAmount") or "0"
        sale = r.get("saleNo") or r.get("SaleNo") or "?"
        url = r.get("itemDescURL") or r.get("ItemDescURL") or ""
        print(f"- {item}")
        print(f"    {city}, {state} {zipc}  |  ends {end}  |  high bid ${bid}  |  sale #{sale}")
        if url:
            print(f"    {url}")
        print()


if __name__ == "__main__":
    main()
