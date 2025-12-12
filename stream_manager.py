"""FFmpeg stream manager for Watts-A broadcast station.

Handles streaming to multiple RTMP destinations simultaneously
using FFmpeg's tee muxer for single-encode, multi-output efficiency.

Includes "Dead Man's Switch" to detect and kill frozen FFmpeg processes.
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages FFmpeg streaming process with dead man's switch."""

    def __init__(self):
        """Initialize the stream manager."""
        self._process: subprocess.Popen | None = None
        self._current_video: Path | None = None
        self._start_time: float | None = None
        self._expected_duration: float | None = None

    def _build_ffmpeg_command(self, video_path: Path) -> list[str]:
        """
        Build the FFmpeg command for streaming.

        Args:
            video_path: Path to the video file to stream.

        Returns:
            List of command arguments for subprocess.
        """
        rtmp_urls = Config.get_active_rtmp_urls()

        if not rtmp_urls:
            raise ValueError("No RTMP destinations configured")

        # OVERLAY DISABLED: imageio-ffmpeg lacks drawtext filter
        # Build tee output for multiple destinations
        tee_outputs = "|".join(f"[f=flv]{url}" for url in rtmp_urls)

        cmd = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-i", str(video_path),
            # "-vf", drawtext_filter,  # DISABLED: No drawtext support
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", Config.STREAM_BITRATE,
            "-maxrate", Config.STREAM_BITRATE,
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", str(Config.STREAM_FPS * 2),  # Keyframe interval
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "tee",
            "-map", "0:v",
            "-map", "0:a",
            tee_outputs
        ]

        return cmd

    def set_expected_duration(self, duration: float):
        """
        Set expected video duration for dead man's switch.

        Args:
            duration: Expected video duration in seconds.
        """
        self._expected_duration = duration
        logger.debug(f"Expected duration set to {duration:.0f}s")

    def check_frozen(self) -> bool:
        """
        Check if FFmpeg is frozen (runtime exceeds expected duration + buffer).

        The dead man's switch triggers if:
        - Runtime > expected_duration + 120 seconds (2 minute buffer)

        Returns:
            True if FFmpeg appears frozen, False otherwise.
        """
        if not self._start_time or not self._expected_duration:
            return False

        runtime = time.time() - self._start_time
        max_allowed = self._expected_duration + 120  # 2 minute buffer

        if runtime > max_allowed:
            logger.warning(
                f"Dead man's switch triggered! "
                f"Runtime {runtime:.0f}s exceeds max allowed {max_allowed:.0f}s"
            )
            return True

        return False

    def start(self, video_path: Path) -> bool:
        """
        Start streaming a video.

        Args:
            video_path: Path to the video file to stream.

        Returns:
            True if streaming started successfully, False otherwise.
        """
        if self.is_streaming():
            logger.warning("Stream already running, stopping first")
            self.stop()

        try:
            cmd = self._build_ffmpeg_command(video_path)
            logger.info(f"Starting stream: {video_path.name}")

            # Log command with sanitized stream keys (security)
            safe_cmd = ' '.join(cmd)
            for key in [Config.TWITCH_STREAM_KEY, Config.KICK_STREAM_KEY, Config.RUMBLE_STREAM_KEY]:
                if key and key != "xxxxx":
                    safe_cmd = safe_cmd.replace(key, "***REDACTED***")
            logger.debug(f"FFmpeg command: {safe_cmd}")

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )
            self._current_video = video_path
            self._start_time = time.time()

            # Give FFmpeg a moment to start
            try:
                self._process.wait(timeout=2)
                # If we get here, FFmpeg exited too quickly (error)
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                logger.error(f"FFmpeg exited immediately: {stderr}")
                self._process = None
                self._start_time = None
                return False
            except subprocess.TimeoutExpired:
                # FFmpeg is still running, which is what we want
                return True

        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            self._process = None
            self._start_time = None
            return False

    def stop(self):
        """Stop the current stream."""
        if self._process:
            logger.info("Stopping stream")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg didn't terminate, killing")
                self._process.kill()
            self._process = None
            self._current_video = None
            self._start_time = None
            self._expected_duration = None

    def is_streaming(self) -> bool:
        """
        Check if a stream is currently running.

        Also checks for frozen state and kills the process if detected.

        Returns:
            True if streaming, False otherwise.
        """
        if self._process is None:
            return False

        # Check if frozen (dead man's switch)
        if self.check_frozen():
            logger.error("FFmpeg appears frozen, force killing process")
            try:
                self._process.kill()
            except Exception:
                pass
            self._process = None
            self._current_video = None
            self._start_time = None
            self._expected_duration = None
            return False

        # Check if process is still alive
        poll_result = self._process.poll()
        if poll_result is not None:
            # Process has ended
            self._process = None
            self._current_video = None
            self._start_time = None
            self._expected_duration = None
            return False

        return True

    async def wait_for_completion(self) -> int | None:
        """
        Asynchronously wait for the stream to complete.

        Returns:
            Return code of FFmpeg process, or None if not streaming.
        """
        if not self._process:
            return None

        while self.is_streaming():
            await asyncio.sleep(1)

        return self._process.returncode if self._process else None

    @property
    def current_video(self) -> Path | None:
        """Get the currently streaming video path."""
        return self._current_video

    @property
    def runtime(self) -> float:
        """Get current stream runtime in seconds."""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0


# Global stream manager instance
stream = StreamManager()
