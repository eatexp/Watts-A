"""Utility functions for Watts-A broadcast station."""

import json
import random
import subprocess
from pathlib import Path

from config import Config


def scan_videos(folder: str = None) -> list[Path]:
    """
    Scan folder for .mp4 video files.

    Args:
        folder: Path to scan. Defaults to Config.VIDEOS_FOLDER.

    Returns:
        List of Path objects for each .mp4 file found.
    """
    folder = folder or Config.VIDEOS_FOLDER
    video_path = Path(folder)

    if not video_path.exists():
        return []

    return sorted(video_path.glob("*.mp4"))


def get_video_duration(video_path: str | Path) -> float:
    """
    Get video duration in seconds using ffprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        Duration in seconds, or 0.0 if unable to determine.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(video_path)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0.0))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass

    return 0.0


def get_video_title(video_path: Path) -> str:
    """
    Extract a clean title from video filename.

    Args:
        video_path: Path to the video file.

    Returns:
        Cleaned title string without extension.
    """
    return video_path.stem.replace("_", " ").replace("-", " ")


def select_random_choices(
    videos: list[Path], count: int = 4, exclude: Path = None
) -> list[Path]:
    """
    Select random video choices for voting.

    Args:
        videos: List of available video paths.
        count: Number of choices to select.
        exclude: Video path to exclude (currently playing).

    Returns:
        List of randomly selected video paths.
    """
    available = [v for v in videos if v != exclude]

    if len(available) <= count:
        return available

    return random.sample(available, count)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to MM:SS string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "05:30".
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
