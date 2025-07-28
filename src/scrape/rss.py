print(">>> rss.py reached <<<")
import feedparser, logging, pathlib, json, os
from pathlib import Path

FEED = "https://www.boatinternational.com/feed"
OUT  = Path("data/cache/rss_boatinternational.json")

def run() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d = feedparser.parse(FEED)
    json.dump(d.entries[:20], OUT.open("w"))
    logging.getLogger(__name__).info("Saved %s items → %s", len(d.entries), OUT)
if __name__ == "__main__":
    run()
