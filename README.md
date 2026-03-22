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

# List episodes
xyz podcast episodes 696186a3f83ec0a898b875c6 --limit 10

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
xyz --json podcast episodes 696186a3f83ec0a898b875c6 --limit 5
```

## How to Find a Podcast ID (pid)

Most commands need a **pid** (24-char hex string). Since the search API requires login, you can:

1. Go to [xiaoyuzhoufm.com](https://www.xiaoyuzhoufm.com/) and find the podcast
2. Copy the pid from the URL: `https://www.xiaoyuzhoufm.com/podcast/<pid>`

Or web search: `site:xiaoyuzhoufm.com <podcast name>`

## Commands

### No Login Required

| Command | Description |
|---------|-------------|
| `podcast info <pid>` | Podcast details (title, author, episode count, subscribers) |
| `podcast episodes <pid>` | List episodes (latest ~15 without login) |
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

## JSON Output

Add `--json` to any command for machine-readable output:

```bash
xyz --json podcast episodes 696186a3f83ec0a898b875c6 --limit 3
```

```json
[
  {
    "eid": "69b6291acaaea1fb3b4e1b82",
    "title": "周日宏观早班车 前端重定价",
    "duration": 2302,
    "pubDate": "2026-03-16T...",
    "enclosure": {"url": "https://media.xyzcdn.net/xxx.m4a"},
    "playCount": 1234
  }
]
```

## Limitations

- **Without login, only the latest ~15 episodes** are available per podcast via listing commands. For small podcasts this covers everything; for large ones you need to login for full pagination.
- **Search, transcript, and subscription features require login** (SMS-based auth via Chinese phone number).
- Individual episode commands (`episode info/shownotes/download`) work for ANY episode if you have the eid.

## For AI Agents

This CLI includes a `SKILL.md` file at `cli_anything/xiaoyuzhoufm/skills/SKILL.md` that provides:
- Step-by-step workflow templates
- JSON output structure documentation
- Auth requirement matrix
- Common task patterns (batch download, analysis, etc.)

AI agents can read this file to immediately understand how to use the CLI without trial and error.

## Project Structure

```
cli_anything/xiaoyuzhoufm/
├── xiaoyuzhoufm_cli.py      # Main CLI (Click-based)
├── core/
│   └── session.py            # REPL session management
├── utils/
│   ├── api_client.py         # Dual-channel API client (web + mobile)
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
