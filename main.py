#!/usr/bin/env python3
"""
Watts-A: 24/7 Alan Watts Tribute Broadcast Station

A headless streaming service that plays videos from a local folder
and streams to Twitch, Kick, and Rumble with interactive voting.

Features:
- Multi-platform streaming (Twitch, Kick, Rumble)
- Interactive chat voting
- Dead man's switch for frozen streams
- Safe mode fallback when voting fails
"""

import asyncio
import logging
import random
import signal
import sys
from pathlib import Path

from config import Config
from utils import scan_videos, get_video_duration, select_random_choices
from overlay import overlay
from stream_manager import stream
from chat_listener import chat
from voting import voting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("watts-a")


class BroadcastStation:
    """Main broadcast station controller."""

    def __init__(self):
        """Initialize the broadcast station."""
        self._running = False
        self._next_video: Path | None = None

    async def run(self):
        """Main broadcast loop."""
        self._running = True

        # Validate configuration
        warnings = Config.validate()
        for warning in warnings:
            logger.warning(warning)

        # Start chat listeners
        chat.set_vote_callback(self._handle_vote)
        await chat.start()

        logger.info("Broadcast station started")

        try:
            while self._running:
                await self._broadcast_cycle()
        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)
        finally:
            await self._shutdown()

    async def _broadcast_cycle(self):
        """Execute one broadcast cycle (play one video with voting)."""
        # Get available videos
        videos = scan_videos()

        if not videos:
            logger.error("No videos found in videos folder")
            await asyncio.sleep(10)
            return

        # Select video to play
        if self._next_video and self._next_video in videos:
            current_video = self._next_video
        else:
            current_video = random.choice(videos)
            logger.info("Randomly selected first video")

        self._next_video = None

        # Get video duration
        duration = get_video_duration(current_video)
        if duration <= 0:
            logger.error(f"Could not get duration for {current_video.name}")
            duration = 300  # Default to 5 minutes

        logger.info(f"Playing: {current_video.name} ({duration:.0f}s)")

        # Prepare voting options (excluding current video)
        vote_options = select_random_choices(videos, 4, exclude=current_video)

        if len(vote_options) < 2:
            logger.warning("Not enough videos for voting")
            vote_options = videos[:4]

        options = [
            (chr(ord("A") + i), video)
            for i, video in enumerate(vote_options)
        ]

        # Update overlay with now playing
        overlay.show_now_playing(current_video)

        # Start streaming
        if not stream.start(current_video):
            logger.error("Failed to start stream")
            await asyncio.sleep(5)
            return

        # Set expected duration for dead man's switch
        stream.set_expected_duration(duration)

        # Calculate timing
        vote_start_time = max(0, duration - Config.VOTE_WINDOW_SECONDS)
        time_elapsed = 0

        # Wait until voting time
        while time_elapsed < vote_start_time and stream.is_streaming() and self._running:
            await asyncio.sleep(1)
            time_elapsed += 1

            # Show countdown when close to voting
            remaining = vote_start_time - time_elapsed
            if 0 < remaining <= 10:
                overlay.show_countdown(int(remaining))

        # === SAFE MODE VOTING ===
        # Wrap voting logic in try/except so stream continues even if voting fails
        try:
            # Start voting
            if stream.is_streaming() and self._running:
                voting.start(options)
                logger.info("Voting started")

                # Collect votes for remaining time + grace period for stream latency
                vote_end_time = duration + Config.VOTE_GRACE_PERIOD_SECONDS
                total_vote_time = int(vote_end_time - time_elapsed)
                logger.info(f"Voting window: {Config.VOTE_WINDOW_SECONDS}s + {Config.VOTE_GRACE_PERIOD_SECONDS}s grace period")

                # Update overlay every 1 second for smooth countdown
                while time_elapsed < vote_end_time and self._running:
                    # Calculate remaining time for countdown display
                    remaining = int(vote_end_time - time_elapsed)

                    # Update overlay with results and live countdown
                    if voting.is_active:
                        overlay.show_vote_results_with_countdown(
                            voting.get_results(),
                            options,
                            remaining
                        )

                    await asyncio.sleep(1)
                    time_elapsed += 1

                    # Check if stream is still running (dead man's switch may kill it)
                    if not stream.is_streaming():
                        logger.warning("Stream ended during voting")
                        break

            # Stop voting and determine winner
            voting.stop()
            winner = voting.get_winner()

            if winner:
                letter, video_path = winner
                self._next_video = video_path
                overlay.show_winner(letter, video_path)
                logger.info(f"Winner: {letter}) {video_path.name}")
                await asyncio.sleep(5)  # Show winner for 5 seconds
            else:
                # No votes - pick random
                self._next_video = random.choice(vote_options) if vote_options else None
                logger.info("No votes received, selecting randomly")

        except Exception as e:
            # SAFE MODE: Voting failed, fallback to random selection
            logger.error(f"Voting system error (safe mode activated): {e}")

            # Ensure voting is stopped
            try:
                voting.stop()
            except Exception:
                pass

            # Fallback to random selection
            self._next_video = random.choice(vote_options) if vote_options else None
            logger.info("Safe mode: Selected random video as fallback")

        # Stop current stream
        stream.stop()
        overlay.clear()

        # Brief pause between videos
        await asyncio.sleep(2)

    def _handle_vote(self, platform: str, username: str, choice: str, timestamp: float):
        """Handle incoming vote from chat."""
        try:
            voting.record_vote(platform, username, choice, timestamp)
        except Exception as e:
            logger.error(f"Failed to record vote: {e}")

    async def _shutdown(self):
        """Clean shutdown of all components."""
        logger.info("Shutting down...")
        self._running = False
        stream.stop()
        await chat.stop()
        overlay.clear()
        logger.info("Shutdown complete")

    def stop(self):
        """Signal the broadcast station to stop."""
        self._running = False


# Global station instance
station = BroadcastStation()


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}")
    station.stop()


async def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print startup banner
    print("""
    ╦ ╦╔═╗╔╦╗╔╦╗╔═╗   ╔═╗
    ║║║╠═╣ ║  ║ ╚═╗───╠═╣
    ╚╩╝╩ ╩ ╩  ╩ ╚═╝   ╩ ╩
    24/7 Alan Watts Tribute
    """)

    logger.info("Starting Watts-A Broadcast Station...")

    # Check for FFmpeg
    import shutil
    if not shutil.which("ffmpeg"):
        logger.error("FFmpeg not found. Please install FFmpeg.")
        sys.exit(1)

    if not shutil.which("ffprobe"):
        logger.error("ffprobe not found. Please install FFmpeg.")
        sys.exit(1)

    # Check for videos
    videos = scan_videos()
    if not videos:
        logger.warning(f"No videos found in {Config.VIDEOS_FOLDER}")
        logger.warning("Add .mp4 files to the videos folder to start streaming")

    # Run the station
    await station.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
