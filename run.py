from pathlib import Path
import os
import csv
import requests


def main() -> None:
    api_key = os.environ["GOOGLE_CSE_API_KEY"]
    cx = os.environ["GOOGLE_CSE_CX"]
    params = {"key": api_key, "cx": cx, "q": "yacht"}
    try:
        requests.get(
            "https://www.googleapis.com/customsearch/v1", params=params, timeout=10
        )
    except requests.RequestException:
        print("WARNING: CSE failed")
    Path("exports").mkdir(exist_ok=True)
    with open(Path("exports") / "yachts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "length_m"])


if __name__ == "__main__":
    main()
