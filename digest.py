#!/usr/bin/env python3
"""Read joined communities and print a daily Markdown digest using Reddit OAuth."""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class RedditReader:
    def __init__(self, token, user_agent):
        self.token = token
        self.user_agent = user_agent
        self.resume_at = 0

    def get(self, path, **params):
        delay = self.resume_at - time.monotonic()
        if delay > 60:
            raise RuntimeError("Rate limit reached. Try again after the reset window.")
        if delay > 0:
            time.sleep(delay)
        url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={
            "Authorization": "bearer " + self.token,
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                remaining = response.headers.get("X-Ratelimit-Remaining")
                if remaining is not None and float(remaining) < 1:
                    self.resume_at = time.monotonic() + float(
                        response.headers.get("X-Ratelimit-Reset", "60")) + 1
                return json.load(response)["data"]
        except urllib.error.HTTPError as exc:
            messages = {
                401: "OAuth token expired or invalid; obtain a new user token.",
                403: "Access denied. Check Reddit approval and OAuth scopes.",
                429: "Rate limit reached. Wait before trying again.",
            }
            raise RuntimeError(messages.get(exc.code, "Reddit returned HTTP " + str(exc.code))) from None
        except urllib.error.URLError:
            raise RuntimeError("Could not connect to Reddit.") from None

    def joined(self):
        names = set()
        after = None
        seen = set()
        while True:
            params = {"limit": 100, "raw_json": 1}
            if after:
                params["after"] = after
            listing = self.get("/subreddits/mine/subscriber", **params)
            for child in listing["children"]:
                name = child["data"]["display_name"]
                if re.fullmatch(r"[A-Za-z0-9_]+", name):
                    names.add(name)
            after = listing.get("after")
            if not after:
                return names
            if after in seen:
                raise RuntimeError("Reddit returned a repeated pagination cursor.")
            seen.add(after)

    def recent(self, name, limit, cutoff):
        listing = self.get("/r/" + name + "/new", limit=limit, raw_json=1)
        return [child["data"] for child in listing["children"]
                if child["data"].get("created_utc", 0) >= cutoff]


def choose_communities(joined, requested):
    lookup = {name.casefold(): name for name in joined}
    if not requested:
        return sorted(joined, key=str.casefold)[:5]
    selected = []
    for value in requested:
        name = value[2:] if value.startswith("r/") else value
        if name.casefold() not in lookup:
            raise RuntimeError("Community is not in the authorized account's joined list: " + value)
        canonical = lookup[name.casefold()]
        if canonical not in selected:
            selected.append(canonical)
    return selected


def markdown_text(value):
    text = html.escape(" ".join(value.split()))
    return re.sub(r"([\\`*_{\[\]}])", r"\\\1", text)


def build_report(reader, communities, limit, hours, now):
    cutoff = now.timestamp() - hours * 3600
    lines = ["# Daily community report", "", "Generated: " + now.isoformat(),
             "", f"Window: last {hours:g} hours; up to {limit} latest posts per community.",
             "This is a snapshot, not a complete archive.", ""]
    for name in communities:
        lines.extend(["## r/" + name, ""])
        posts = reader.recent(name, limit, cutoff)
        if not posts:
            lines.append("No posts within the time window among the retrieved posts.")
        for post in posts:
            permalink = post.get("permalink", "")
            if not permalink.startswith("/r/"):
                continue
            url = "https://www.reddit.com" + urllib.parse.quote(permalink, safe="/")
            published = dt.datetime.fromtimestamp(post["created_utc"], dt.timezone.utc)
            lines.append(f"- [{markdown_text(post['title'])}]({url}) — {published.isoformat()}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-communities", action="store_true")
    parser.add_argument("--subreddit", action="append", default=[], help="Repeat to select joined communities")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--hours", type=float, default=24)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or not 0 < args.hours <= 168:
        parser.error("limit must be 1–100; hours must be greater than 0 and at most 168")
    token = os.environ.get("REDDIT_ACCESS_TOKEN", "")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "")
    if not token or not user_agent:
        parser.error("Set REDDIT_ACCESS_TOKEN and REDDIT_USER_AGENT after Reddit grants API access")
    try:
        reader = RedditReader(token, user_agent)
        joined = reader.joined()
        if args.list_communities:
            print("\n".join(sorted(joined, key=str.casefold)))
            return
        communities = choose_communities(joined, args.subreddit)
        if not communities:
            raise RuntimeError("The authorized account has no accessible joined communities.")
        print(build_report(reader, communities, args.limit, args.hours, dt.datetime.now(dt.timezone.utc)))
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
