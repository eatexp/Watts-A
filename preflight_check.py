#!/usr/bin/env python3
"""
Pre-flight check script for Watts-A broadcast station.
Validates all systems before going live.
"""
import os
import subprocess
import sys
from pathlib import Path

from config import Config


class PreflightChecker:
    """Comprehensive pre-flight validation."""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print('='*60)

    def check(self, name: str, condition: bool, error_msg: str = "", warning: bool = False):
        """
        Run a single check.

        Args:
            name: Check name
            condition: True if passed
            error_msg: Message to show on failure
            warning: If True, failure is a warning not an error
        """
        if condition:
            print(f"✅ {name}")
            self.checks_passed += 1
            return True
        else:
            if warning:
                print(f"⚠️  {name}")
                if error_msg:
                    print(f"    {error_msg}")
                self.warnings += 1
            else:
                print(f"❌ {name}")
                if error_msg:
                    print(f"    {error_msg}")
                self.checks_failed += 1
            return False

    def check_ffmpeg(self):
        """Check FFmpeg installation and capabilities."""
        self.print_header("FFmpeg Checks")

        # Check ffmpeg exists
        ffmpeg_path = subprocess.run(
            ["which", "ffmpeg"],
            capture_output=True,
            text=True,
            check=False
        ).stdout.strip()

        if not self.check(
            "FFmpeg installed",
            bool(ffmpeg_path),
            "Run: apt install ffmpeg (or equivalent)"
        ):
            return

        print(f"    Location: {ffmpeg_path}")

        # Check ffprobe exists
        ffprobe_path = subprocess.run(
            ["which", "ffprobe"],
            capture_output=True,
            text=True,
            check=False
        ).stdout.strip()

        self.check(
            "ffprobe installed",
            bool(ffprobe_path),
            "Required for video duration detection"
        )

        # Check for drawtext filter (critical for overlays)
        filters_output = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True,
            text=True,
            check=False
        ).stdout

        has_drawtext = "drawtext" in filters_output

        if not self.check(
            "drawtext filter available (CRITICAL)",
            has_drawtext,
            "Overlays will not work! Install full FFmpeg with FreeType support"
        ):
            print("    Run: apt install ffmpeg fonts-dejavu")
            print("    WITHOUT THIS: Viewers cannot see voting options!")

        # Check for required encoders
        encoders_output = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            check=False
        ).stdout

        self.check(
            "H.264 encoder (libx264)",
            "libx264" in encoders_output,
            "Required for video encoding"
        )

        self.check(
            "AAC encoder",
            "aac" in encoders_output or "libfdk_aac" in encoders_output,
            "Required for audio encoding"
        )

        # Check font file exists
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        self.check(
            "Font file exists",
            font_path.exists(),
            f"Install fonts: apt install fonts-dejavu",
            warning=True
        )

    def check_configuration(self):
        """Check configuration completeness."""
        self.print_header("Configuration Checks")

        # Stream keys
        self.check(
            "Twitch stream key configured",
            bool(Config.TWITCH_STREAM_KEY) and Config.TWITCH_STREAM_KEY != "xxxxx",
            "Set TWITCH_STREAM_KEY in .env"
        )

        self.check(
            "Kick stream key configured",
            bool(Config.KICK_STREAM_KEY) and Config.KICK_STREAM_KEY != "xxxxx",
            "Set KICK_STREAM_KEY in .env"
        )

        self.check(
            "Rumble stream key configured",
            bool(Config.RUMBLE_STREAM_KEY) and Config.RUMBLE_STREAM_KEY != "xxxxx",
            "Set RUMBLE_STREAM_KEY in .env (optional)",
            warning=True
        )

        # Chat credentials
        self.check(
            "Twitch OAuth token configured",
            bool(Config.TWITCH_ACCESS_TOKEN) and Config.TWITCH_ACCESS_TOKEN.startswith("oauth:"),
            "Set TWITCH_ACCESS_TOKEN in .env"
        )

        self.check(
            "Twitch channel configured",
            bool(Config.TWITCH_CHANNEL),
            "Set TWITCH_CHANNEL in .env"
        )

        self.check(
            "Kick channel configured",
            bool(Config.KICK_CHANNEL),
            "Set KICK_CHANNEL in .env"
        )

        # Stream settings
        print(f"\n  Stream Settings:")
        print(f"    Resolution: {Config.STREAM_RESOLUTION}")
        print(f"    FPS: {Config.STREAM_FPS}")
        print(f"    Bitrate: {Config.STREAM_BITRATE}")

        self.check(
            "Resolution is 1080p or higher",
            "1080" in Config.STREAM_RESOLUTION or "2160" in Config.STREAM_RESOLUTION,
            "Low resolution detected",
            warning=True
        )

    def check_videos(self):
        """Check video library."""
        self.print_header("Video Library Checks")

        video_dir = Path(Config.VIDEOS_FOLDER)

        self.check(
            "Video directory exists",
            video_dir.exists(),
            f"Create directory: mkdir {video_dir}"
        )

        if not video_dir.exists():
            return

        videos = list(video_dir.glob("*.mp4"))

        self.check(
            "Videos found",
            len(videos) > 0,
            "Run: python3 downloader.py (requires YouTube access)"
        )

        self.check(
            "Minimum 4 videos (for voting)",
            len(videos) >= 4,
            f"Only {len(videos)} videos found. Need 4+ for full voting UI",
            warning=len(videos) >= 2
        )

        if len(videos) > 0:
            print(f"\n  Video Library ({len(videos)} files):")

            # Check for test videos
            test_videos = [v for v in videos if "test" in v.name.lower()]
            if test_videos:
                print(f"    ⚠️  {len(test_videos)} test videos detected (not real content)")
                for tv in test_videos:
                    print(f"        - {tv.name}")

            # Calculate total size
            total_size = sum(v.stat().st_size for v in videos)
            total_gb = total_size / (1024**3)
            print(f"    Total size: {total_gb:.2f} GB")

            # Check video integrity (sample first 3)
            print(f"\n  Checking video integrity (sampling)...")
            for video in list(videos)[:3]:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                     str(video)],
                    capture_output=True,
                    text=True,
                    check=False
                )

                duration_str = result.stdout.strip()
                if duration_str and duration_str != "N/A":
                    try:
                        duration = float(duration_str)
                        status = "✅" if duration > 0 else "❌"
                        print(f"    {status} {video.name}: {duration:.0f}s")
                    except ValueError:
                        print(f"    ⚠️  {video.name}: Duration unknown (fallback: 300s)")
                else:
                    print(f"    ⚠️  {video.name}: Duration unknown (fallback: 300s)")

    def check_network(self):
        """Check network connectivity to streaming destinations."""
        self.print_header("Network Connectivity Checks")

        # Check if ping is available
        ping_path = subprocess.run(
            ["which", "ping"],
            capture_output=True,
            check=False
        ).stdout.strip()

        if not ping_path:
            print("  ⚠️  ping command not available, skipping network checks")
            self.warnings += 1
            return

        # Check DNS resolution
        destinations = [
            ("Twitch RTMP", "live.twitch.tv"),
            ("Kick RTMPS", "fa723fc1b171.global-contribute.live-video.net"),
            ("Rumble RTMP", "rtmp.rumble.com"),
        ]

        for name, host in destinations:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", host],
                capture_output=True,
                check=False
            )

            self.check(
                f"{name} reachable",
                result.returncode == 0,
                f"Network issue or firewall blocking {host}",
                warning=True
            )

    def check_dependencies(self):
        """Check Python dependencies."""
        self.print_header("Python Dependencies")

        required_packages = [
            ("twitchio", "twitchio", "Twitch chat integration"),
            ("pysher", "pysher", "Kick chat integration"),
            ("requests", "requests", "HTTP requests"),
            ("python-dotenv", "dotenv", "Configuration management"),
        ]

        for pip_name, import_name, description in required_packages:
            try:
                __import__(import_name)
                self.check(f"{pip_name} installed", True)
            except ImportError:
                self.check(
                    f"{pip_name} installed",
                    False,
                    f"Run: pip3 install {pip_name}"
                )

    def check_overlay_system(self):
        """Check overlay system configuration."""
        self.print_header("Overlay System Checks")

        # Check if overlay file location is writable
        overlay_file = Path(Config.OVERLAY_FILE)
        overlay_dir = overlay_file.parent

        self.check(
            "Overlay directory exists",
            overlay_dir.exists() or overlay_dir.parent.exists(),
            f"Cannot create {overlay_dir}"
        )

        # Try to write to overlay file
        try:
            overlay_file.parent.mkdir(parents=True, exist_ok=True)
            overlay_file.write_text("TEST")
            overlay_file.unlink()
            self.check("Overlay file writable", True)
        except Exception as e:
            self.check(
                "Overlay file writable",
                False,
                f"Cannot write to {overlay_file}: {e}"
            )

        # Check if overlay is enabled in stream_manager.py
        stream_manager_path = Path("stream_manager.py")
        if stream_manager_path.exists():
            content = stream_manager_path.read_text()

            # Look for commented-out drawtext filter
            if "# OVERLAY DISABLED" in content or "# -vf" in content:
                self.check(
                    "Overlay enabled in stream_manager.py",
                    False,
                    "Edit stream_manager.py and uncomment the -vf drawtext filter"
                )
            else:
                self.check("Overlay enabled in stream_manager.py", True)

    def check_permissions(self):
        """Check file permissions and access."""
        self.print_header("Permissions Checks")

        # Check if run.sh is executable
        run_script = Path("run.sh")
        if run_script.exists():
            is_executable = os.access(run_script, os.X_OK)
            self.check(
                "run.sh is executable",
                is_executable,
                "Run: chmod +x run.sh"
            )

    def run_all_checks(self):
        """Run all pre-flight checks."""
        print("""
╔══════════════════════════════════════════════════════════════╗
║              WATTS-A PRE-FLIGHT CHECK                        ║
║          24/7 Alan Watts Tribute Broadcast Station           ║
╚══════════════════════════════════════════════════════════════╝
        """)

        self.check_ffmpeg()
        self.check_configuration()
        self.check_videos()
        self.check_dependencies()
        self.check_overlay_system()
        self.check_permissions()
        self.check_network()

        # Print summary
        print("\n" + "="*60)
        print("  SUMMARY")
        print("="*60)
        print(f"✅ Checks passed: {self.checks_passed}")
        print(f"❌ Checks failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {self.warnings}")

        if self.checks_failed == 0:
            if self.warnings == 0:
                print("\n🚀 ALL SYSTEMS GO! Ready for launch!")
                return 0
            else:
                print("\n⚠️  READY WITH WARNINGS - Review warnings above")
                return 0
        else:
            print("\n❌ NOT READY - Fix failed checks before launching")
            return 1


def main():
    """Main entry point."""
    checker = PreflightChecker()
    exit_code = checker.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
