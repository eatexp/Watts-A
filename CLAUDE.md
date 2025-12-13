# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and AI assistants when working with code in this repository.

## Project Overview

Watts-A is a headless 24/7 broadcast station that streams video content to Twitch, Kick, and Rumble simultaneously with interactive chat voting. It runs autonomously on a VPS without OBS.

**Status:** Production-ready with comprehensive error handling, auto-recovery, and documentation.

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
- **Safe Mode Voting**: Falls back to random selection on chat API errors (main.py:136-195)
- **Pusher WebSocket**: Kick chat via reverse-engineered `pysher` connection
- **Thread-Safe Callbacks**: `call_soon_threadsafe()` bridges pysher thread to asyncio
- **Graceful Degradation**: System continues even if individual components fail

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt
apt install -y ffmpeg fonts-dejavu

# Pre-flight validation (always run before deploying)
python3 preflight_check.py

# System tests
python3 test_system.py

# Enable overlay (production VPS only)
python3 enable_overlay.py

# Run broadcast (with auto-restart supervisor)
./run.sh

# Run broadcast directly (for debugging)
python3 main.py

# Run content harvester (separate terminal)
python3 downloader.py
```

## Configuration

Copy `.env.example` to `.env` and configure:
- Stream keys: `TWITCH_STREAM_KEY`, `KICK_STREAM_KEY`, `RUMBLE_STREAM_KEY`
- Chat: `TWITCH_ACCESS_TOKEN`, `TWITCH_CHANNEL`, `KICK_CHANNEL`
- Harvester: `SOURCE_CHANNELS` (comma-separated YouTube URLs)

### Stream Settings (`.env`)
```bash
STREAM_RESOLUTION=1920x1080
STREAM_FPS=30
STREAM_BITRATE=3000k
```

## Critical Implementation Details

### Overlay System
- **File:** `/tmp/watts_overlay.txt` read by FFmpeg with `reload=1`
- **Font:** `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` (Debian/Ubuntu standard)
- **Status:** Disabled in development (imageio-ffmpeg lacks drawtext), enabled in production
- **Enable:** Run `python3 enable_overlay.py` after installing full FFmpeg

### Chat Integration
- **Twitch:** TwitchIO bot with OAuth token, auto-reconnects on disconnect
- **Kick:** Pusher WebSocket, app key `eb1d5f283081a78b932c`, cluster `us2`
- **Kick Reconnection:** Implemented in `chat_listener.py:214-221`
- **Vote Pattern:** Single letter A/B/C/D (case-insensitive)

### Security Considerations
- Stream keys **redacted in debug logs** (stream_manager.py:125-130)
- `.env` in `.gitignore` - never commit credentials
- OAuth tokens use `oauth:` prefix for Twitch
- Read-only chat bots (no moderation commands)

### Error Handling Strategy
1. **Component-level:** Try/except in each module
2. **System-level:** Safe mode wrapper in main.py (lines 136-195)
3. **Process-level:** Supervisor script (run.sh) restarts on crash
4. **Stream-level:** Dead man's switch kills frozen FFmpeg

## Development Workflow

### Making Changes

When modifying code:
1. Read the file first using Read tool
2. Make targeted edits using Edit tool
3. Test with `python3 test_system.py`
4. Validate with `python3 preflight_check.py`
5. Commit with descriptive message
6. Push to branch

### Testing Hierarchy
```
test_system.py          → Quick validation (30s)
preflight_check.py      → Comprehensive pre-launch checks (1min)
PRODUCTION_READINESS.md → Full deployment guide with edge cases
```

### Common Tasks

**Adding a new voting option:**
- Modify `main.py:103-106` to support more than 4 options
- Update `overlay.py` formatting for additional letters
- Test with `python3 test_system.py`

**Changing stream quality:**
- Edit `.env`: `STREAM_BITRATE`, `STREAM_RESOLUTION`
- Restart broadcast: `pkill -f main.py && ./run.sh`

**Adding error handling:**
- Use safe mode pattern from `main.py:136-195`
- Log errors with context: `logger.error(f"...", exc_info=True)`
- Never crash the main loop - always fall back gracefully

## File Reference

### Core Components
- `main.py` - Main broadcast controller, voting orchestration
- `stream_manager.py` - FFmpeg process management, dead man's switch
- `chat_listener.py` - Multi-platform chat integration
- `voting.py` - Vote tracking with first-to-reach tie-breaking
- `overlay.py` - Dynamic text overlay system
- `config.py` - Environment variable management
- `utils.py` - Video scanning, duration detection

### Scripts
- `run.sh` - Supervisor with auto-restart (infinite loop, 5s delay on crash)
- `downloader.py` - YouTube content harvester (yt-dlp wrapper)

### Testing & Validation
- `test_system.py` - System validation suite (FFmpeg, videos, voting, config)
- `preflight_check.py` - Pre-launch comprehensive checks
- `enable_overlay.py` - Automated overlay enablement for production

### Documentation
- `README.md` - Quick start guide for users
- `PRODUCTION_READINESS.md` - Deployment guide, edge cases, troubleshooting
- `CLAUDE.md` - This file (AI assistant guidance)
- `.env.example` - Configuration template

## Troubleshooting Guide

### Overlay Not Showing
**Symptom:** Viewers see raw video, no text overlays
**Cause:** imageio-ffmpeg lacks drawtext filter
**Fix:** Install full FFmpeg, run `python3 enable_overlay.py`
**Verify:** `ffmpeg -filters 2>&1 | grep drawtext`

### Kick Chat Not Working
**Symptom:** No votes from Kick platform
**Cause 1:** Chatroom ID fetch failed (network blocked)
**Fix:** Manually set `KICK_CHATROOM_ID` in `.env`
**Get ID:** `curl "https://kick.com/api/v2/channels/CHANNEL" | jq '.chatroom.id'`

**Cause 2:** Pusher WebSocket disconnected
**Fix:** Already handled by auto-reconnect (chat_listener.py:214-221)

### Stream Not Starting
**Symptom:** FFmpeg exits immediately
**Check 1:** `python3 preflight_check.py` (must show "ALL SYSTEMS GO")
**Check 2:** Stream keys valid in `.env`
**Check 3:** Videos exist in `videos/` folder
**Logs:** `tail -f watts-a.log | grep ERROR`

### No Votes Counted
**Symptom:** Users voting but tallies stay at 0
**Check 1:** Voting window active (last 60s of video)
**Check 2:** Chat bots connected (logs show "connected as...")
**Check 3:** Users typing valid votes (A/B/C/D only)
**Debug:** `tail -f watts-a.log | grep Vote`

## Production Deployment Checklist

Before deploying to production VPS:

- [ ] Run `python3 preflight_check.py` → Must show "🚀 ALL SYSTEMS GO!"
- [ ] At least 10 videos in `videos/` folder (15+ minutes each)
- [ ] No test videos (test_A.mp4, etc.) in library
- [ ] Overlay enabled: `python3 enable_overlay.py`
- [ ] `.env` configured with production credentials
- [ ] FFmpeg has drawtext filter: `ffmpeg -filters | grep drawtext`
- [ ] Font file exists: `ls /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`
- [ ] Test stream visible at https://twitch.tv/YOUR_CHANNEL
- [ ] Send test vote in chat, verify overlay updates

See `PRODUCTION_READINESS.md` for comprehensive deployment guide.

## Important Notes for AI Assistants

### When Reading Code
1. **Always read files before editing** - Never modify code you haven't seen
2. **Check related files** - Changes to voting.py may affect main.py
3. **Preserve error handling** - Don't remove try/except blocks
4. **Maintain safe mode pattern** - System must degrade gracefully

### When Making Changes
1. **Use Edit tool, not Write** - Preserve existing code structure
2. **Match existing style** - Use f-strings, type hints, docstrings
3. **Add logging** - Use logger.info/error/debug appropriately
4. **Test before committing** - Run test_system.py and preflight_check.py

### Security Reminders
1. **Never log stream keys** - Always redact sensitive data
2. **Never commit .env** - Check .gitignore before adding files
3. **Sanitize user input** - Vote pattern already validated (A/B/C/D only)
4. **No command injection** - Use subprocess safely (already done)

### Common Pitfalls to Avoid
1. **Don't break safe mode** - main.py:136-195 is critical error wrapper
2. **Don't disable auto-restart** - run.sh supervisor keeps system alive
3. **Don't remove reconnection logic** - chat_listener.py:214-221
4. **Don't expose secrets in logs** - stream_manager.py:125-130 redacts keys
5. **Don't assume network access** - Handle DNS failures gracefully

## Architecture Decisions

### Why FFmpeg Tee Muxer?
- Single encode → multiple outputs (saves 60% CPU vs. 3 separate FFmpeg processes)
- Maintains sync across all platforms
- Simpler process management (one process instead of three)

### Why Pusher for Kick?
- Official Kick API doesn't exist
- Reverse-engineered WebSocket connection is most reliable method
- Pusher is stable and production-ready (used by Kick themselves)

### Why Safe Mode Voting?
- Chat APIs can fail unpredictably (rate limits, network issues)
- Stream must continue even if voting breaks
- Random fallback ensures uninterrupted broadcast
- Viewers still get content even without interaction

### Why Dead Man's Switch?
- FFmpeg can freeze without exiting (network issues, RTMP hangs)
- Standard process monitoring won't catch this
- 120s buffer accounts for stream latency and buffering
- Prevents indefinite frozen streams

## Performance Characteristics

- **CPU Usage:** 20-30% (single core, x264 veryfast preset)
- **RAM Usage:** 200-300 MB
- **Network Upload:** ~400 KB/s (3000k bitrate)
- **Disk I/O:** Minimal (sequential video reads)
- **Startup Time:** 2-3 seconds
- **Recovery Time:** 5 seconds after crash (supervisor delay)

## License & Credits

Built for the Alan Watts community. Designed to run 24/7 on a VPS without manual intervention.

For questions about this codebase, refer to:
- `README.md` for user-facing documentation
- `PRODUCTION_READINESS.md` for deployment details
- This file (CLAUDE.md) for development guidance
