"""CLI entry point for cli-anything-xiaoyuzhoufm."""

from __future__ import annotations

import html
import json
import os
import re
import shlex
import sys
from typing import Any

import click

from cli_anything.xiaoyuzhoufm import __version__
from cli_anything.xiaoyuzhoufm.core.session import Session
from cli_anything.xiaoyuzhoufm.utils.api_client import XYZClient, load_auth, clear_auth
from cli_anything.xiaoyuzhoufm.utils.player_backend import play_audio, download_audio, find_mpv


# ── Helpers ──────────────────────────────────────────────────────────

def _json_out(ctx: click.Context, data: Any) -> None:
    """Print JSON if --json flag is set, otherwise return data for formatted output."""
    if ctx.obj.get("json_mode"):
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return data
    return data


def _format_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _truncate(text: str, maxlen: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) > maxlen:
        return text[:maxlen - 1] + "…"
    return text


# ── Main group ───────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format.")
@click.version_option(__version__, prog_name="cli-anything-xiaoyuzhoufm")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool) -> None:
    """CLI-Anything: XiaoYuZhou FM (小宇宙FM) podcast platform."""
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["client"] = XYZClient()
    ctx.obj["session"] = Session()

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── Auth ─────────────────────────────────────────────────────────────

@cli.group()
def auth():
    """Authentication: login, logout, status."""
    pass


@auth.command("send-code")
@click.argument("phone")
@click.option("--area-code", default="+86", help="Area code (default: +86).")
@click.pass_context
def auth_send_code(ctx, phone, area_code):
    """Send SMS verification code to phone number."""
    client: XYZClient = ctx.obj["client"]
    result = client.send_code(phone, area_code)
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"验证码已发送到 {phone}")


@auth.command("login")
@click.argument("phone")
@click.argument("code")
@click.option("--area-code", default="+86")
@click.pass_context
def auth_login(ctx, phone, code, area_code):
    """Login with phone number and SMS code."""
    client: XYZClient = ctx.obj["client"]
    result = client.login_with_sms(phone, code, area_code)
    data = {"status": "ok", "user": result.get("data", result)}
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo("登录成功！")


@auth.command("status")
@click.pass_context
def auth_status(ctx):
    """Show current authentication status."""
    auth_data = load_auth()
    data = {
        "authenticated": bool(auth_data.get("access_token")),
        "device_id": auth_data.get("device_id", "N/A"),
        "has_refresh_token": bool(auth_data.get("refresh_token")),
    }
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(data, indent=2))
    else:
        status = "已登录" if data["authenticated"] else "未登录"
        click.echo(f"状态: {status}")
        click.echo(f"设备ID: {data['device_id']}")


@auth.command("logout")
@click.pass_context
def auth_logout(ctx):
    """Clear saved authentication tokens."""
    clear_auth()
    data = {"status": "logged_out"}
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(data))
    else:
        click.echo("已退出登录")


# ── Search ───────────────────────────────────────────────────────────

@cli.command("search")
@click.argument("keyword")
@click.option("--type", "result_type", default="ALL", type=click.Choice(["ALL", "PODCAST", "EPISODE", "USER"]))
@click.option("--limit", default=10, type=int)
@click.pass_context
def search_cmd(ctx, keyword, result_type, limit):
    """Search for podcasts, episodes, or users."""
    client: XYZClient = ctx.obj["client"]
    result = client.search(keyword, result_type, limit)
    data = result.get("data", result)

    if _json_out(ctx, data) is not None and not ctx.obj["json_mode"]:
        items = data if isinstance(data, list) else data.get("data", [])
        if not items:
            click.echo("无搜索结果")
            return
        for item in items:
            itype = item.get("type", "")
            if itype == "PODCAST":
                podcast = item.get("podcast", item)
                click.echo(f"  [播客] {podcast.get('title', '?')}")
                click.echo(f"         pid={podcast.get('pid', '?')}  订阅={podcast.get('subscriptionCount', '?')}  集数={podcast.get('episodeCount', '?')}")
            elif itype == "EPISODE":
                ep = item.get("episode", item)
                click.echo(f"  [单集] {ep.get('title', '?')}")
                click.echo(f"         eid={ep.get('eid', '?')}  时长={_format_duration(ep.get('duration', 0))}  播放={ep.get('playCount', '?')}")
            elif itype == "USER":
                user = item.get("user", item)
                click.echo(f"  [用户] {user.get('nickname', '?')}  uid={user.get('uid', '?')}")
            else:
                click.echo(f"  [{itype}] {json.dumps(item, ensure_ascii=False)[:100]}")


