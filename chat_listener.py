"""Chat listener for Watts-A broadcast station.

Handles Twitch and Kick chat integration for vote collection.
Votes are forwarded to the voting module via callbacks.
"""

import asyncio
import json
import logging
import re
import threading
import time
from typing import Callable

import pysher
import requests
from twitchio.ext import commands

from config import Config

logger = logging.getLogger(__name__)

# Vote callback type: (platform, username, vote_letter, timestamp)
VoteCallback = Callable[[str, str, str, float], None]


class TwitchBot(commands.Bot):
    """Twitch chat bot for collecting votes."""

    def __init__(self, vote_callback: VoteCallback = None):
        """
        Initialize the Twitch bot.

        Args:
            vote_callback: Function to call when a vote is received.
        """
        super().__init__(
            token=Config.TWITCH_ACCESS_TOKEN,
            prefix="!",
            initial_channels=[Config.TWITCH_CHANNEL] if Config.TWITCH_CHANNEL else []
        )
        self._vote_callback = vote_callback
        self._vote_pattern = re.compile(r"^[AaBbCcDd]$")

    async def event_ready(self):
        """Called when bot is ready."""
        logger.info(f"Twitch bot connected as {self.nick}")

    async def event_message(self, message):
        """Handle incoming chat messages."""
        # Ignore bot's own messages
        if message.echo:
            return

        content = message.content.strip()

        # Check if message is a vote (single letter A, B, C, or D)
        if self._vote_pattern.match(content):
            vote = content.upper()
            username = message.author.name
            timestamp = asyncio.get_event_loop().time()

            logger.debug(f"Twitch vote: {username} -> {vote}")

            if self._vote_callback:
                self._vote_callback("twitch", username, vote, timestamp)

    def set_vote_callback(self, callback: VoteCallback):
        """Set the vote callback function."""
        self._vote_callback = callback


