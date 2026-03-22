# 小宇宙FM (XiaoYuZhou FM) — Agent Harness Analysis

## Target

- Software: 小宇宙FM (xiaoyuzhoufm.com) — Chinese podcast platform
- User goal: CLI interface for searching, browsing, playing, downloading, and analyzing podcasts without a browser

## Backend Surfaces

### API Endpoints

Base URL: `https://api.xiaoyuzhoufm.com`
Web API: `https://web-api.xiaoyuzhoufm.com`
CDN (audio): `https://media.xyzcdn.net`
CDN (images): `https://image.xyzcdn.net`

### Authentication

- SMS-based login: send code → verify code → receive tokens
- `POST /v1/auth/sendCode` — `{mobilePhoneNumber, areaCode: "+86"}`
- `POST /v1/auth/loginOrSignUpWithSMS` — `{mobilePhoneNumber, verifyCode, areaCode}`
- Tokens returned in response headers: `x-jike-access-token`, `x-jike-refresh-token`
- `POST /app_auth_tokens.refresh` — refresh token pair
- Required headers per request:
  - `x-jike-access-token`
  - `x-jike-device-id` (UUID)
  - `User-Agent: okhttp/4.12.0`

### Core API Catalog

#### Episodes
| Method | Path | Params |
|--------|------|--------|
| GET | `/v1/episode/get` | `?eid=<id>` |
| POST | `/v1/episode/list` | `{pid, order, limit, loadMoreKey?}` |
| POST | `/v1/episode/list-by-filter` | `{pid, label:"POPULAR"}` |
| POST | `/v1/episode-transcript/get` | `{eid, mediaId}` |
| GET | `/v1/private-media/get` | `?eid=<id>` (paid content) |

#### Podcasts
| Method | Path | Params |
|--------|------|--------|
| GET | `/v1/podcast/get` | `?pid=<id>` |
| GET | `/v1/podcast/get-info` | `?pid=<id>` |
| POST | `/v1/related-podcast/list` | `{pid}` |
| POST | `/v1/podcast-honor/list` | `{pid}` |

#### Search
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/search/create` | `{keyword, type, limit, loadMoreKey?}` |
| GET | `/v1/search/get-preset` | (none) |

#### Subscriptions
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/subscription/list` | `{uid, limit, sortOrder, sortBy, loadMoreKey?}` |
| POST | `/v1/subscription/update` | `{pid, mode:"ON"/"OFF"}` |
| POST | `/v1/subscription-star/list` | `{}` |
| POST | `/v1/subscription-star/update` | `{pid, withStar:bool}` |

#### Comments
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/comment/list-primary` | `{eid, order, loadMoreKey?}` |
| POST | `/v1/comment/list-thread` | `{order, primaryCommentId}` |
| POST | `/v1/comment/create` | `{text, ownerIdType, ownerId}` |

#### User / Profile
| Method | Path | Params |
|--------|------|--------|
| GET | `/v1/profile/get` | `?uid=<id>` or none for self |
| GET | `/v1/user-stats/get` | `?uid=<id>` |
| POST | `/v1/user-relation/list-following` | `{uid}` |
| POST | `/v1/user-relation/list-follower` | `{uid}` |

#### Playback & History
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/playback-progress/list` | `{eids:[]}` |
| POST | `/v1/episode-played/list-history` | `{loadMoreKey?}` |

#### Discovery & Rankings
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/discovery-feed/list` | `{returnAll, loadMoreKey?}` |
| GET | `/v1/top-list/get` | `?category=HOT_EPISODES_IN_24_HOURS` |
| POST | `/v1/category/list-all` | `{}` |
| POST | `/v1/category/podcast/list-by-tab` | `{categoryId, tab, loadMoreKey?}` |

#### Favorites
| Method | Path | Params |
|--------|------|--------|
| POST | `/v1/favorite/update` | `{eid, favorited:bool}` |
| POST | `/v1/favorite/list` | `{}` |

#### Mileage (Listening Stats)
| Method | Path | Params |
|--------|------|--------|
| GET | `/v1/mileage/get` | (none) |

### Data Models

**Podcast:**
```json
{
  "pid": "string",
  "title": "string",
  "author": "string",
  "description": "string",
  "subscriptionCount": 0,
  "episodeCount": 0,
  "image": {"picUrl": "string", ...},
  "podcasters": [{"uid": "string", "nickname": "string", "bio": "string"}],
  "latestEpisodePubDate": "ISO8601",
  "payType": "FREE|PAY",
  "status": "NORMAL"
}
```

**Episode:**
```json
{
  "eid": "string",
  "pid": "string",
  "title": "string",
  "description": "string",
  "shownotes": "html string",
  "duration": 0,
  "enclosure": {"url": "https://media.xyzcdn.net/xxx.m4a"},
  "isPrivateMedia": false,
  "media": {"id": "string", "size": 0, "mimeType": "audio/mp4"},
  "playCount": 0,
  "commentCount": 0,
  "favoriteCount": 0,
  "pubDate": "ISO8601"
}
```

**Pagination:** Uses `loadMoreKey` object — shape varies per endpoint.

## CLI Architecture

### Command Groups

| Group | Commands | Auth Required |
|-------|----------|--------------|
| `auth` | login, refresh, status, logout | No (creates auth) |
| `search` | podcasts, episodes | No |
| `podcast` | info, episodes, related | No |
| `episode` | info, shownotes, transcript, download | No (transcript needs auth) |
| `play` | start, pause, resume, stop | No |
| `subscribe` | list, add, remove, star | Yes |
| `comment` | list, thread, create | Partial |
| `user` | profile, stats, history, favorites | Yes |
| `discover` | feed, trending, categories, top-list | No |

### State Model

Subcommand mode: stateless per invocation (tokens from config file)

REPL mode:
- persisted `current_podcast` (pid)
- persisted `current_episode` (eid)
- persisted auth tokens
- session JSON at `~/.config/cli-anything-xiaoyuzhoufm/session.json`
- auth config at `~/.config/cli-anything-xiaoyuzhoufm/auth.json`

### Backend Software

- **mpv** — audio playback (required for `play` commands)
- **ffmpeg** — optional, for audio format conversion
- Audio URLs are direct M4A links from CDN, playable by mpv

### Output Format

- `--json` flag for machine-readable JSON output
- Human-readable tables/formatted text by default
- Show notes rendered as plain text (strip HTML)

## Reference Projects

- https://github.com/ultrazg/xyz — Go API wrapper (73 endpoints)
- https://github.com/shiquda/xyz-dl — Python CLI downloader