# ── Podcast ──────────────────────────────────────────────────────────

@cli.group()
def podcast():
    """Podcast info and episode listing."""
    pass


@podcast.command("info")
@click.argument("pid")
@click.pass_context
def podcast_info(ctx, pid):
    """Get podcast details by pid."""
    client: XYZClient = ctx.obj["client"]
    data = client.podcast_get(pid).get("data", {})

    if _json_out(ctx, data) and not ctx.obj["json_mode"]:
        click.echo(f"标题: {data.get('title', '?')}")
        click.echo(f"作者: {data.get('author', '?')}")
        click.echo(f"描述: {_truncate(data.get('description', ''), 200)}")
        click.echo(f"订阅: {data.get('subscriptionCount', '?')}")
        click.echo(f"集数: {data.get('episodeCount', '?')}")
        click.echo(f"PID:  {data.get('pid', '?')}")


@podcast.command("episodes")
@click.argument("pid")
@click.option("--limit", default=20, type=int)
@click.option("--order", default="desc", type=click.Choice(["asc", "desc"]))
@click.pass_context
def podcast_episodes(ctx, pid, limit, order):
    """List episodes for a podcast."""
    client: XYZClient = ctx.obj["client"]
    result = client.podcast_episodes(pid, order, limit)
    episodes = result.get("data", [])

    if _json_out(ctx, episodes) and not ctx.obj["json_mode"]:
        if not episodes:
            click.echo("无节目")
            return
        for i, ep in enumerate(episodes, 1):
            dur = _format_duration(ep.get("duration", 0))
            date = ep.get("pubDate", "")[:10]
            click.echo(f"  {i:2d}. [{dur}] {ep.get('title', '?')}")
            click.echo(f"       eid={ep.get('eid', '?')}  {date}  播放={ep.get('playCount', 0)}")


@podcast.command("popular")
@click.argument("pid")
@click.pass_context
def podcast_popular(ctx, pid):
    """List popular episodes for a podcast."""
    client: XYZClient = ctx.obj["client"]
    result = client.podcast_popular(pid)
    episodes = result.get("data", [])

    if _json_out(ctx, episodes) and not ctx.obj["json_mode"]:
        for i, ep in enumerate(episodes, 1):
            dur = _format_duration(ep.get("duration", 0))
            click.echo(f"  {i:2d}. [{dur}] {ep.get('title', '?')}  播放={ep.get('playCount', 0)}")
            click.echo(f"       eid={ep.get('eid', '?')}")


@podcast.command("rss")
@click.argument("pid_or_name")
@click.option("--episodes/--no-episodes", default=True, help="Include episode list.")
@click.pass_context
def podcast_rss(ctx, pid_or_name, episodes):
    """Find RSS feed for a podcast (via iTunes). No auth needed.

    Accepts either a pid (24-char hex) or a podcast name.
    This bypasses the 15-episode limit — RSS feeds contain ALL episodes.
    """
    client: XYZClient = ctx.obj["client"]
    is_pid = bool(re.match(r'^[0-9a-f]{24}$', pid_or_name))
    result = client.podcast_rss(
        pid=pid_or_name if is_pid else None,
        name=pid_or_name if not is_pid else None,
    )

    if not episodes:
        result.pop("episodes", None)

    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"播客: {result.get('title', '?')}")
        click.echo(f"RSS:  {result.get('feedUrl', 'N/A')}")
        click.echo(f"iTunes ID: {result.get('itunesId', '?')}")
        ep_count = result.get('episodeCount', 0)
        click.echo(f"节目数: {ep_count}")
        if episodes and result.get("episodes"):
            click.echo()
            for i, ep in enumerate(result["episodes"], 1):
                dur = ep.get("duration", "?")
                click.echo(f"  {i:3d}. [{dur}] {ep.get('title', '?')}")
                if i >= 20 and not ctx.obj["json_mode"]:
                    click.echo(f"  ... 共 {ep_count} 集 (用 --json 查看全部)")
                    break


