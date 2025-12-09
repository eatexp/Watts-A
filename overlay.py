"""Dynamic overlay system for Watts-A broadcast station.

FFmpeg's drawtext filter reads from a text file with reload=1,
allowing us to update the overlay dynamically during streaming.
"""

from pathlib import Path

from config import Config
from utils import get_video_title


class OverlayManager:
    """Manages the overlay text file that FFmpeg reads from."""

    def __init__(self, overlay_file: str = None):
        """
        Initialize the overlay manager.

        Args:
            overlay_file: Path to the overlay text file.
        """
        self.overlay_file = Path(overlay_file or Config.OVERLAY_FILE)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the overlay file if it doesn't exist."""
        self.overlay_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.overlay_file.exists():
            self.overlay_file.write_text("")

    def update(self, text: str):
        """
        Update the overlay text.

        Args:
            text: New text to display on the overlay.
        """
        # Escape special characters for FFmpeg drawtext
        escaped = text.replace("'", "'\\''").replace(":", "\\:")
        self.overlay_file.write_text(escaped)

    def clear(self):
        """Clear the overlay text."""
        self.overlay_file.write_text("")

    def show_now_playing(self, video_path: Path):
        """
        Display now playing information.

        Args:
            video_path: Path to the currently playing video.
        """
        title = get_video_title(video_path)
        self.update(f"Now Playing: {title}")

    def show_voting_options(self, options: list[tuple[str, Path]]):
        """
        Display voting options.

        Args:
            options: List of (letter, video_path) tuples.
                     e.g., [("A", Path("video1.mp4")),
                     ("B", Path("video2.mp4"))]
        """
        lines = ["VOTE NOW! Type A, B, C, or D in chat!"]
        for letter, video_path in options:
            title = get_video_title(video_path)
            # Truncate long titles
            if len(title) > 30:
                title = title[:27] + "..."
            lines.append(f"{letter}) {title}")

        self.update("\n".join(lines))

    def show_vote_results(self, results: dict[str, int]):
        """
        Display current vote tallies (legacy method).

        Args:
            results: Dictionary of letter -> vote count.
        """
        lines = ["VOTING RESULTS:"]
        for letter in ["A", "B", "C", "D"]:
            count = results.get(letter, 0)
            bar = "#" * min(count, 20)
            lines.append(f"{letter}: {bar} ({count})")

        self.update("\n".join(lines))

    def show_vote_results_with_countdown(
        self,
        results: dict[str, int],
        options: list[tuple[str, Path]],
        seconds_remaining: int
    ):
        """
        Display professional vote tallies with countdown timer.

        Args:
            results: Dictionary of letter -> vote count.
            options: List of (letter, video_path) tuples.
            seconds_remaining: Seconds until voting closes.
        """
        # Build options dict for easy lookup
        options_dict = {letter: path for letter, path in options}

        # Header
        lines = [
            "      NEXT VIDEO VOTE",
            f"    Time Remaining: {seconds_remaining}s",
            "-" * 30
        ]

        # Vote options with counts
        for letter in ["A", "B", "C", "D"]:
            if letter in options_dict:
                title = get_video_title(options_dict[letter])
                # Truncate long titles
                if len(title) > 18:
                    title = title[:15] + "..."
                count = results.get(letter, 0)
                # Format: "A: Title ...... X votes"
                vote_text = f"{count} vote" if count == 1 else f"{count} votes"
                lines.append(f"{letter}: {title:<18} {vote_text:>8}")

        self.update("\n".join(lines))

    def show_winner(self, letter: str, video_path: Path):
        """
        Display the winning selection.

        Args:
            letter: Winning vote letter.
            video_path: Path to the winning video.
        """
        title = get_video_title(video_path)
        self.update(f"WINNER: {letter}) {title}\nUp Next!")

    def show_countdown(self, seconds: int):
        """
        Display countdown to voting.

        Args:
            seconds: Seconds remaining until voting starts.
        """
        self.update(f"Voting starts in {seconds} seconds...")


# Global overlay manager instance
overlay = OverlayManager()