class KickListener:
    """
    Kick chat listener for collecting votes.

    Uses Pusher websocket to connect to Kick's chat system.
    Kick's chat runs on Pusher with app key: eb1d5f283081a78b932c
    """

    PUSHER_APP_KEY = "eb1d5f283081a78b932c"
    PUSHER_CLUSTER = "us2"

    def __init__(self, vote_callback: VoteCallback = None):
        """
        Initialize the Kick listener.

        Args:
            vote_callback: Function to call when a vote is received.
        """
        self._vote_callback = vote_callback
        self._running = False
        self._vote_pattern = re.compile(r"^[AaBbCcDd]$")
        self._pusher: pysher.Pusher | None = None
        self._chatroom_id: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_chatroom_id(self, channel_name: str) -> int | None:
        """
        Fetch chatroom ID from Kick API.

        Args:
            channel_name: Kick channel username.

        Returns:
            Chatroom ID or None if not found.
        """
        try:
            url = f"https://kick.com/api/v2/channels/{channel_name}"
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                chatroom = data.get("chatroom", {})
                return chatroom.get("id")
            else:
                logger.error(f"Failed to fetch Kick channel info: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching Kick chatroom ID: {e}")

        return None

    def _on_chat_message(self, data: str):
        """
        Handle incoming Pusher chat message.

        Args:
            data: JSON string of the chat message event.
        """
        try:
            message_data = json.loads(data)
            username = message_data.get("sender", {}).get("username", "")
            content = message_data.get("content", "").strip()

            # Check if message is a vote
            if self._vote_pattern.match(content):
                vote = content.upper()
                timestamp = time.time()

                logger.debug(f"Kick vote: {username} -> {vote}")

                if self._vote_callback and self._loop:
                    # Schedule callback in the asyncio event loop
                    self._loop.call_soon_threadsafe(
                        self._vote_callback, "kick", username, vote, timestamp
                    )
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse Kick message: {data}")
        except Exception as e:
            logger.error(f"Error processing Kick message: {e}")

    def _on_connect(self, data):
        """Handle Pusher connection established."""
        logger.info("Kick Pusher connected, subscribing to chatroom...")

        if self._chatroom_id and self._pusher:
            channel_name = f"chatrooms.{self._chatroom_id}.v2"
            channel = self._pusher.subscribe(channel_name)
            channel.bind("App\\Events\\ChatMessageEvent", self._on_chat_message)
            logger.info(f"Subscribed to Kick channel: {channel_name}")

    def _on_disconnect(self, data):
        """Handle Pusher disconnection."""
        logger.warning("Kick Pusher disconnected")

    def _on_error(self, data):
        """Handle Pusher error."""
        logger.error(f"Kick Pusher error: {data}")

    async def start(self):
        """Start listening to Kick chat."""
        if not Config.KICK_CHANNEL:
            logger.warning("KICK_CHANNEL not configured, Kick chat disabled")
            return

        self._running = True
        self._loop = asyncio.get_event_loop()

        # Get chatroom ID
        logger.info(f"Fetching Kick chatroom ID for: {Config.KICK_CHANNEL}")
        self._chatroom_id = self._get_chatroom_id(Config.KICK_CHANNEL)

        if not self._chatroom_id:
            logger.error(f"Could not find Kick channel: {Config.KICK_CHANNEL}")
            return

        logger.info(f"Kick chatroom ID: {self._chatroom_id}")

        # Initialize Pusher client
        self._pusher = pysher.Pusher(
            key=self.PUSHER_APP_KEY,
            cluster=self.PUSHER_CLUSTER,
            secure=True
        )

        # Bind connection handlers
        self._pusher.connection.bind("pusher:connection_established", self._on_connect)
        self._pusher.connection.bind("pusher:connection_failed", self._on_error)
        self._pusher.connection.bind("pusher:disconnected", self._on_disconnect)

        # Connect (runs in background thread)
        self._pusher.connect()

        logger.info(f"Kick listener started for channel: {Config.KICK_CHANNEL}")

        # Keep coroutine alive while running
        while self._running:
            await asyncio.sleep(1)

            # Reconnect if disconnected
            if self._pusher and not self._pusher.connection.is_alive():
                logger.warning("Kick connection lost, attempting reconnect...")
                try:
                    self._pusher.connect()
                except Exception as e:
                    logger.error(f"Kick reconnect failed: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the Kick listener."""
        self._running = False

        if self._pusher:
            try:
                self._pusher.disconnect()
            except Exception:
                pass
            self._pusher = None

        logger.info("Kick listener stopped")

    def set_vote_callback(self, callback: VoteCallback):
        """Set the vote callback function."""
        self._vote_callback = callback


class RumbleListener:
    """
    Rumble chat listener placeholder.

    Rumble doesn't have an official public chat API.
    This placeholder allows for future integration when/if
    Rumble releases chat API access.

    Known approaches (unofficial):
    - Screen scraping the live chat widget
    - Reverse engineering WebSocket connections
    - Using browser automation
    """

    def __init__(self, vote_callback: VoteCallback = None):
        """Initialize the Rumble listener."""
        self._vote_callback = vote_callback
        self._running = False
        self._vote_pattern = re.compile(r"^[AaBbCcDd]$")

    async def start(self):
        """Start listening to Rumble chat (placeholder)."""
        # Rumble chat integration is not yet available
        # When implemented, this would connect to Rumble's chat system
        logger.info("Rumble chat not yet implemented - streaming only")
        self._running = True

        while self._running:
            await asyncio.sleep(60)  # Minimal resource usage

    async def stop(self):
        """Stop the Rumble listener."""
        self._running = False
        logger.info("Rumble listener stopped")

    def set_vote_callback(self, callback: VoteCallback):
        """Set the vote callback function."""
        self._vote_callback = callback


class ChatManager:
    """Manages all chat platform listeners."""

    def __init__(self):
        """Initialize the chat manager."""
        self._twitch_bot: TwitchBot | None = None
        self._kick_listener: KickListener | None = None
        self._vote_callback: VoteCallback | None = None
        self._tasks: list[asyncio.Task] = []

    def set_vote_callback(self, callback: VoteCallback):
        """
        Set the callback for when votes are received.

        Args:
            callback: Function to call with (platform, username, vote, timestamp).
        """
        self._vote_callback = callback

        if self._twitch_bot:
            self._twitch_bot.set_vote_callback(callback)
        if self._kick_listener:
            self._kick_listener.set_vote_callback(callback)

    async def start(self):
        """Start all chat listeners."""
        # Start Twitch bot
        if Config.TWITCH_ACCESS_TOKEN and Config.TWITCH_CHANNEL:
            self._twitch_bot = TwitchBot(self._vote_callback)
            task = asyncio.create_task(self._twitch_bot.start())
            self._tasks.append(task)
            logger.info("Twitch bot starting...")
        else:
            logger.warning("Twitch credentials not configured")

        # Start Kick listener
        if Config.KICK_CHANNEL:
            self._kick_listener = KickListener(self._vote_callback)
            task = asyncio.create_task(self._kick_listener.start())
            self._tasks.append(task)
            logger.info("Kick listener starting...")
        else:
            logger.warning("Kick channel not configured")

    async def stop(self):
        """Stop all chat listeners."""
        if self._twitch_bot:
            await self._twitch_bot.close()

        if self._kick_listener:
            await self._kick_listener.stop()

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("All chat listeners stopped")


# Global chat manager instance
chat = ChatManager()