# ── Episode ──────────────────────────────────────────────────────────

@cli.group()
def episode():
    """Episode details, shownotes, transcript, download."""
    pass


@episode.command("info")
@click.argument("eid")
@click.pass_context
def episode_info(ctx, eid):
    """Get episode details by eid."""
    client: XYZClient = ctx.obj["client"]
    data = client.episode_get(eid).get("data", {})

    if _json_out(ctx, data) and not ctx.obj["json_mode"]:
        click.echo(f"标题:   {data.get('title', '?')}")
        click.echo(f"播客:   {data.get('podcast', {}).get('title', '?')}")
        click.echo(f"时长:   {_format_duration(data.get('duration', 0))}")
        click.echo(f"发布:   {data.get('pubDate', '?')[:10]}")
        click.echo(f"播放:   {data.get('playCount', 0)}")
        click.echo(f"评论:   {data.get('commentCount', 0)}")
        click.echo(f"EID:    {data.get('eid', '?')}")
        media = data.get("enclosure", {}).get("url", "")
        if media:
            click.echo(f"音频:   {media}")


@episode.command("shownotes")
@click.argument("eid")
@click.pass_context
def episode_shownotes(ctx, eid):
    """Get episode show notes (cleaned text)."""
    client: XYZClient = ctx.obj["client"]
    data = client.episode_get(eid).get("data", {})

    shownotes = data.get("shownotes") or data.get("description", "")
    cleaned = _strip_html(shownotes)

    if ctx.obj["json_mode"]:
        click.echo(json.dumps({"eid": eid, "title": data.get("title", ""), "shownotes": cleaned}, ensure_ascii=False, indent=2))
    else:
        click.echo(f"── {data.get('title', '?')} ──")
        click.echo()
        click.echo(cleaned)


@episode.command("transcript")
@click.argument("eid")
@click.pass_context
def episode_transcript(ctx, eid):
    """Get episode transcript (requires auth)."""
    client: XYZClient = ctx.obj["client"]
    ep = client.episode_get(eid).get("data", {})
    media_id = ep.get("media", {}).get("id") or ep.get("mediaKey", "")
    if not media_id:
        raise click.ClickException("Cannot determine media ID for this episode.")

    result = client.episode_transcript(eid, media_id)
    transcript = result.get("data", result)

    if ctx.obj["json_mode"]:
        click.echo(json.dumps({"eid": eid, "title": ep.get("title", ""), "transcript": transcript}, ensure_ascii=False, indent=2))
    else:
        click.echo(f"── 转录: {ep.get('title', '?')} ──\n")
        # Transcript may be a list of segments
        if isinstance(transcript, list):
            for seg in transcript:
                ts = _format_duration(int(seg.get("startTime", 0)))
                text = seg.get("text", "")
                click.echo(f"[{ts}] {text}")
        elif isinstance(transcript, dict):
            paragraphs = transcript.get("paragraphs", [])
            if paragraphs:
                for p in paragraphs:
                    ts = _format_duration(int(p.get("startTime", 0)))
                    words = " ".join(w.get("text", "") for w in p.get("words", []))
                    click.echo(f"[{ts}] {words}")
            else:
                click.echo(json.dumps(transcript, ensure_ascii=False, indent=2))
        else:
            click.echo(str(transcript))


