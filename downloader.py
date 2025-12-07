#!/usr/bin/env python3
"""
Watts-A Content Harvester

Automated video downloader that:
- Scans YouTube channels for Alan Watts content
- Downloads only videos > 15 minutes (ignores Shorts/Livestreams)
- Maintains a healthy video library (max 30 videos)
- Runs continuously with 4-hour intervals
"""

import logging
import os
import time
from pathlib import Path

import yt_dlp

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("harvester")


def get_video_files() -> list[Path]:
    """Get list of video files sorted by creation time (oldest first)."""
    videos_folder = Path(Config.VIDEOS_FOLDER)
    if not videos_folder.exists():
        videos_folder.mkdir(parents=True, exist_ok=True)
        return []

    videos = list(videos_folder.glob("*.mp4"))
    # Sort by creation time (oldest first)
    videos.sort(key=lambda p: p.stat().st_ctime)
    return videos


def cleanup_old_videos():
    """Delete oldest videos if we're at or over capacity."""
    videos = get_video_files()

    while len(videos) >= Config.MAX_VIDEOS:
        oldest = videos[0]
        logger.info(f"Deleting oldest video to free space: {oldest.name}")
        try:
            oldest.unlink()
            videos.pop(0)
        except Exception as e:
            logger.error(f"Failed to delete {oldest.name}: {e}")
            break


def duration_filter(info_dict, *, incomplete):
    """
    Filter function for yt-dlp to only download videos > 15 minutes.
    Also filters out Shorts and Livestreams.
    """
    duration = info_dict.get('duration')
    title = info_dict.get('title', '').lower()
    is_live = info_dict.get('is_live', False)

    # Skip livestreams
    if is_live:
        return "Skipping livestream"

    # Skip if no duration info
    if duration is None:
        return "No duration info available"

    # Skip shorts (< 60 seconds) or videos with #shorts in title
    if duration < 60 or '#shorts' in title or '#short' in title:
        return f"Skipping short video ({duration}s)"

    # Skip videos under minimum duration (15 minutes = 900 seconds)
    if duration < Config.MIN_VIDEO_DURATION:
        return f"Video too short ({duration}s < {Config.MIN_VIDEO_DURATION}s)"

    # Accept this video
    return None


def download_from_channel(channel_url: str) -> int:
    """
    Download new videos from a YouTube channel.

    Args:
        channel_url: YouTube channel URL

    Returns:
        Number of videos downloaded
    """
    videos_folder = Config.VIDEOS_FOLDER
    archive_file = os.path.join(videos_folder, "download_archive.txt")

    # Ensure videos folder exists
    Path(videos_folder).mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(videos_folder, '%(title)s.%(ext)s'),
        'download_archive': archive_file,
        'match_filter': duration_filter,
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': False,
        'no_color': True,
        'extract_flat': False,
        'playlistend': 10,  # Only check last 10 videos per channel
        'sleep_interval': 2,  # Be nice to YouTube
        'max_sleep_interval': 5,
        'retries': 3,
        'fragment_retries': 3,
        # Sanitize filenames
        'restrictfilenames': True,
        'windowsfilenames': True,
    }

    downloaded = 0

    try:
        logger.info(f"Scanning channel: {channel_url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Check capacity before each download
            cleanup_old_videos()

            # Get channel videos
            result = ydl.extract_info(channel_url, download=False)

            if result is None:
                logger.warning(f"Could not fetch info from {channel_url}")
                return 0

            entries = result.get('entries', [])
            if not entries:
                logger.info(f"No videos found on {channel_url}")
                return 0

            logger.info(f"Found {len(entries)} videos to check")

            for entry in entries:
                if entry is None:
                    continue

                # Check capacity before each download
                current_count = len(get_video_files())
                if current_count >= Config.MAX_VIDEOS:
                    cleanup_old_videos()

                # Check if we still have room
                if len(get_video_files()) >= Config.MAX_VIDEOS:
                    logger.warning("At max capacity, stopping downloads")
                    break

                video_url = entry.get('webpage_url') or entry.get('url')
                if not video_url:
                    continue

                try:
                    # Count files before download
                    files_before = len(get_video_files())

                    # Download this video
                    ydl.download([video_url])

                    # Only count if a new file was actually created
                    files_after = len(get_video_files())
                    if files_after > files_before:
                        downloaded += 1
                except Exception as e:
                    logger.debug(f"Skipped or failed: {e}")

    except Exception as e:
        logger.error(f"Error scanning channel {channel_url}: {e}")

    return downloaded


def harvest_cycle():
    """Run one harvest cycle across all configured channels."""
    channels = Config.SOURCE_CHANNELS

    if not channels:
        logger.warning("No SOURCE_CHANNELS configured in .env")
        return

    logger.info(f"Starting harvest cycle with {len(channels)} channels")
    total_downloaded = 0

    for channel_url in channels:
        if not channel_url:
            continue

        try:
            downloaded = download_from_channel(channel_url)
            total_downloaded += downloaded
            logger.info(f"Downloaded {downloaded} videos from {channel_url}")
        except Exception as e:
            logger.error(f"Failed to process channel {channel_url}: {e}")

        # Brief pause between channels
        time.sleep(5)

    video_count = len(get_video_files())
    logger.info(f"Harvest complete. Downloaded {total_downloaded} new videos. Library: {video_count}/{Config.MAX_VIDEOS}")


def main():
    """Main entry point - runs harvest loop forever."""
    print("""
    ╦ ╦╔═╗╔╦╗╔╦╗╔═╗   ╔═╗
    ║║║╠═╣ ║  ║ ╚═╗───╠═╣
    ╚╩╝╩ ╩ ╩  ╩ ╚═╝   ╩ ╩
    Content Harvester
    """)

    logger.info("Starting Watts-A Content Harvester...")
    logger.info(f"Videos folder: {Config.VIDEOS_FOLDER}")
    logger.info(f"Max videos: {Config.MAX_VIDEOS}")
    logger.info(f"Min duration: {Config.MIN_VIDEO_DURATION}s ({Config.MIN_VIDEO_DURATION // 60} minutes)")
    logger.info(f"Harvest interval: {Config.HARVESTER_INTERVAL_HOURS} hours")

    if not Config.SOURCE_CHANNELS:
        logger.error("No SOURCE_CHANNELS configured! Add YouTube channel URLs to .env")
        logger.error("Example: SOURCE_CHANNELS=https://www.youtube.com/@AlanWattsOrg")
        return

    logger.info(f"Configured channels: {len(Config.SOURCE_CHANNELS)}")
    for url in Config.SOURCE_CHANNELS:
        logger.info(f"  - {url}")

    while True:
        try:
            harvest_cycle()
        except Exception as e:
            logger.error(f"Harvest cycle failed: {e}", exc_info=True)

        # Sleep until next cycle
        sleep_seconds = Config.HARVESTER_INTERVAL_HOURS * 3600
        logger.info(f"Sleeping for {Config.HARVESTER_INTERVAL_HOURS} hours until next harvest...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Harvester stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
