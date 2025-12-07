# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Watts-A is a headless 24/7 broadcast station that streams video content to Twitch, Kick, and Rumble simultaneously with interactive chat voting. It runs autonomously on a VPS without OBS.

## Architecture

```
main.py (BroadcastStation)
    ├── stream_manager.py   FFmpeg tee muxer → 3 RTMP destinations
    ├── chat_listener.py    Twitch (TwitchIO) + Kick (Pusher WebSocket)
    ├── voting.py           One-vote-per-user, first-to-reach tie-breaker
    ├── overlay.py          Dynamic FFmpeg drawtext (reload=1)
    └── config.py           Environment variables from .env

downloader.py (Content Harvester) - runs separately
    └── yt-dlp with 15-min filter, 30-video cap

run.sh (Supervisor) - auto-restarts main.py on crash
```

### Key Design Patterns

- **FFmpeg Tee Muxer**: Single encode, three RTMP outputs (saves CPU)
- **Dead Man's Switch**: Kills FFmpeg if runtime > duration + 120s
- **Safe Mode Voting**: Falls back to random selection on chat API errors
- **Pusher WebSocket**: Kick chat via reverse-engineered `pysher` connection

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt
apt install -y ffmpeg fonts-dejavu

# Run broadcast (with auto-restart supervisor)
./run.sh

# Run broadcast directly
python3 main.py

# Run content harvester (separate terminal)
python3 downloader.py
```

## Configuration

Copy `.env.example` to `.env` and configure:
- Stream keys: `TWITCH_STREAM_KEY`, `KICK_STREAM_KEY`, `RUMBLE_STREAM_KEY`
- Chat: `TWITCH_ACCESS_TOKEN`, `TWITCH_CHANNEL`, `KICK_CHANNEL`
- Harvester: `SOURCE_CHANNELS` (comma-separated YouTube URLs)

## Critical Implementation Details

- Kick chat uses Pusher app key `eb1d5f283081a78b932c` on cluster `us2`
- Overlay file at `/tmp/watts_overlay.txt` is read by FFmpeg with `reload=1`
- Font path hardcoded to `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`
- Vote callback uses `call_soon_threadsafe()` to bridge pysher thread to asyncio
