# cli-anything-xiaoyuzhoufm

CLI interface for 小宇宙FM (XiaoYuZhou FM) podcast platform.

## Prerequisites

- Python 3.10+
- **mpv** (for audio playback): `brew install mpv`
- **curl** (for downloads, usually pre-installed)

## Install

```bash
cd xiaoyuzhoufm/agent-harness
pip install -e .
```

## Usage

```bash
# Search podcasts
cli-anything-xiaoyuzhoufm search "科技" --json

# Get podcast info
cli-anything-xiaoyuzhoufm podcast info <pid>

# List episodes
cli-anything-xiaoyuzhoufm podcast episodes <pid> --limit 10

# Get episode details
cli-anything-xiaoyuzhoufm episode info <eid>

# Get show notes
cli-anything-xiaoyuzhoufm episode shownotes <eid>

# Get transcript (requires auth)
cli-anything-xiaoyuzhoufm episode transcript <eid>

# Download episode audio
cli-anything-xiaoyuzhoufm episode download <eid> -o output.m4a

# Play episode with mpv
cli-anything-xiaoyuzhoufm play <eid>

# View comments
cli-anything-xiaoyuzhoufm comment list <eid>

# Discover trending
cli-anything-xiaoyuzhoufm discover trending

# Interactive REPL
cli-anything-xiaoyuzhoufm
```

## Authentication

Some features (subscriptions, transcript, history) require login:

```bash
cli-anything-xiaoyuzhoufm auth send-code 13800138000
cli-anything-xiaoyuzhoufm auth login 13800138000 123456
cli-anything-xiaoyuzhoufm auth status
```

## JSON Output

Add `--json` flag for machine-readable output:

```bash
cli-anything-xiaoyuzhoufm --json search "AI" --limit 5
cli-anything-xiaoyuzhoufm --json episode info <eid>
```
