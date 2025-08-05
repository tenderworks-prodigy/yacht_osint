# Diagnostics

This document explains how to collect detailed diagnostics when RSS feed
discovery yields no results. These tools are intended for developers working
on the pipeline to understand why certain websites fail to expose feed
metadata and to provide evidence for improving heuristics.

## Diagnostic script

The `scripts/diagnose_and_run.py` script performs a targeted probe against a
single domain or URL and emits a structured JSON report. It does **not**
depend on third‑party libraries, instead relying on Python’s standard
library, so it can be executed in very restricted environments.

### Usage

```bash
python scripts/diagnose_and_run.py example.com
```

The script will:

* Fetch the page with realistic browser headers.
* Extract all `<link rel="alternate" type="application/rss+xml|atom+xml" ...>`
  elements.
* Count the number of `<a>` tags as a proxy for page complexity.
* Detect common bot‑challenge indicators in the HTML (e.g. “captcha”,
  “are you human”).
* Save the raw HTML into `diagnostics/raw/<domain>.html` when no feed links
  are discovered.

Example output:

```json
{
  "url": "https://example.com",
  "status": 200,
  "content_type": "text/html; charset=utf-8",
  "response_len": 12345,
  "feed_link_tags": ["https://example.com/feed.xml"],
  "a_count": 42,
  "bot_challenge_detected": false
}
```

### Interpreting results

- A non‑200 status or very small `response_len` often means the URL redirected
  elsewhere or a network error occurred.
- An empty `feed_link_tags` list combined with a low `a_count` may indicate a
  simple marketing stub with no feed metadata.
- A high `a_count` coupled with an empty `feed_link_tags` list can point to a
  dynamically generated site where feed tags are injected client side.
- `bot_challenge_detected: true` suggests the request was served a bot
  protection page (e.g. Cloudflare), in which case adding proper headers or
  waiting for a challenge token is required.

## Raw HTML captures

When feed discovery returns zero candidates, the pipeline automatically writes
the fetched HTML into the `diagnostics/raw/` directory. These files can be
opened in a browser or examined with a text editor to look for hidden feed
links, redirects or anti‑bot mechanisms. The filenames are based on the
normalised domain (e.g. `example.com.html`).

## Improving heuristics

The diagnostics captured by the script and pipeline should guide further
development. For example, if many sites rely on `/feed` endpoints without
advertising them via `<link>` tags, adding those endpoints to the fallback
list will increase coverage. Similarly, if bot challenges are frequent, using
a headless browser or a service like FeedBurner may be necessary.
