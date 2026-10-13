# Community Daily Digest

A local Python prototype for generating a daily Markdown report of recent public posts from an OAuth-authorized account's joined communities. It is intended for use by the account owner, rather than as a hosted public service.

## Status

API access approval and application credentials are pending. This source has not been tested against the live Reddit API. Publishing this repository does not itself grant API access or determine eligibility for any access category. This README describes the software functionality; the API application must separately describe the actual intended use.

## Functionality

- Read joined communities, including pagination, through `GET /subreddits/mine/subscriber`.
- Select communities from that account's joined list.
- Read up to 25 latest posts per community by default, keeping posts from the last 24 hours.
- Print titles, community names, UTC publication times, and links to the original posts.
- Perform no posting, commenting, voting, messaging, subscription changes, or moderation.
- Use a descriptive User-Agent and observe Reddit rate-limit response headers. HTTP 429 stops the run.
- Use only Python's standard library. No third-party runtime dependencies.

## Requirements and authorization

Python 3.9 or later, Reddit's approval for the actual use case, and a user OAuth token with the `mysubreddits` and `read` scopes. An application-only token cannot identify the account's joined communities.

OAuth login and automatic token refresh are not implemented in this prototype. Supply a valid user token obtained through the approved application. A token may expire; HTTP 401 requires a renewed token. Never commit credentials or tokens to a repository.

Set these environment variables locally:

- `REDDIT_ACCESS_TOKEN`: the authorized account's current OAuth bearer token.
- `REDDIT_USER_AGENT`: for example `script:community-daily-digest:v0.1.0 (by /u/YOUR_USERNAME)`; replace the username with the actual account name.

## Usage

List the account's joined communities:

```sh
python3 digest.py --list-communities
```

Generate a report for selected communities (replace the example names with communities actually joined by the account):

```sh
python3 digest.py --subreddit COMMUNITY_ONE --subreddit COMMUNITY_TWO
```

Without `--subreddit`, the tool selects the first five joined communities alphabetically. `--limit` accepts 1–100 and `--hours` accepts greater than 0 up to 168. Busy communities can have more posts than the limit; reports are snapshots and are not comprehensive archives.

This prototype runs once per invocation. Automatic scheduling is not enabled. Reports are printed to standard output; the script does not create a content archive or record post bodies, comments, or author names. If output is saved separately, that storage must follow Reddit's applicable retention and deletion requirements.

## Offline verification

```sh
python3 -m unittest discover -s tests -v
```

These checks use synthetic data and make no requests to Reddit.

## Official references

- [Reddit API documentation](https://www.reddit.com/dev/api/)
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Devvit private user data limitations](https://developers.reddit.com/docs/capabilities/server/reddit-api)
