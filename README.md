# cli-anything-xiaoyuzhoufm

CLI interface for [小宇宙FM](https://www.xiaoyuzhoufm.com/) (XiaoYuZhou FM) — a Chinese podcast platform.

Built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) framework, this tool lets you browse, download, and analyze podcasts entirely from the command line — no browser needed. Designed for both human users and AI agents.

## Why

- **For humans**: Search podcasts, download episodes, read shownotes, play audio — all from your terminal
- **For AI agents**: Structured JSON output, batch operations, SKILL.md for auto-discovery. One CLI call replaces 10+ browser interactions, saving 90%+ tokens

## Install

```bash
# Prerequisites
# Python 3.9+
# mpv (for audio playback): brew install mpv

# Clone and install
git clone https://github.com/D3AdCa7/cli-anything-xiaoyuzhoufm.git
cd cli-anything-xiaoyuzhoufm
pip install -e .

# Verify
python3 -m cli_anything.xiaoyuzhoufm --help
```

## Quick Start

```bash
# Shorthand
alias xyz='python3 -m cli_anything.xiaoyuzhoufm'

# Get podcast info (no login needed)
xyz podcast info 696186a3f83ec0a898b875c6

# List episodes (latest ~15 without login)
xyz podcast episodes 696186a3f83ec0a898b875c6 --limit 10

# ⭐ List ALL episodes via RSS (no login, no limit)
xyz podcast rss 696186a3f83ec0a898b875c6
xyz podcast rss "硬地骇客"                    # search by name

# Get episode show notes
xyz episode shownotes 69b6291acaaea1fb3b4e1b82

# Download an episode
xyz episode download 69b6291acaaea1fb3b4e1b82 -o episode.m4a

# Play with mpv
xyz play 69b6291acaaea1fb3b4e1b82

# Batch download entire podcast
xyz batch download 696186a3f83ec0a898b875c6 -o ./downloads

# Batch get all shownotes
xyz batch shownotes 696186a3f83ec0a898b875c6 -o shownotes.txt

# JSON output for scripting / AI agents
xyz --json podcast rss "TIANYU2FM"
```

## How to Find a Podcast ID (pid)

Most commands need a **pid** (24-char hex string). You can:

1. Go to [xiaoyuzhoufm.com](https://www.xiaoyuzhoufm.com/) and find the podcast
2. Copy the pid from the URL: `https://www.xiaoyuzhoufm.com/podcast/<pid>`
3. Or web search: `site:xiaoyuzhoufm.com <podcast name>`

## Commands

### No Login Required

| Command | Description |
|---------|-------------|
| `podcast info <pid>` | Podcast details (title, author, episode count, subscribers) |
| `podcast episodes <pid>` | List episodes (latest ~15 without login) |
| `podcast rss <pid or name>` | **List ALL episodes via RSS** — bypasses 15-episode limit |
| `episode info <eid>` | Episode details including audio URL |
| `episode shownotes <eid>` | Show notes as plain text |
| `episode download <eid>` | Download episode audio (M4A) |
| `play <eid>` | Play episode with mpv |
| `comment list <eid>` | View episode comments |
| `batch download <pid>` | Download all episodes to a folder |
| `batch shownotes <pid>` | Get all shownotes in one call |

### Login Required

| Command | Description |
|---------|-------------|
| `search <keyword>` | Search podcasts / episodes / users |
| `episode transcript <eid>` | Get episode transcript |
| `subscribe list` | List subscriptions |
| `subscribe add/remove <pid>` | Subscribe / unsubscribe |
| `user profile` | Your profile |
| `user history` | Listening history |
| `discover trending` | Trending episodes |
| `discover categories` | Browse categories |

### Authentication

```bash
xyz auth send-code 13800138000     # Send SMS verification code
xyz auth login 13800138000 123456  # Login with code
xyz auth status                     # Check login status
xyz auth logout                     # Logout
```

## The 15-Episode Limit

Without login, `podcast episodes` only returns the latest ~15 episodes. There are two ways to get the full list:

1. **`podcast rss`** (recommended) — Looks up the podcast's RSS feed via iTunes. Returns ALL episodes with audio URLs. Works for any podcast listed on Apple Podcasts. No login needed.

```bash
xyz --json podcast rss "十字路口Crossing"   # 103 episodes, all returned
xyz podcast rss 5f22729f9504bbdb77253e46   # same, by pid
```

2. **Login** — Gives access to the mobile API's pagination for `podcast episodes`.

## JSON Output

Add `--json` to any command for machine-readable output:

```bash
xyz --json podcast rss "TIANYU2FM"
```

```json
{
  "title": "TIANYU2FM — 对谈未知领域",
  "feedUrl": "http://www.ximalaya.com/album/40320716.xml",
  "itunesId": 1525369049,
  "episodeCount": 159,
  "episodes": [
    {
      "title": "E146. 为什么越重要的事，越容易选错？...",
      "pubDate": "Mon, 09 Mar 2026 23:00:00 GMT",
      "audioUrl": "https://...",
      "duration": "1:29:30",
      "size": 214814442
    }
  ]
}
```

## For AI Agents

This CLI includes a `SKILL.md` file at `cli_anything/xiaoyuzhoufm/skills/SKILL.md` that provides:
- Step-by-step workflow templates for common tasks
- JSON output structure documentation
- Auth requirement matrix
- The RSS workaround for the 15-episode limit

AI agents can read this file to immediately understand how to use the CLI without trial and error.

## Project Structure

```
cli_anything/xiaoyuzhoufm/
├── xiaoyuzhoufm_cli.py      # Main CLI (Click-based)
├── core/
│   └── session.py            # REPL session management
├── utils/
│   ├── api_client.py         # Dual-channel API client (web + mobile + RSS)
│   ├── player_backend.py     # mpv audio playback
│   └── repl_skin.py          # Interactive REPL interface
├── skills/
│   └── SKILL.md              # Agent discovery file
└── tests/
```

## Credits

- Built with [CLI-Anything](https://github.com/HKUDS/CLI-Anything) framework
- API research based on [ultrazg/xyz](https://github.com/ultrazg/xyz) and [shiquda/xyz-dl](https://github.com/shiquda/xyz-dl)
- Podcast platform: [小宇宙FM](https://www.xiaoyuzhoufm.com/)

## License

MIT
