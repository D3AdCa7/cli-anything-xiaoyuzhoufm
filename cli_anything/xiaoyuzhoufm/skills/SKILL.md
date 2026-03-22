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

Example: URL `https://www.xiaoyuzhoufm.com/podcast/696186a3f83ec0a898b875c6` → pid = `696186a3f83ec0a898b875c6`

Similarly, episode URLs contain eid: `/episode/<eid>`

## Commands — Quick Reference

### No Auth Required (most useful for agents)

```bash
# Podcast info
$XYZ --json podcast info <pid>

# List all episodes (returns JSON array with eid, title, duration, audio URL)
$XYZ --json podcast episodes <pid> --limit 100

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

### Batch Operations (most efficient for agents)

```bash
# Download ALL episodes of a podcast to a folder — ONE command
$XYZ --json batch download <pid> -o /path/to/dir

# Get ALL shownotes for a podcast — ONE command, ONE JSON output
$XYZ --json batch shownotes <pid>

# Save all shownotes to a file
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

## Agent Workflow Templates

### Template A: "Download all episodes of podcast X"

```bash
# 1. Find pid via web search (see Step 0)
# 2. One command does everything:
$XYZ --json batch download <pid> -o ./downloads
```

Returns JSON with download status for each episode, output directory, and file paths.

### Template B: "Get all content from podcast X for analysis"

```bash
# 1. Get all shownotes in one call:
$XYZ --json batch shownotes <pid>
```

Returns JSON: `{"podcast": "...", "episodes": [{"eid": "...", "title": "...", "shownotes": "..."}]}`

### Template C: "Get audio + text for specific episodes"

```bash
# 1. List episodes to find eids:
$XYZ --json podcast episodes <pid> --limit 20

# 2. For each eid of interest:
$XYZ episode download <eid> -o episode.m4a
$XYZ episode shownotes <eid>
```

### Template D: "Download and analyze a podcast I only know by name"

```bash
# 1. Web search: site:xiaoyuzhoufm.com "podcast name"
# 2. Extract pid from URL
# 3. Download all:
$XYZ --json batch download <pid> -o ./output
# 4. Get all shownotes for analysis:
$XYZ --json batch shownotes <pid>
```

## Output Structures

### `podcast episodes` → JSON array
```json
[{"eid": "69b629...", "title": "...", "duration": 2302, "pubDate": "2026-03-16T...",
  "enclosure": {"url": "https://media.xyzcdn.net/xxx.m4a"}, "playCount": 1234}]
```

### `batch download` → JSON summary
```json
{"podcast": "...", "pid": "...", "output_dir": "./downloads/podcast_name",
 "total": 13, "downloaded": 13, "existed": 0, "failed": 0,
 "files": [{"index": 1, "title": "...", "status": "ok", "path": "...", "size": 37000000}]}
```

### `batch shownotes` → JSON with all text
```json
{"podcast": "...", "pid": "...", "count": 13,
 "episodes": [{"eid": "...", "title": "...", "duration": 2302, "pubDate": "...", "shownotes": "plain text..."}]}
```

## Important Limitations

- **Without login, only the latest ~15 episodes are available** per podcast. This affects `podcast episodes`, `batch download`, and `batch shownotes`. For podcasts with <15 episodes (like Emma的碎碎念 with 13), this covers everything. For large podcasts (300+ episodes), you only get the most recent ~15.
- To access ALL episodes of a large podcast, the user must login first (`auth login`).
- `episode info` and `episode shownotes` work for ANY episode if you have the eid (even old ones).

## Key Facts

- **No auth needed** for: podcast info, episodes (latest ~15), shownotes, download, play, comments
- **Auth needed** for: search, transcript, subscribe, history, discover, full episode pagination
- Audio files are M4A format, direct CDN links, downloadable with curl
- pid/eid are 24-character hex strings (MongoDB ObjectIDs)
- `batch download` skips already-downloaded files (idempotent)
- `batch shownotes` fetches detailed shownotes per episode (makes N+1 API calls internally but returns one JSON)
- If you know specific eids (e.g. from web search), you can always use `episode info/shownotes/download` directly — the ~15 limit only affects listing commands
