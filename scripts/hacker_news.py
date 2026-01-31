#!/usr/bin/env python3
import argparse
import datetime as dt
import sys
from urllib.parse import urlencode

import requests


ALGOLIA_HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"


def unix_ts_days_ago(days: int) -> int:
    return int((dt.datetime.utcnow() - dt.timedelta(days=days)).timestamp())


def search_hn(query: str, days: int = 7, hits: int = 20, tag: str = "story"):
    """
    Search recent Hacker News items matching `query`.

    tag:
      - "story"   -> posts
      - "comment" -> comments
      - "poll"    -> polls
    """
    numeric_filters = f"created_at_i>={unix_ts_days_ago(days)}"
    params = {
        "query": query,
        "tags": tag,
        "numericFilters": numeric_filters,
        "hitsPerPage": min(max(hits, 1), 100),
    }

    r = requests.get(ALGOLIA_HN_SEARCH, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def pick_url(hit: dict) -> str:
    # For HN posts: "url" is the external link; "story_url" sometimes exists in other endpoints.
    # For internal HN page:
    hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
    return hit.get("url") or hn_url


def main():
    ap = argparse.ArgumentParser(description="Search recent Hacker News items by keyword (via Algolia API).")
    ap.add_argument("query", help="Search query, e.g. 'postgres 17' or 'kafka'")
    ap.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    ap.add_argument("--hits", type=int, default=20, help="Max results (default: 20, max: 100)")
    ap.add_argument("--tag", default="story", choices=["story", "comment", "poll"], help="What to search (default: story)")
    args = ap.parse_args()

    data = search_hn(args.query, days=args.days, hits=args.hits, tag=args.tag)
    hits = data.get("hits", [])

    if not hits:
        print("No results.")
        return

    for i, h in enumerate(hits, 1):
        title = h.get("title") or h.get("comment_text") or "(no title)"
        title = " ".join(title.split())  # collapse whitespace
        points = h.get("points", 0)
        author = h.get("author", "?")
        created = h.get("created_at", "?")
        hn_id = h.get("objectID", "?")
        url = pick_url(h)

        print(f"{i:02d}. {title}")
        print(f"    points={points} author={author} created={created} id={hn_id}")
        print(f"    {url}")
        print()


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(2)