@episode.command("download")
@click.argument("eid")
@click.option("-o", "--output", default=None, help="Output file path.")
@click.pass_context
def episode_download(ctx, eid, output):
    """Download episode audio."""
    client: XYZClient = ctx.obj["client"]
    ep = client.episode_get(eid).get("data", {})
    url = ep.get("enclosure", {}).get("url") or ep.get("media", {}).get("source", {}).get("url", "")
    if not url:
        raise click.ClickException("No audio URL found for this episode. It may be paid content.")

    title = ep.get("title", eid)
    if not output:
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', title)[:80]
        ext = url.rsplit(".", 1)[-1].split("?")[0] if "." in url.rsplit("/", 1)[-1] else "m4a"
        output = f"{safe_title}.{ext}"

    result = download_audio(url, output, title)

    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"已下载: {result['output']} ({result['size_human']})")


# ── Play ─────────────────────────────────────────────────────────────

@cli.command("play")
@click.argument("eid")
@click.option("--start", default=0, type=int, help="Start time in seconds.")
@click.pass_context
def play_cmd(ctx, eid, start):
    """Play an episode using mpv."""
    client: XYZClient = ctx.obj["client"]
    ep = client.episode_get(eid).get("data", {})
    url = ep.get("enclosure", {}).get("url") or ep.get("media", {}).get("source", {}).get("url", "")
    if not url:
        raise click.ClickException("No audio URL. May be paid content.")

    title = ep.get("title", eid)
    click.echo(f"正在播放: {title}")
    click.echo(f"时长: {_format_duration(ep.get('duration', 0))}")

    result = play_audio(url, title, start)
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, indent=2))


# ── Comment ──────────────────────────────────────────────────────────

@cli.group()
def comment():
    """View and manage comments."""
    pass


@comment.command("list")
@click.argument("eid")
@click.option("--order", default="hot", type=click.Choice(["hot", "time"]))
@click.option("--limit", default=20, type=int)
@click.pass_context
def comment_list(ctx, eid, order, limit):
    """List comments for an episode."""
    client: XYZClient = ctx.obj["client"]
    result = client.comment_list(eid, order)
    comments = result.get("data", [])[:limit]

    if _json_out(ctx, comments) and not ctx.obj["json_mode"]:
        if not comments:
            click.echo("暂无评论")
            return
        for c in comments:
            author = c.get("author", {}).get("nickname", "?")
            text = _truncate(c.get("text", ""), 120)
            likes = c.get("likeCount", 0)
            click.echo(f"  [{author}] {text}")
            click.echo(f"    👍 {likes}  回复={c.get('replyCount', 0)}")


# ── Subscribe ────────────────────────────────────────────────────────

@cli.group()
def subscribe():
    """Manage podcast subscriptions (requires auth)."""
    pass


@subscribe.command("list")
@click.option("--limit", default=50, type=int)
@click.pass_context
def subscribe_list(ctx, limit):
    """List subscribed podcasts."""
    client: XYZClient = ctx.obj["client"]
    result = client.subscription_list(limit)
    subs = result.get("data", [])

    if _json_out(ctx, subs) and not ctx.obj["json_mode"]:
        if not subs:
            click.echo("无订阅")
            return
        for i, s in enumerate(subs, 1):
            p = s.get("podcast", s)
            click.echo(f"  {i:2d}. {p.get('title', '?')}  (pid={p.get('pid', '?')})")


@subscribe.command("add")
@click.argument("pid")
@click.pass_context
def subscribe_add(ctx, pid):
    """Subscribe to a podcast."""
    client: XYZClient = ctx.obj["client"]
    result = client.subscription_update(pid, "ON")
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"已订阅 {pid}")


@subscribe.command("remove")
@click.argument("pid")
@click.pass_context
def subscribe_remove(ctx, pid):
    """Unsubscribe from a podcast."""
    client: XYZClient = ctx.obj["client"]
    result = client.subscription_update(pid, "OFF")
    if ctx.obj["json_mode"]:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"已取消订阅 {pid}")


