"""Session state management for REPL mode."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any


def _state_dir() -> Path:
    override = os.environ.get("CLI_ANYTHING_XIAOYUZHOUFM_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "cli-anything-xiaoyuzhoufm"


def _session_path() -> Path:
    return _state_dir() / "session.json"


def _locked_save_json(path: Path, data: dict, **dump_kwargs: Any) -> None:
    """Atomically write JSON with exclusive file locking."""
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        f = open(path, "w")
    with f:
        locked = False
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=2, **dump_kwargs)
            f.flush()
        finally:
            if locked:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Session:
    """Manages REPL session state: current podcast, episode, command history."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        path = _session_path()
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "current_podcast": None,
            "current_episode": None,
            "command_history": [],
        }

    def save(self) -> None:
        _locked_save_json(_session_path(), self._state)

    @property
    def current_podcast(self) -> str | None:
        return self._state.get("current_podcast")

    @current_podcast.setter
    def current_podcast(self, pid: str | None) -> None:
        self._state["current_podcast"] = pid
        self.save()

    @property
    def current_episode(self) -> str | None:
        return self._state.get("current_episode")

    @current_episode.setter
    def current_episode(self, eid: str | None) -> None:
        self._state["current_episode"] = eid
        self.save()

    def add_history(self, cmd: str, limit: int = 50) -> None:
        hist = self._state.setdefault("command_history", [])
        hist.append(cmd)
        if len(hist) > limit:
            self._state["command_history"] = hist[-limit:]
        self.save()

    @property
    def history(self) -> list[str]:
        return self._state.get("command_history", [])

    def status(self) -> dict[str, Any]:
        return {
            "current_podcast": self.current_podcast,
            "current_episode": self.current_episode,
            "history_count": len(self.history),
            "state_file": str(_session_path()),
        }

    def clear(self) -> None:
        self._state = {
            "current_podcast": None,
            "current_episode": None,
            "command_history": [],
        }
        self.save()
