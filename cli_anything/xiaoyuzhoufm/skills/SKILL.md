---
name: "cli-anything-xiaoyuzhoufm"
description: "CLI for 小宇宙FM podcast platform — search, browse, play, download, and analyze podcasts"
---

# cli-anything-xiaoyuzhoufm

CLI for 小宇宙FM (XiaoYuZhou FM) — a Chinese podcast platform.

**Invoke**: `python3 -m cli_anything.xiaoyuzhoufm`
**Shorthand used below**: `$XYZ`

## Step 0: How to Find a Podcast ID (pid)

Most commands need a **pid** (24-char hex string). Since the search API requires login, use this workaround:

1. **Web search** for: `site:xiaoyuzhoufm.com <podcast name>`
2. Extract pid from the URL: `https://www.xiaoyuzhoufm.com/podcast/<pid>`

Example: URL `.../podcast/696186a3f83ec0a898b875c6` → pid = `696186a3f83ec0a898b875c6`

Similarly, episode URLs contain eid: `/episode/<eid>`

## Commands — Quick Reference

### No Auth Required

```bash
# Podcast info
$XYZ --json podcast info <pid>

# List episodes (latest ~15 without login)
$XYZ --json podcast episodes <pid> --limit 100

# ⭐ RSS feed — lists ALL episodes, bypasses 15-episode limit
$XYZ --json podcast rss <pid>              # by pid
$XYZ --json podcast rss "播客名"            # by name (iTunes lookup)
$XYZ podcast rss <pid> --no-episodes       # only show feed URL

# Episode details (includes audio URL)
$XYZ --json episode info <eid>

# Show notes as plain text
$XYZ episode shownotes <eid>

# Download one episode
$XYZ episode download <eid> -o output.m4a

# Play with mpv
$XYZ play <eid>

# View comments
$XYZ --json comment list <eid>
```

### Batch Operations

```bash
# Download ALL episodes of a podcast to a folder — ONE command
$XYZ --json batch download <pid> -o /path/to/dir

# Get ALL shownotes — ONE command, ONE JSON output
$XYZ --json batch shownotes <pid>

# Save all shownotes to a text file
$XYZ batch shownotes <pid> -o shownotes.txt
```

### Auth Required

```bash
$XYZ auth send-code <phone>              # Send SMS code
$XYZ auth login <phone> <code>           # Login
$XYZ --json search "keyword"             # Search
$XYZ --json episode transcript <eid>     # Transcript
$XYZ --json subscribe list               # Subscriptions
$XYZ --json user history                 # Listening history
```

## The 15-Episode Limit and How to Bypass It

Without login, `podcast episodes` only returns the latest ~15 episodes.

**Solution: `podcast rss`** — Looks up the podcast's RSS feed via iTunes and returns ALL episodes with audio URLs. Works for any podcast listed on Apple Podcasts.

```bash
# Get ALL episodes (not just 15) — no login needed
$XYZ --json podcast rss <pid>
```

Returns JSON:
```json
{
  "title": "播客名",
  "feedUrl": "https://feed.xyzfm.space/xxx",
  "episodeCount": 159,
  "episodes": [
    {"title": "...", "pubDate": "Mon, 09 Mar 2026 23:00:00 GMT",
     "audioUrl": "https://...", "duration": "1:29:30", "size": 214814442}
  ]
}
```

Note: RSS audio URLs may be from ximalaya CDN or xyzfm CDN (same content, different host). RSS does NOT include playCount — use `episode info <eid>` for that.

## Agent Workflow Templates

### Template A: "List ALL episodes of a podcast" (best approach)

```bash
# 1. Find pid (web search or known)
# 2. Use RSS to get complete episode list:
$XYZ --json podcast rss <pid>
```

### Template B: "Download all episodes"

```bash
# For small podcasts (<15 episodes):
$XYZ --json batch download <pid> -o ./downloads

# For large podcasts: get audio URLs from RSS, then download with curl
$XYZ --json podcast rss <pid>
# Parse JSON, extract audioUrl from each episode, download with curl
```

### Template C: "Get all shownotes for analysis"

```bash
$XYZ --json batch shownotes <pid>
```

### Template D: "Find a podcast I only know by name"

```bash
# 1. Web search: site:xiaoyuzhoufm.com "podcast name"
# 2. Extract pid from URL
# 3. Get info: $XYZ --json podcast info <pid>
# 4. List all: $XYZ --json podcast rss <pid>
```

## Output Structures

### `podcast episodes` → JSON array
```json
[{"eid": "69b629...", "title": "...", "duration": 2302, "pubDate": "2026-03-16T...",
  "enclosure": {"url": "https://media.xyzcdn.net/xxx.m4a"}, "playCount": 1234}]
```

### `podcast rss` → JSON with ALL episodes
```json
{"title": "...", "feedUrl": "https://...", "itunesId": 12345, "episodeCount": 103,
 "episodes": [{"title": "...", "pubDate": "...", "audioUrl": "https://...", "duration": "01:07:57", "size": 0}]}
```

### `batch download` → JSON summary
```json
{"podcast": "...", "pid": "...", "output_dir": "./downloads/name",
 "total": 13, "downloaded": 13, "existed": 0, "failed": 0,
 "files": [{"index": 1, "title": "...", "status": "ok", "path": "...", "size": 37000000}]}
```

### `batch shownotes` → JSON with all text
```json
{"podcast": "...", "pid": "...", "count": 13,
 "episodes": [{"eid": "...", "title": "...", "duration": 2302, "pubDate": "...", "shownotes": "plain text..."}]}
```

## Key Facts

- **No auth needed** for: podcast info, episodes (latest ~15), rss (ALL), shownotes, download, play, comments
- **Auth needed** for: search, transcript, subscribe, history, discover
- `podcast rss` bypasses the 15-episode limit — returns ALL episodes via iTunes/RSS lookup
- Audio files are M4A format, direct CDN links, downloadable with curl
- pid/eid are 24-character hex strings (MongoDB ObjectIDs)
- `batch download` skips already-downloaded files (idempotent)
- RSS lookup works for any podcast listed on Apple Podcasts (most are)
- RSS audio URLs may differ from xiaoyuzhoufm CDN URLs but contain the same audio content