# ── User ─────────────────────────────────────────────────────────────

@cli.group()
def user():
    """User profile, stats, history."""
    pass


@user.command("profile")
@click.option("--uid", default=None, help="User ID (default: self).")
@click.pass_context
def user_profile(ctx, uid):
    """Get user profile."""
    client: XYZClient = ctx.obj["client"]
    data = client.profile_get(uid).get("data", {})
    if _json_out(ctx, data) and not ctx.obj["json_mode"]:
        click.echo(f"昵称: {data.get('nickname', '?')}")
        click.echo(f"简介: {data.get('bio', '')}")
        click.echo(f"UID:  {data.get('uid', '?')}")


@user.command("history")
@click.option("--limit", default=20, type=int)
@click.pass_context
def user_history(ctx, limit):
    """Show listening history (requires auth)."""
    client: XYZClient = ctx.obj["client"]
    result = client.play_history()
    items = result.get("data", [])[:limit]
    if _json_out(ctx, items) and not ctx.obj["json_mode"]:
        for ep in items:
            click.echo(f"  {ep.get('title', '?')}  [{_format_duration(ep.get('duration', 0))}]")


# ── Discover ─────────────────────────────────────────────────────────

@cli.group()
def discover():
    """Discovery: trending, top lists, categories."""
    pass


@discover.command("trending")
@click.option("--category", default="HOT_EPISODES_IN_24_HOURS",
              type=click.Choice(["HOT_EPISODES_IN_24_HOURS", "SKYROCKET_EPISODES", "NEW_STAR_EPISODES"]))
@click.pass_context
def discover_trending(ctx, category):
    """Show trending/top episodes."""
    client: XYZClient = ctx.obj["client"]
    result = client.top_list(category)
    data = result.get("data", result)
    episodes = data.get("episodes", data) if isinstance(data, dict) else data

    if _json_out(ctx, episodes) and not ctx.obj["json_mode"]:
        if isinstance(episodes, list):
            for i, item in enumerate(episodes, 1):
                ep = item.get("episode", item) if isinstance(item, dict) else item
                title = ep.get("title", "?") if isinstance(ep, dict) else str(ep)
                click.echo(f"  {i:2d}. {title}")
                if isinstance(ep, dict):
                    click.echo(f"       eid={ep.get('eid', '?')}  播放={ep.get('playCount', '?')}")


@discover.command("categories")
@click.pass_context
def discover_categories(ctx):
    """List all podcast categories."""
    client: XYZClient = ctx.obj["client"]
    result = client.category_list()
    cats = result.get("data", [])
    if _json_out(ctx, cats) and not ctx.obj["json_mode"]:
        for cat in cats:
            click.echo(f"  {cat.get('name', '?')}  (id={cat.get('id', '?')})")


# ── Batch ────────────────────────────────────────────────────────────

@cli.group()
def batch():
    """Batch operations: download all, get all shownotes, etc."""
    pass


