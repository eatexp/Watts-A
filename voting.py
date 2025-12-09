"""Voting system for Watts-A broadcast station.

Handles vote collection, tallying, and winner determination.
Implements first-to-reach tie-breaking strategy.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Vote:
    """Represents a single vote."""
    platform: str
    username: str
    choice: str
    timestamp: float


@dataclass
class VoteOption:
    """Represents a voting option."""
    letter: str
    video_path: Path
    vote_count: int = 0
    # Track when this option reached each vote count (for tie-breaking)
    count_timestamps: dict[int, float] = field(default_factory=dict)


class VotingSession:
    """
    Manages a single voting session.

    Tracks votes from multiple platforms, ensures one vote per user,
    and determines winner using first-to-reach tie-breaking.
    """

    def __init__(self):
        """Initialize a new voting session."""
        self._options: dict[str, VoteOption] = {}
        self._votes: dict[str, Vote] = {}  # user_key -> Vote
        self._is_active: bool = False

    def start(self, options: list[tuple[str, Path]]):
        """
        Start a new voting session.

        Args:
            options: List of (letter, video_path) tuples.
                     e.g., [("A", Path("video1.mp4")),
                     ("B", Path("video2.mp4"))]
        """
        self._options.clear()
        self._votes.clear()

        for letter, video_path in options:
            self._options[letter.upper()] = VoteOption(
                letter=letter.upper(),
                video_path=video_path
            )

        self._is_active = True
        logger.info(f"Voting started with {len(options)} options")

    def stop(self):
        """Stop the current voting session."""
        self._is_active = False
        results = self.get_results()
        tally = ", ".join(f"{k}:{v}" for k, v in sorted(results.items()))
        logger.info(
            f"Voting stopped. Final tally: {tally}. "
            f"Total voters: {self.total_votes}"
        )

    def record_vote(
        self, platform: str, username: str, choice: str, timestamp: float
    ):
        """
        Record a vote from a user.

        Args:
            platform: Platform the vote came from (twitch, kick).
            username: Username of the voter.
            choice: Vote choice (A, B, C, or D).
            timestamp: Timestamp when the vote was received.
        """
        if not self._is_active:
            return

        choice = choice.upper()

        if choice not in self._options:
            logger.debug(f"Invalid vote choice: {choice}")
            return

        # Create unique user key
        # (platform:username to allow same user on different platforms)
        user_key = f"{platform}:{username.lower()}"

        # Check if user already voted
        if user_key in self._votes:
            old_vote = self._votes[user_key]
            if old_vote.choice == choice:
                # Same vote - ignore to prevent spam
                logger.debug(
                    f"Duplicate vote ignored: {username} already voted "
                    f"{choice}"
                )
                return
            # Different vote - decrement old choice
            old_option = self._options[old_vote.choice]
            old_option.vote_count -= 1
            logger.info(
                f"[Vote] {username} ({platform}) changed vote: "
                f"{old_vote.choice} -> {choice}"
            )
        else:
            logger.info(f"[Vote] {username} ({platform}) voted: {choice}")

        # Record the vote
        vote = Vote(
            platform=platform,
            username=username,
            choice=choice,
            timestamp=timestamp
        )
        self._votes[user_key] = vote

        # Update option count
        option = self._options[choice]
        option.vote_count += 1

        # Track when this option reached this vote count (for tie-breaking)
        # Only record the FIRST time it reaches each count
        if option.vote_count not in option.count_timestamps:
            option.count_timestamps[option.vote_count] = timestamp

        # Log current tally
        tally = ", ".join(
            f"{k}:{v.vote_count}" for k, v in sorted(self._options.items())
        )
        logger.info(f"[Tally] {tally}")

    def get_results(self) -> dict[str, int]:
        """
        Get current vote tallies.

        Returns:
            Dictionary of letter -> vote count.
        """
        return {
            letter: option.vote_count
            for letter, option in self._options.items()
        }

    def get_winner(self) -> Optional[tuple[str, Path]]:
        """
        Determine the winning option.

        Uses first-to-reach tie-breaking: if multiple options have
        the same vote count, the one that reached that count first wins.

        Returns:
            Tuple of (winning_letter, video_path), or None if no votes.
        """
        if not self._options:
            return None

        # Get max vote count
        max_votes = max(opt.vote_count for opt in self._options.values())

        if max_votes == 0:
            return None

        # Find all options with max votes
        tied_options = [
            opt for opt in self._options.values()
            if opt.vote_count == max_votes
        ]

        if len(tied_options) == 1:
            winner = tied_options[0]
        else:
            # Tie-breaker: first to reach the winning count
            # Sort by when they reached max_votes (earliest wins)
            tied_options.sort(
                key=lambda x: x.count_timestamps.get(max_votes, float('inf'))
            )
            winner = tied_options[0]
            tied_letters = [opt.letter for opt in tied_options]
            logger.info(
                f"Tie between {tied_letters} at {max_votes} votes. "
                f"Winner: {winner.letter} (reached {max_votes} first)"
            )

        return (winner.letter, winner.video_path)

    def get_options(self) -> list[tuple[str, Path]]:
        """
        Get the current voting options.

        Returns:
            List of (letter, video_path) tuples.
        """
        return [
            (opt.letter, opt.video_path)
            for opt in sorted(self._options.values(), key=lambda x: x.letter)
        ]

    @property
    def is_active(self) -> bool:
        """Check if voting is currently active."""
        return self._is_active

    @property
    def total_votes(self) -> int:
        """Get total number of unique voters."""
        return len(self._votes)


# Global voting session instance
voting = VotingSession()
