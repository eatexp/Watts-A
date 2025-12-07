"""Configuration module for Watts-A broadcast station."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Stream Keys
    TWITCH_STREAM_KEY: str = os.getenv("TWITCH_STREAM_KEY", "")
    KICK_STREAM_KEY: str = os.getenv("KICK_STREAM_KEY", "")
    RUMBLE_STREAM_KEY: str = os.getenv("RUMBLE_STREAM_KEY", "")

    # Twitch Chat Bot
    TWITCH_ACCESS_TOKEN: str = os.getenv("TWITCH_ACCESS_TOKEN", "")
    TWITCH_CHANNEL: str = os.getenv("TWITCH_CHANNEL", "")

    # Kick Chat
    KICK_CHANNEL: str = os.getenv("KICK_CHANNEL", "")

    # Stream Settings
    STREAM_BITRATE: str = os.getenv("STREAM_BITRATE", "3000k")
    STREAM_RESOLUTION: str = os.getenv("STREAM_RESOLUTION", "1920x1080")
    STREAM_FPS: int = int(os.getenv("STREAM_FPS", "30"))

    # RTMP URLs
    TWITCH_RTMP_URL: str = f"rtmp://live.twitch.tv/app/{TWITCH_STREAM_KEY}"
    KICK_RTMP_URL: str = f"rtmps://fa723fc1b171.global-contribute.live-video.net/app/{KICK_STREAM_KEY}"
    RUMBLE_RTMP_URL: str = f"rtmp://rtmp.rumble.com/live/{RUMBLE_STREAM_KEY}"

    # Paths
    VIDEOS_FOLDER: str = os.path.join(os.path.dirname(__file__), "videos")
    OVERLAY_FILE: str = "/tmp/watts_overlay.txt"

    # Voting Settings
    VOTE_WINDOW_SECONDS: int = 60
    VOTE_OPTIONS_COUNT: int = 4
    # Grace period after video ends to account for stream latency (5-10s typical)
    VOTE_GRACE_PERIOD_SECONDS: int = int(os.getenv("VOTE_GRACE_PERIOD_SECONDS", "5"))

    # Content Harvester Settings
    SOURCE_CHANNELS: list[str] = [
        url.strip()
        for url in os.getenv("SOURCE_CHANNELS", "").split(",")
        if url.strip()
    ]
    MAX_VIDEOS: int = int(os.getenv("MAX_VIDEOS", "30"))
    MIN_VIDEO_DURATION: int = int(os.getenv("MIN_VIDEO_DURATION", "900"))  # 15 minutes
    HARVESTER_INTERVAL_HOURS: int = int(os.getenv("HARVESTER_INTERVAL_HOURS", "4"))

    @classmethod
    def get_active_rtmp_urls(cls) -> list[str]:
        """Return list of RTMP URLs that have stream keys configured."""
        urls = []
        if cls.TWITCH_STREAM_KEY:
            urls.append(cls.TWITCH_RTMP_URL)
        if cls.KICK_STREAM_KEY:
            urls.append(cls.KICK_RTMP_URL)
        if cls.RUMBLE_STREAM_KEY:
            urls.append(cls.RUMBLE_RTMP_URL)
        return urls

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of warnings."""
        warnings = []
        if not cls.TWITCH_STREAM_KEY and not cls.KICK_STREAM_KEY and not cls.RUMBLE_STREAM_KEY:
            warnings.append("No stream keys configured - streaming will be disabled")
        if not cls.TWITCH_ACCESS_TOKEN:
            warnings.append("TWITCH_ACCESS_TOKEN not set - Twitch chat voting disabled")
        if not cls.TWITCH_CHANNEL:
            warnings.append("TWITCH_CHANNEL not set - Twitch chat voting disabled")
        return warnings