@batch.command("download")
@click.argument("pid")
@click.option("-o", "--output-dir", default=".", help="Output directory.")
@click.option("--limit", default=100, type=int)
@click.pass_context
def batch_download_cmd(ctx, pid, output_dir, limit):
    """Download ALL audio files for a podcast."""
    client: XYZClient = ctx.obj["client"]

    # Get podcast info for folder name
    podcast_data = client.podcast_get(pid).get("data", {})
    podcast_title = podcast_data.get("title", pid)
    safe_podcast = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', podcast_title)[:40]

    # Create output dir
    dest = os.path.join(output_dir, safe_podcast)
    os.makedirs(dest, exist_ok=True)

    # Get episodes
    result = client.podcast_episodes(pid, "desc", limit)
    episodes = result.get("data", [])
    total = len(episodes)

    results = []
    for i, ep in enumerate(episodes, 1):
        title = ep.get("title", f"episode_{i}")
        eid = ep.get("eid", "")
        url = ep.get("enclosure", {}).get("url", "")
        if not url:
            results.append({"index": i, "title": title, "status": "skipped", "reason": "no_url"})
            continue

        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', title)[:60]
        ext = url.rsplit(".", 1)[-1].split("?")[0] if "." in url.rsplit("/", 1)[-1] else "m4a"
        fname = f"{i:02d}_{safe_title}.{ext}"
        fpath = os.path.join(dest, fname)

        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            size = os.path.getsize(fpath)
            results.append({"index": i, "title": title, "status": "exists", "path": fpath, "size": size})
            if not ctx.obj["json_mode"]:
                click.echo(f"  [{i:2d}/{total}] EXISTS {title}")
            continue

        if not ctx.obj["json_mode"]:
            click.echo(f"  [{i:2d}/{total}] 下载: {title}...", nl=False)

        try:
            dl = download_audio(url, fpath, title)
            results.append({"index": i, "title": title, "status": "ok", "path": dl["output"], "size": dl["size"]})
            if not ctx.obj["json_mode"]:
                click.echo(f" {dl['size_human']}")
        except Exception as e:
            results.append({"index": i, "title": title, "status": "error", "error": str(e)})
            if not ctx.obj["json_mode"]:
                click.echo(f" FAILED: {e}")

    summary = {
        "podcast": podcast_title,
        "pid": pid,
        "output_dir": dest,
        "total": total,
        "downloaded": sum(1 for r in results if r["status"] == "ok"),
        "existed": sum(1 for r in results if r["status"] == "exists"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "files": results,
    }

    if ctx.obj["json_mode"]:
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        click.echo(f"\n完成: {summary['downloaded']} 下载, {summary['existed']} 已存在, {summary['failed']} 失败")
        click.echo(f"保存位置: {dest}")


@batch.command("shownotes")
@click.argument("pid")
@click.option("--limit", default=100, type=int)
@click.option("-o", "--output", default=None, help="Save to file instead of stdout.")
@click.pass_context
def batch_shownotes_cmd(ctx, pid, limit, output):
    """Get ALL shownotes for a podcast in one call."""
    client: XYZClient = ctx.obj["client"]

    podcast_data = client.podcast_get(pid).get("data", {})
    podcast_title = podcast_data.get("title", pid)

    result = client.podcast_episodes(pid, "desc", limit)
    episodes = result.get("data", [])

    all_notes = []
    for ep in episodes:
        eid = ep.get("eid", "")
        title = ep.get("title", "?")
        desc = ep.get("description", "")
        # Try to get full shownotes via episode detail
        try:
            detail = client.episode_get(eid).get("data", {})
            raw = detail.get("shownotes") or detail.get("description", "") or desc
        except Exception:
            raw = desc
        cleaned = _strip_html(raw)
        all_notes.append({
            "eid": eid,
            "title": title,
            "duration": ep.get("duration", 0),
            "pubDate": ep.get("pubDate", ""),
            "shownotes": cleaned,
        })

    if ctx.obj["json_mode"]:
        click.echo(json.dumps({
            "podcast": podcast_title,
            "pid": pid,
            "count": len(all_notes),
            "episodes": all_notes,
        }, ensure_ascii=False, indent=2))
    else:
        text_parts = []
        for note in all_notes:
            part = f"{'='*60}\n{note['title']}\n发布: {note['pubDate'][:10]}  时长: {_format_duration(note['duration'])}\n{'='*60}\n\n{note['shownotes']}\n\n"
            text_parts.append(part)
        full_text = "\n".join(text_parts)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(full_text)
            click.echo(f"已保存 {len(all_notes)} 篇 shownotes 到 {output}")
        else:
            click.echo(full_text)


# ── REPL ─────────────────────────────────────────────────────────────

@cli.command(hidden=True)
@click.pass_context
def repl(ctx):
    """Interactive REPL mode."""
    try:
        from cli_anything.xiaoyuzhoufm.utils.repl_skin import ReplSkin
    except ImportError:
        ReplSkin = None

    session: Session = ctx.obj["session"]

    if ReplSkin:
        skin = ReplSkin("xiaoyuzhoufm", version=__version__)
        skin.print_banner()
    else:
        click.echo(f"cli-anything-xiaoyuzhoufm v{__version__}")
        click.echo("Type 'help' for commands, 'exit' to quit.\n")

    COMMANDS = {
        "auth": "Authentication: login, logout, status",
        "search": "Search podcasts/episodes: search <keyword>",
        "podcast": "Podcast info/episodes: podcast info <pid>",
        "episode": "Episode details: episode info <eid>",
        "play": "Play episode: play <eid>",
        "comment": "Comments: comment list <eid>",
        "subscribe": "Subscriptions: subscribe list",
        "user": "User profile/history: user profile",
        "discover": "Discovery: discover trending",
    }

    BUILTINS = {
        "help": "Show this help",
        "exit/quit": "Exit the REPL",
        "use-podcast <pid>": "Set current podcast",
        "use-episode <eid>": "Set current episode",
        "status": "Show session status",
        "history": "Show command history",
        "clear": "Clear session state",
    }

    try:
        if ReplSkin:
            pt_session = skin.create_prompt_session()
        else:
            pt_session = None

        while True:
            try:
                podcast_label = session.current_podcast or ""
                prompt_str = f"xiaoyuzhoufm"
                if podcast_label:
                    prompt_str += f":{podcast_label[:12]}"

                if ReplSkin and pt_session:
                    line = skin.get_input(pt_session, project_name=podcast_label or None)
                else:
                    try:
                        line = input(f"{prompt_str}> ").strip()
                    except EOFError:
                        break

                if not line:
                    continue

                # Builtins
                if line in ("exit", "quit"):
                    break
                elif line == "help":
                    click.echo("\n命令组:")
                    for cmd, desc in COMMANDS.items():
                        click.echo(f"  {cmd:15s} {desc}")
                    click.echo("\n内置命令:")
                    for cmd, desc in BUILTINS.items():
                        click.echo(f"  {cmd:20s} {desc}")
                    click.echo()
                    continue
                elif line == "status":
                    for k, v in session.status().items():
                        click.echo(f"  {k}: {v}")
                    auth_data = load_auth()
                    click.echo(f"  authenticated: {bool(auth_data.get('access_token'))}")
                    continue
                elif line.startswith("use-podcast "):
                    pid = line.split(maxsplit=1)[1].strip()
                    session.current_podcast = pid
                    click.echo(f"当前播客: {pid}")
                    continue
                elif line.startswith("use-episode "):
                    eid = line.split(maxsplit=1)[1].strip()
                    session.current_episode = eid
                    click.echo(f"当前单集: {eid}")
                    continue
                elif line == "clear":
                    session.clear()
                    click.echo("会话已清除")
                    continue
                elif line == "history":
                    for h in session.history[-20:]:
                        click.echo(f"  {h}")
                    continue

                # Replace @podcast and @episode references
                line = line.replace("@podcast", session.current_podcast or "<no-podcast>")
                line = line.replace("@episode", session.current_episode or "<no-episode>")

                session.add_history(line)

                # Parse and dispatch to Click commands
                try:
                    args = shlex.split(line)
                except ValueError:
                    args = line.split()

                # Inject --json if json_mode is on
                if ctx.obj["json_mode"] and "--json" not in args:
                    args = ["--json"] + args

                try:
                    cli.main(args, standalone_mode=False, **{"obj": ctx.obj})
                except SystemExit:
                    pass
                except click.exceptions.UsageError as e:
                    click.echo(f"用法错误: {e}")
                except RuntimeError as e:
                    click.echo(f"错误: {e}")
                except Exception as e:
                    click.echo(f"错误: {type(e).__name__}: {e}")

            except KeyboardInterrupt:
                click.echo()
                continue

    except (EOFError, KeyboardInterrupt):
        pass

    if ReplSkin:
        skin.print_goodbye()
    else:
        click.echo("再见！")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
