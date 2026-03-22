"""Audio playback backend using mpv."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def find_mpv() -> str:
    path = shutil.which("mpv")
    if path:
        return path
    raise RuntimeError(
        "mpv is not installed. Install it with:\n"
        "  brew install mpv        # macOS\n"
        "  apt install mpv         # Debian/Ubuntu\n"
        "  choco install mpv       # Windows"
    )


def play_audio(url: str, title: str = "", start_time: int = 0) -> dict:
    """Play audio URL with mpv. Returns when playback finishes or is interrupted."""
    mpv = find_mpv()
    args = [
        mpv,
        "--no-video",
        "--term-osd-bar",
        f"--force-media-title={title}" if title else "",
    ]
    if start_time > 0:
        args.append(f"--start={start_time}")
    args.append(url)
    args = [a for a in args if a]  # remove empty strings

    start = time.time()
    result = subprocess.run(args, check=False)
    elapsed = time.time() - start

    return {
        "status": "finished" if result.returncode == 0 else "interrupted",
        "returncode": result.returncode,
        "elapsed_seconds": round(elapsed, 1),
    }


def download_audio(url: str, output_path: str, title: str = "") -> dict:
    """Download audio file using curl."""
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl is not installed.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [curl, "-L", "-o", str(output), "--progress-bar", url],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Download failed with exit code {result.returncode}")

    size = output.stat().st_size
    return {
        "output": str(output),
        "size": size,
        "size_human": f"{size / 1024 / 1024:.1f} MB",
        "title": title,
    }
